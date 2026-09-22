# ESP32 UART host — ESP-IDF

Este projeto usa o ESP-IDF para gerar e capturar o tráfego UART da DE10-Lite
ou da Cyclone IV sem um adaptador USB–UART externo.

## Pinagem

Para um ESP32 DevKit clássico com GPIO16 e GPIO17 disponíveis:

| ESP32 | DE10-Lite | Cyclone IV | Função |
| --- | --- | --- | --- |
| GPIO17 / TX2 | JP1 pino 1 / `V10` | J3 `PIN_103` | entrada `UART_RX` da FPGA |
| GPIO16 / RX2 | JP1 pino 2 / `W10` | J3 `PIN_100` | saída `UART_TX` da FPGA |
| GND | JP1 pino 12 ou 30 | GND do J3 | referência comum |

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

O modo padrão é `baseline`. Antes do ensaio `secure`, executar
`idf.py menuconfig`, abrir **FPGA UART bench host** e selecionar
**Secure: capture ciphertext**. Essa opção muda apenas a interpretação dos
contadores: o mesmo firmware sempre preserva e imprime os bytes recebidos.

## Comportamento

O firmware configura UART2 em 9600 baud, 8N1, envia repetidamente:

```text
55 A5 00 FF 3C
```

e mostra no monitor USB os bytes retornados pela FPGA. Cada tentativa:

- começa somente após uma janela de armamento de 10 s depois do boot;
- espera exatamente cinco bytes por até 30 ms;
- mantém uma guarda adicional de 10 ms para detectar bytes tardios ou
  duplicados;
- registra eventos de framing, paridade, overflow da FIFO UART do ESP32 e
  buffer cheio;
- começa a cada 1 s, sem somar o tempo de leitura ao período;
- não limpa a entrada entre tentativas, pois isso esconderia bytes tardios.

O log principal é estruturado para ser salvo e analisado depois:

```text
RESULT seq=1 mode=baseline tx=55A500FF3C rx=55A500FF3C rx_len=5 same=1 timeout=0 extra=0 frame_err=0 parity_err=0 fifo_ovf=0 buffer_full=0 break=0 write_err=0 tx_timeout=0 host_window_us=...
SUMMARY trials=1 timeouts=0 mismatches=0 extra_trials=0 capture_failures=0 ...
```

No top `baseline`, são exigidos cinco bytes iguais e nenhum erro. No top
`secure`, `same=0` é normalmente esperado: o ciphertext deve ser conferido no
PC com o contexto AES-CTR do ensaio, e não por sua aparência no terminal.
`host_window_us` mede a janela do driver e do escalonamento do ESP32; não é a
latência física da FPGA. A latência deve ser medida no osciloscópio usando RX e
TX como referências.

O código-fonte está em `main/uart_host_main.c`.

## Verificação automática do log

Salve a saída completa do monitor e execute, a partir da raiz do repositório:

```bash
make esp32-log-check \
  ESP32_LOG=data/private/de10-2026-09-22/baseline-monitor.log \
  BENCH_MODE=baseline \
  REPORT=data/private/de10-2026-09-22/baseline-report.json
```

Para o bring-up secure com o contexto público padrão, troque o modo para
`secure`. Para um ensaio com contexto próprio, acrescente
`CONTEXT_FILE=data/private/.../context.json`. O verificador exige quatro
linhas `RESULT`, sequência iniciando em 1 e consecutiva, cinco bytes por
tentativa e nenhum erro de transporte. No secure, ele concatena o ciphertext,
decifra AES-CTR de forma independente e compara com todos os bytes enviados.
Se o arquivo contiver reinicializações, somente a sessão iniciada pelo último
`ESP-IDF UART host ready` é analisada.

O [roteiro integrado da DE10-Lite](../../docs/bancada-de10-lite-integrada-2026-09-22.md)
define a ordem de programação, captura e medição no osciloscópio.

## Compatibilidade de placa

A pinagem acima é para o ESP32 clássico/DevKit que expõe GPIO16 e GPIO17. Se o
módulo disponível for ESP32-S2, S3, C3 ou uma placa sem esses GPIOs, confirme o
modelo antes de ligar: os pinos e a disponibilidade de UART2 podem mudar.
