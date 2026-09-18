# UART isolada na DE10-Nano

Este alvo reproduz o ensaio `uart_scope` da DE10-Lite na Terasic DE10-Nano.
Ele não inclui FIFO, AES ou GPS: gera o byte `0x55` a cada 100 ms e usa o
mesmo UART RTL em 50 MHz, 9600 baud e 8N1.

## Alvo e compilação

- FPGA: Cyclone V SoC `5CSEBA6U23I7`;
- projeto: `uart_scope.qpf`;
- top: `de10_nano_uart_scope_top`;
- saída: `build/de10_nano/uart_scope/uart_scope.sof`;
- comando: `make uart-fpga BOARD=de10_nano`.

O alvo usa somente a FPGA fabric. O UART-USB integrado da DE10-Nano pertence
ao caminho HPS/FT232R e não é usado neste teste; a observação do TX é feita
diretamente no GPIO com o osciloscópio.

## Pinagem usada

| Sinal | FPGA | Conector / função |
| --- | --- | --- |
| `FPGA_CLK1_50` | `PIN_V11` | clock de 50 MHz |
| `KEY0_N` | `PIN_AH17` | botão KEY0, reset ativo em nível baixo |
| `UART_RX` | `PIN_V12` | JP1 pino 1, `GPIO_0[0]` |
| `UART_TX` | `PIN_E8` | JP1 pino 2, `GPIO_0[1]` |
| `LED[0]` | `PIN_W15` | heartbeat |
| `LED[1]` | `PIN_AA24` | ao menos um TX iniciado |
| `LED[7:2]` | manual da placa | seis bits superiores do último RX |

Todos os GPIO utilizados são de 3,3 V. Para o loopback, ligar somente JP1
pino 2 (`UART_TX`) ao JP1 pino 1 (`UART_RX`) e usar um GND do mesmo header
(pino 12 ou 30). Não aplicar 5 V aos sinais.

## Ensaio no osciloscópio

1. Compilar e programar o `.sof` via USB-Blaster II/JTAG. Execute `jtagconfig`
   primeiro e use exatamente o nome do cabo que aparecer, normalmente
   `DE-SoC [USB-1]`.
2. Conectar a ponta do osciloscópio ao JP1 pino 2 e a garra de terra ao JP1
   pino 12 ou 30.
3. Soltar KEY0. O circuito envia `0x55` a cada 100 ms.
4. Medir a duração do bit, o quadro completo e o intervalo entre quadros.
5. Opcionalmente, ligar TX → RX e confirmar nos LEDs o padrão de `0x55`;
   para `0x55`, os LEDs correspondentes aos bits 6, 4 e 2 ficam ativos.

Com 50 MHz e divisor inteiro de 5.208 ciclos, os valores esperados são os
mesmos do teste da DE10-Lite:

- bit: aproximadamente `104,16 µs`;
- quadro 8N1: aproximadamente `1,0416 ms`;
- início dos quadros: aproximadamente `100 ms`.

Como clock, baud rate, formato e RTL são iguais, não esperamos diferença
protocolar entre as placas. A comparação relevante é a medição física do
nível alto/baixo, tempos de subida/descida, período observado e estabilidade
do quadro.

Este ensaio é uma caracterização auxiliar da UART na Cyclone V; ele não
substitui os quatro builds planejados para o artigo nem constitui validação
do GPS/AES-CTR.
