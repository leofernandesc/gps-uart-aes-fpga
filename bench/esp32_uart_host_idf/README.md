# ESP32 UART host — ESP-IDF

Este projeto usa o ESP-IDF para gerar e capturar o tráfego UART da Cyclone IV
sem um adaptador USB–UART externo.

## Pinagem

Para um ESP32 DevKit clássico com GPIO16 e GPIO17 disponíveis:

| ESP32 | Cyclone IV | Função |
| --- | --- | --- |
| GPIO17 / TX2 | J3 `PIN_103` | entrada `UART_RX` da FPGA |
| GPIO16 / RX2 | J3 `PIN_100` | saída `UART_TX` da FPGA |
| GND | GND do J3 | referência comum |

O USB do ESP32 é usado somente para programação e para o log no PC. As duas
placas devem ser alimentadas separadamente. Não conectar `5V` ou `3V3` de uma
placa à outra.

## Compilar e gravar

```bash
cd bench/esp32_uart_host_idf
source /home/leofernandesc/.espressif/v6.0.2/esp-idf/export.sh
idf.py set-target esp32
idf.py build
idf.py -p /dev/ttyUSB0 flash
idf.py -p /dev/ttyUSB0 monitor -b 115200
```

Substitua `/dev/ttyUSB0` pelo dispositivo que aparecer no Linux. O comando
`flash` altera apenas o firmware do ESP32; não altera a configuração da FPGA.

## Comportamento

O firmware configura UART2 em 9600 baud, 8N1, envia repetidamente:

```text
55 A5 00 FF 3C
```

e mostra no monitor USB os bytes retornados pela FPGA. No top `baseline`, o
esperado é o mesmo vetor na saída. No top `secure`, o esperado é um ciphertext;
a conferência deve ser feita com o contexto AES-CTR correspondente, não pela
aparência do texto no terminal.

O código-fonte está em `main/uart_host_main.c`.

## Compatibilidade de placa

A pinagem acima é para o ESP32 clássico/DevKit que expõe GPIO16 e GPIO17. Se o
módulo disponível for ESP32-S2, S3, C3 ou uma placa sem esses GPIOs, confirme o
modelo antes de ligar: os pinos e a disponibilidade de UART2 podem mudar.
