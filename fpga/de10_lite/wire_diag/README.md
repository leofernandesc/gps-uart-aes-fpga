# Diagnóstico de continuidade UART da DE10-Lite

Este projeto de bancada copia diretamente `UART_RX` (JP1 pino físico 1,
`V10`) para `UART_TX` (JP1 pino físico 2, `W10`). Não contém receptor UART,
FIFO, AES ou guarda de contexto. `LEDR0` pisca com o clock de 50 MHz para
indicar que o bitstream foi carregado e está executando.

Compilar a partir desta pasta com `quartus_sh --flow compile uart_wire_diag`.
Programar `build/de10_lite/wire_diag/uart_wire_diag.sof` pelo USB-Blaster
identificado para a DE10-Lite. O CP2102 usa `TXD → V10`, `W10 → RXD` e GND
comum, sem jumper direto entre V10 e W10. Uma transmissão conhecida pelo
CP2102 deve aparecer idêntica na recepção do PC, sem depender de 50 MHz nem
da decodificação 8N1 pelo FPGA.

Este SOF serve apenas para localizar uma falha da bancada. A restrição SDC
exclui explicitamente o caminho assíncrono de pino a pino; seus números de
timing e recursos não participam do comparativo baseline/AES-CTR do artigo.
Para a montagem física e os limites dos ensaios, consulte
[`docs/bancada.md`](../../../docs/bancada.md) e
[`docs/results.md`](../../../docs/results.md).
