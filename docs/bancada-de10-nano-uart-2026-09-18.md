# Ensaio auxiliar da UART na DE10-Nano

**Data:** 18/09/2026
**Status:** compilação concluída; programação e medição física pendentes.

Este ensaio repete, em uma FPGA Cyclone V, o teste isolado da UART já
realizado na DE10-Lite. O objetivo é verificar se o mesmo RTL mantém o quadro
serial e registrar diferenças elétricas ou temporais observadas no
osciloscópio. Ele é uma caracterização auxiliar e não substitui a validação
do sistema GPS/AES-CTR do artigo.

## Configuração

| Item | Valor |
| --- | --- |
| Placa | Terasic DE10-Nano |
| Dispositivo Quartus | `5CSEBA6U23I7` |
| Clock da FPGA | 50 MHz |
| UART | 9600 baud, 8N1 |
| Estímulo automático | `0x55` a cada 100 ms |
| Projeto | `fpga/de10_nano/uart_scope/` |
| Saída | `build/de10_nano/uart_scope/uart_scope.sof` |

## Resultado da compilação

O Quartus Prime 25.1 Standard concluiu síntese, fitting, assembler e análise
temporal. O auditor de constraints passou nos quatro cantos de timing.

| Métrica | Resultado |
| --- | ---: |
| ALMs | 101 |
| Registradores | 127 |
| RAM, DSP e PLL | 0 |
| Fmax reportada | 192,98 MHz |
| Pior setup slack | 14,818 ns |
| Pior hold slack | 0,168 ns |
| `.sof` | gerado |

O fitter registrou apenas avisos não bloqueantes sobre licença do LogicLock e
slew rate não especificado para algumas saídas; não houve erro de síntese,
fitting, assembler ou timing.

## Pinagem do ensaio

| Sinal | Pino FPGA | Conexão |
| --- | --- | --- |
| `FPGA_CLK1_50` | `V11` | clock de 50 MHz |
| `KEY0_N` | `AH17` | reset ativo em nível baixo |
| `UART_RX` | `V12` | JP1 pino 1 (`GPIO_0[0]`) |
| `UART_TX` | `E8` | JP1 pino 2 (`GPIO_0[1]`) |
| GND | — | JP1 pino 12 ou 30 |

Para medir, ligar a ponta do osciloscópio ao JP1 pino 2 e a referência ao GND
do mesmo header. O loopback opcional liga JP1 pino 2 ao pino 1. Não aplicar 5 V
nos GPIO.

## Procedimento físico pendente

1. Conectar o USB-Blaster/JTAG da DE10-Nano ao computador.
2. Confirmar o cabo com `jtagconfig`.
3. Programar `build/de10_nano/uart_scope/uart_scope.sof`.
4. Soltar `KEY0` e observar o `UART_TX` no osciloscópio.
5. Registrar a duração do bit, a duração do quadro, o intervalo entre quadros,
   níveis alto/baixo e tempos de subida/descida.
6. Repetir com o loopback TX→RX e registrar o comportamento dos LEDs.

## Valores esperados e comparação

| Medição | Esperado | DE10-Nano | Referência DE10-Lite |
| --- | ---: | ---: | ---: |
| Bit UART | 104,16 µs | pendente | 104,22 µs |
| Quadro 8N1 | 1,0416 ms | pendente | aproximadamente 1,042 ms |
| Intervalo entre inícios | 100 ms | pendente | 100 ms |

Como clock, divisor, formato e RTL são iguais, a comparação não busca uma
diferença protocolar. O que deve ser observado é o comportamento elétrico do
pino e a estabilidade temporal do quadro em cada placa.

## Reprodução

```text
make de10-nano-uart-fpga
jtagconfig
quartus_pgm -c '<cabo exibido pelo jtagconfig>' -m jtag \
  -o 'p;build/de10_nano/uart_scope/uart_scope.sof'
```

O build foi gerado sem programação automática da placa. Até a execução do
procedimento acima, não há resultado físico da DE10-Nano a declarar.
