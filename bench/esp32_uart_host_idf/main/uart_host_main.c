/*
 * ESP-IDF UART host for the Cyclone IV baseline/secure bench tests.
 *
 * USB Serial (UART0 through the ESP32 development board) is the PC log
 * channel at 115200 baud. UART2 is the tested 9600/8N1 FPGA channel:
 *
 *   ESP32 GPIO17 / TX2 -> Cyclone IV J3 PIN_103 / UART_RX
 *   ESP32 GPIO16 / RX2 <- Cyclone IV J3 PIN_100 / UART_TX
 *   ESP32 GND          -> Cyclone IV GND
 *
 * Both boards must be powered independently. Do not connect their 5 V or
 * 3.3 V supply rails together; share only GND and the 3.3 V logic signals.
 */

#include <stdio.h>
#include <stdint.h>

#include "driver/uart.h"
#include "esp_err.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define FPGA_UART_PORT          UART_NUM_2
#define FPGA_UART_BAUD          9600
#define FPGA_UART_RX_GPIO       16
#define FPGA_UART_TX_GPIO       17
#define FPGA_UART_RX_BUFFER     256
#define FPGA_UART_TX_BUFFER     256
#define FPGA_UART_TIMEOUT_MS    250
#define FPGA_UART_PERIOD_MS     1000

static const char *TAG = "esp32_uart_host";
static const uint8_t test_bytes[] = {0x55, 0xA5, 0x00, 0xFF, 0x3C};

static void print_hex_line(const char *label, const uint8_t *data, size_t length)
{
    char line[3 * 64 + 1];
    size_t position = 0;

    for (size_t index = 0; index < length && index < 64; ++index) {
        int written = snprintf(&line[position], sizeof(line) - position,
                               "%02X%s", data[index],
                               index + 1U == length ? "" : " ");
        if (written < 0 || (size_t) written >= sizeof(line) - position) {
            break;
        }
        position += (size_t) written;
    }

    line[position] = '\0';
    ESP_LOGI(TAG, "%s%s", label, line);
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
                                        0,
                                        NULL,
                                        0));
    ESP_ERROR_CHECK(uart_param_config(FPGA_UART_PORT, &config));
    ESP_ERROR_CHECK(uart_set_pin(FPGA_UART_PORT,
                                 FPGA_UART_TX_GPIO,
                                 FPGA_UART_RX_GPIO,
                                 UART_PIN_NO_CHANGE,
                                 UART_PIN_NO_CHANGE));
}

void app_main(void)
{
    uint8_t received[64];

    configure_fpga_uart();
    ESP_LOGI(TAG, "ESP-IDF UART host ready");
    ESP_LOGI(TAG, "FPGA channel: 9600 8N1; TX GPIO%d; RX GPIO%d",
             FPGA_UART_TX_GPIO, FPGA_UART_RX_GPIO);

    while (true) {
        uart_flush_input(FPGA_UART_PORT);
        print_hex_line("TX: ", test_bytes, sizeof(test_bytes));

        int written = uart_write_bytes(FPGA_UART_PORT,
                                       (const char *) test_bytes,
                                       sizeof(test_bytes));
        if (written != (int) sizeof(test_bytes)) {
            ESP_LOGE(TAG, "UART write failed: %d/%u bytes",
                     written, (unsigned) sizeof(test_bytes));
        }

        esp_err_t tx_status = uart_wait_tx_done(
            FPGA_UART_PORT, pdMS_TO_TICKS(FPGA_UART_TIMEOUT_MS));
        if (tx_status != ESP_OK) {
            ESP_LOGE(TAG, "UART TX did not finish: %s",
                     esp_err_to_name(tx_status));
        }

        int received_count = uart_read_bytes(
            FPGA_UART_PORT,
            received,
            sizeof(received),
            pdMS_TO_TICKS(FPGA_UART_TIMEOUT_MS));
        if (received_count < 0) {
            ESP_LOGE(TAG, "UART read failed: %d", received_count);
            received_count = 0;
        }

        print_hex_line("RX: ", received, (size_t) received_count);
        ESP_LOGI(TAG, "RX bytes: %d", received_count);
        vTaskDelay(pdMS_TO_TICKS(FPGA_UART_PERIOD_MS));
    }
}
