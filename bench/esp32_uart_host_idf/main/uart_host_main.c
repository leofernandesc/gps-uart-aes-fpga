/*
 * ESP-IDF UART host for the DE10-Lite and Cyclone IV baseline/secure tests.
 *
 * USB Serial (UART0 through the ESP32 development board) is the PC log
 * channel at 115200 baud. UART2 is the tested 9600/8N1 FPGA channel:
 *
 *   ESP32 GPIO17 / TX2 -> FPGA UART_RX
 *   ESP32 GPIO16 / RX2 <- FPGA UART_TX
 *   ESP32 GND          -> FPGA GND
 *
 * Both boards must be powered independently. Do not connect their 5 V or
 * 3.3 V supply rails together; share only GND and the 3.3 V logic signals.
 */

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "driver/uart.h"
#include "esp_err.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"

#define FPGA_UART_PORT             UART_NUM_2
#define FPGA_UART_BAUD             9600
#define FPGA_UART_RX_GPIO          16
#define FPGA_UART_TX_GPIO          17
#define FPGA_UART_RX_BUFFER        256
#define FPGA_UART_TX_BUFFER        256
#define FPGA_UART_EVENT_QUEUE      20
#define FPGA_UART_TX_TIMEOUT_MS    30
#define FPGA_UART_RX_DEADLINE_MS   30
#define FPGA_UART_EXTRA_GUARD_MS   10
#define FPGA_UART_PERIOD_MS        1000
#define FPGA_UART_CAPTURE_BYTES    64
#define FPGA_UART_ARM_DELAY_MS     10000

static const char *TAG = "esp32_uart_host";
static const uint8_t test_bytes[] = {0x55, 0xA5, 0x00, 0xFF, 0x3C};
static QueueHandle_t fpga_uart_queue;
#if CONFIG_FPGA_UART_EXPECT_ECHO
static const char *test_mode = "baseline";
#else
static const char *test_mode = "secure";
#endif

typedef struct {
    uint8_t bytes[FPGA_UART_CAPTURE_BYTES];
    size_t captured_length;
    size_t total_length;
    int64_t expected_complete_us;
    uint32_t frame_errors;
    uint32_t parity_errors;
    uint32_t fifo_overflows;
    uint32_t buffer_fulls;
    uint32_t breaks;
    bool timed_out;
    bool write_error;
    bool tx_timeout;
} trial_result_t;

typedef struct {
    uint32_t trials;
    uint32_t timeouts;
    uint32_t mismatches;
    uint32_t extras;
    uint32_t capture_failures;
    uint32_t frame_errors;
    uint32_t parity_errors;
    uint32_t fifo_overflows;
    uint32_t buffer_fulls;
    uint32_t breaks;
    uint32_t write_errors;
    uint32_t tx_timeouts;
} run_counters_t;

static void format_hex(char *output, size_t output_size,
                       const uint8_t *data, size_t length)
{
    size_t position = 0;

    if (output_size == 0) {
        return;
    }
    if (length == 0) {
        snprintf(output, output_size, "-");
        return;
    }

    for (size_t index = 0; index < length; ++index) {
        int written = snprintf(&output[position], output_size - position,
                               "%02X", data[index]);
        if (written < 0 || (size_t)written >= output_size - position) {
            break;
        }
        position += (size_t)written;
    }
    output[position] = '\0';
}

static TickType_t ticks_until(int64_t deadline_us)
{
    int64_t remaining_us = deadline_us - esp_timer_get_time();
    if (remaining_us <= 0) {
        return 0;
    }

    int64_t ticks_64 =
        (remaining_us * configTICK_RATE_HZ + 999999) / 1000000;
    TickType_t ticks = (TickType_t)ticks_64;
    return ticks == 0 ? 1 : ticks;
}

static void read_event_bytes(size_t requested, trial_result_t *result)
{
    uint8_t chunk[FPGA_UART_CAPTURE_BYTES];

    while (requested > 0) {
        size_t chunk_length = requested < sizeof(chunk) ? requested : sizeof(chunk);
        int received = uart_read_bytes(FPGA_UART_PORT, chunk, chunk_length,
                                       pdMS_TO_TICKS(1));
        if (received <= 0) {
            return;
        }

        size_t free_space = sizeof(result->bytes) - result->captured_length;
        size_t copy_length = (size_t)received < free_space
                                 ? (size_t)received
                                 : free_space;
        if (copy_length > 0) {
            memcpy(&result->bytes[result->captured_length], chunk, copy_length);
            result->captured_length += copy_length;
        }
        size_t previous_total = result->total_length;
        result->total_length += (size_t)received;
        if (previous_total < sizeof(test_bytes) &&
            result->total_length >= sizeof(test_bytes)) {
            result->expected_complete_us = esp_timer_get_time();
        }
        requested -= (size_t)received;
    }
}

