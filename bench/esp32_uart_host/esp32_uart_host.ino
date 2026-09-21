// ESP32 UART host for the Cyclone IV baseline/secure bench tests.
//
// USB Serial (Serial) is the PC log channel at 115200 baud.
// UART2 (FPGA) is the tested 9600/8N1 channel:
//   ESP32 GPIO17 (TX2) -> Cyclone IV PIN_103 (UART_RX)
//   ESP32 GPIO16 (RX2) <- Cyclone IV PIN_100 (UART_TX)
//   ESP32 GND          -> Cyclone IV GND
//
// Do not connect the ESP32 5 V or 3.3 V supply to the FPGA. Power the boards
// independently and share only GND and the two 3.3 V logic signals.

#include <Arduino.h>

HardwareSerial FpgaUart(2);

constexpr int FPGA_RX_PIN = 16;  // ESP32 receives Cyclone IV TX
constexpr int FPGA_TX_PIN = 17;  // ESP32 transmits to Cyclone IV RX
constexpr uint32_t FPGA_BAUD = 9600;

const uint8_t TEST_BYTES[] = {0x55, 0xA5, 0x00, 0xFF, 0x3C};
constexpr size_t TEST_LENGTH = sizeof(TEST_BYTES);

void printHexByte(uint8_t value) {
  if (value < 0x10) Serial.print('0');
  Serial.print(value, HEX);
}

void setup() {
  Serial.begin(115200);
  FpgaUart.begin(FPGA_BAUD, SERIAL_8N1, FPGA_RX_PIN, FPGA_TX_PIN);
  delay(500);
  Serial.println("ESP32 UART host ready");
  Serial.println("FPGA channel: 9600 8N1");
}

void loop() {
  while (FpgaUart.available() > 0) {
    FpgaUart.read();
  }

  Serial.print("TX: ");
  for (size_t i = 0; i < TEST_LENGTH; ++i) {
    printHexByte(TEST_BYTES[i]);
    Serial.print(i + 1 == TEST_LENGTH ? '\n' : ' ');
  }

  FpgaUart.write(TEST_BYTES, TEST_LENGTH);
  FpgaUart.flush();

  const unsigned long deadline = millis() + 250;
  size_t received = 0;
  Serial.print("RX: ");
  while (static_cast<long>(deadline - millis()) > 0) {
    while (FpgaUart.available() > 0) {
      const uint8_t value = static_cast<uint8_t>(FpgaUart.read());
      printHexByte(value);
      Serial.print(' ');
      ++received;
    }
  }
  Serial.println();
  Serial.print("RX bytes: ");
  Serial.println(received);
  Serial.println();

  delay(750);
}
