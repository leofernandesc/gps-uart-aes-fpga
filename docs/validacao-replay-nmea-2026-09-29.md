# Replay NMEA em clock de produção — 29/09/2026

## Configuração

- RTL: baseline e secure na mesma ponte UART–FIFO–CTR.
- Clock: 50 MHz; UART 38400/8N1, 1.302 ciclos de clock por bit.
- Entrada: fixture NMEA pública/sintética, cinco sentenças, 309 bytes com CRLF.
- Comando: `make integration-gps`.

## Resultado

| Medida RTL | Baseline | Secure |
| --- | ---: | ---: |
| Bytes recebidos/transmitidos | 309/309 | 309/309 |
| Verificação independente no PC | PASS, eco idêntico | PASS, texto decifrado idêntico |
| Divergências / overflow | 0 / 0 | 0 / 0 |
| Ocupação máxima da FIFO | 1 byte | 1 byte |
| `rx_valid` até início TX | 80 ns | 80 ns |
| `rx_valid` até fim do quadro TX | 260.480 ns | 260.480 ns |
| Início quadro RX até início TX | 247.503 ns | 247.503 ns |

As métricas são de simulação RTL em clock de produção e usam a saída serial
decodificada por um verificador independente; não são captura elétrica nem
aquisição GPS física. A entrada é sintética e não comprova o NEO-M8N. Em 38400
baud, um quadro 8N1 de dez bits tem duração nominal aproximada de 260,4 µs.

## Reproduzir

```bash
make integration-gps
```

Os logs completos e dumps ficam em `build/`, ignorados pelo Git. Este registro
descreve a simulação de 29/09; o par de builds daquela data está preservado em
[`metricas-fpga-2026-09-29.md`](metricas-fpga-2026-09-29.md). As métricas
selecionadas para o artigo estão em
[`metricas-fpga-2026-09-30.md`](metricas-fpga-2026-09-30.md). A aquisição física
do NEO-M8N foi validada posteriormente em P07, P12 e P13, com os resultados e
limites de cada ensaio registrados em [`plano-de-testes.md`](plano-de-testes.md).
