# DE10-Lite baseline

Este projeto implementa a referência sem cifra usada no artigo:

```text
UART RX -> FIFO -> UART TX
```

Parâmetros fixos: clock de 50 MHz, UART 9600 baud/8N1, dispositivo
`10M50DAF484C7G`, RX no `V10` e TX no `W10`.

O contexto de configuração é aceito automaticamente pelo wrapper após o reset.
No baseline, `ENABLE_AES=0` remove o AES durante a elaboração. O fluxo não
possui parser NMEA nem protocolo de configuração pela UART.

Na raiz do repositório:

```bash
make baseline-fpga
```

O SOF é gerado em `build/de10_lite/baseline/uart_baseline.sof`. A compilação
não programa a placa.