static void handle_uart_event(const uart_event_t *event, trial_result_t *result)
{
    switch (event->type) {
    case UART_DATA:
        read_event_bytes(event->size, result);
        break;
    case UART_FRAME_ERR:
        result->frame_errors++;
        break;
    case UART_PARITY_ERR:
        result->parity_errors++;
        break;
    case UART_FIFO_OVF:
        result->fifo_overflows++;
        ESP_ERROR_CHECK(uart_flush_input(FPGA_UART_PORT));
        xQueueReset(fpga_uart_queue);
        break;
    case UART_BUFFER_FULL:
        result->buffer_fulls++;
        ESP_ERROR_CHECK(uart_flush_input(FPGA_UART_PORT));
        xQueueReset(fpga_uart_queue);
        break;
    case UART_BREAK:
        result->breaks++;
        break;
    default:
        break;
    }
}

static void collect_until(int64_t deadline_us, bool stop_after_expected,
                          trial_result_t *result)
{
    uart_event_t event;

    while (!stop_after_expected || result->total_length < sizeof(test_bytes)) {
        TickType_t wait_ticks = ticks_until(deadline_us);
        if (wait_ticks == 0) {
            return;
        }
        if (xQueueReceive(fpga_uart_queue, &event, wait_ticks) != pdTRUE) {
            if (esp_timer_get_time() >= deadline_us) {
                return;
            }
            continue;
        }
        handle_uart_event(&event, result);
    }
}

static void configure_fpga_uart(void)
{
    const uart_config_t config = {
        .baud_rate = FPGA_UART_BAUD,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT,
    };

    ESP_ERROR_CHECK(uart_driver_install(FPGA_UART_PORT,
                                        FPGA_UART_RX_BUFFER,
                                        FPGA_UART_TX_BUFFER,
                                        FPGA_UART_EVENT_QUEUE,
                                        &fpga_uart_queue,
                                        0));
    ESP_ERROR_CHECK(uart_param_config(FPGA_UART_PORT, &config));
    ESP_ERROR_CHECK(uart_set_pin(FPGA_UART_PORT,
                                 FPGA_UART_TX_GPIO,
                                 FPGA_UART_RX_GPIO,
                                 UART_PIN_NO_CHANGE,
                                 UART_PIN_NO_CHANGE));

    // Discard only bytes that predate the experiment. Per-trial flushing could
    // hide late or duplicated bytes and would invalidate the error counters.
    ESP_ERROR_CHECK(uart_flush_input(FPGA_UART_PORT));
    xQueueReset(fpga_uart_queue);
}

static void update_counters(run_counters_t *counters,
                            const trial_result_t *result,
                            bool same_payload, size_t extra_bytes)
{
    bool transport_error = result->timed_out || extra_bytes != 0 ||
                           result->frame_errors != 0 ||
                           result->parity_errors != 0 ||
                           result->fifo_overflows != 0 ||
                           result->buffer_fulls != 0 ||
                           result->breaks != 0 || result->write_error ||
                           result->tx_timeout;

    counters->trials++;
    counters->timeouts += result->timed_out ? 1U : 0U;
#if CONFIG_FPGA_UART_EXPECT_ECHO
    counters->mismatches += same_payload ? 0U : 1U;
#endif
    counters->extras += extra_bytes != 0 ? 1U : 0U;
    counters->capture_failures += transport_error ? 1U : 0U;
    counters->frame_errors += result->frame_errors;
    counters->parity_errors += result->parity_errors;
    counters->fifo_overflows += result->fifo_overflows;
    counters->buffer_fulls += result->buffer_fulls;
    counters->breaks += result->breaks;
    counters->write_errors += result->write_error ? 1U : 0U;
    counters->tx_timeouts += result->tx_timeout ? 1U : 0U;
}

void app_main(void)
{
    run_counters_t counters = {0};
    TickType_t previous_wake;
    uint32_t sequence = 0;
    char tx_hex[sizeof(test_bytes) * 2 + 1];

    configure_fpga_uart();
    format_hex(tx_hex, sizeof(tx_hex), test_bytes, sizeof(test_bytes));
    ESP_LOGI(TAG, "ESP-IDF UART host ready");
    ESP_LOGI(TAG, "FPGA channel: 9600 8N1; TX GPIO%d; RX GPIO%d",
             FPGA_UART_TX_GPIO, FPGA_UART_RX_GPIO);
#if CONFIG_FPGA_UART_EXPECT_ECHO
    ESP_LOGI(TAG, "mode=baseline expected_echo=1");
#else
    ESP_LOGI(TAG, "mode=secure expected_echo=0; ciphertext requires PC verification");
#endif
    ESP_LOGW(TAG, "host_window_us is driver timing, not FPGA latency");
    ESP_LOGW(TAG, "ARM_DELAY_MS=%d; connect FPGA UART now",
             FPGA_UART_ARM_DELAY_MS);
    vTaskDelay(pdMS_TO_TICKS(FPGA_UART_ARM_DELAY_MS));
    ESP_LOGI(TAG, "ARMED: starting sequence at seq=1");
    previous_wake = xTaskGetTickCount();

    while (true) {
        trial_result_t result = {0};
        char rx_hex[FPGA_UART_CAPTURE_BYTES * 2 + 1];
        int64_t host_start_us = esp_timer_get_time();
        int64_t receive_deadline_us =
            host_start_us + (int64_t)FPGA_UART_RX_DEADLINE_MS * 1000;
        sequence++;

        int written = uart_write_bytes(FPGA_UART_PORT,
                                       (const char *)test_bytes,
                                       sizeof(test_bytes));
        result.write_error = written != (int)sizeof(test_bytes);

        esp_err_t tx_status = uart_wait_tx_done(
            FPGA_UART_PORT, pdMS_TO_TICKS(FPGA_UART_TX_TIMEOUT_MS));
        result.tx_timeout = tx_status != ESP_OK;

        collect_until(receive_deadline_us, true, &result);
        result.timed_out =
            result.expected_complete_us == 0 ||
            result.expected_complete_us > receive_deadline_us;

        // Keep listening after the expected response. This guard makes delayed
        // or duplicated bytes visible instead of discarding them next cycle.
        int64_t guard_deadline_us =
            esp_timer_get_time() + (int64_t)FPGA_UART_EXTRA_GUARD_MS * 1000;
        collect_until(guard_deadline_us, false, &result);

        size_t extra_bytes = result.total_length > sizeof(test_bytes)
                                 ? result.total_length - sizeof(test_bytes)
                                 : 0;
        bool same_payload =
            result.captured_length >= sizeof(test_bytes) &&
            memcmp(result.bytes, test_bytes, sizeof(test_bytes)) == 0;
        int64_t host_window_us = esp_timer_get_time() - host_start_us;

        format_hex(rx_hex, sizeof(rx_hex), result.bytes,
                   result.captured_length);
        update_counters(&counters, &result, same_payload, extra_bytes);

        ESP_LOGI(TAG,
                 "RESULT seq=%lu mode=%s tx=%s rx=%s rx_len=%u same=%d timeout=%d "
                 "extra=%u frame_err=%lu parity_err=%lu fifo_ovf=%lu "
                 "buffer_full=%lu break=%lu write_err=%d tx_timeout=%d "
                 "host_window_us=%lld",
                 (unsigned long)sequence, test_mode, tx_hex, rx_hex,
                 (unsigned)result.total_length, same_payload ? 1 : 0,
                 result.timed_out ? 1 : 0, (unsigned)extra_bytes,
                 (unsigned long)result.frame_errors,
                 (unsigned long)result.parity_errors,
                 (unsigned long)result.fifo_overflows,
                 (unsigned long)result.buffer_fulls,
                 (unsigned long)result.breaks,
                 result.write_error ? 1 : 0,
                 result.tx_timeout ? 1 : 0,
                 (long long)host_window_us);
        ESP_LOGI(TAG,
                 "SUMMARY trials=%lu timeouts=%lu mismatches=%lu "
                 "extra_trials=%lu capture_failures=%lu frame_err=%lu "
                 "parity_err=%lu fifo_ovf=%lu buffer_full=%lu break=%lu "
                 "write_err=%lu tx_timeout=%lu",
                 (unsigned long)counters.trials,
                 (unsigned long)counters.timeouts,
                 (unsigned long)counters.mismatches,
                 (unsigned long)counters.extras,
                 (unsigned long)counters.capture_failures,
                 (unsigned long)counters.frame_errors,
                 (unsigned long)counters.parity_errors,
                 (unsigned long)counters.fifo_overflows,
                 (unsigned long)counters.buffer_fulls,
                 (unsigned long)counters.breaks,
                 (unsigned long)counters.write_errors,
                 (unsigned long)counters.tx_timeouts);

        vTaskDelayUntil(&previous_wake, pdMS_TO_TICKS(FPGA_UART_PERIOD_MS));
    }
}
