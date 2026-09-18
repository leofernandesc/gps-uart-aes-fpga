# UART isolada: osciloscópio e recepção por jumper

Abrir `uart_scope.qpf` no Quartus ou, na raiz do repositório:

```bash
make uart         # RX, TX, top e gerador de bancada; simulação, lint e estrutura
make uart-waves   # build/uart_top.vcd e build/uart_scope.vcd
make uart-fpga    # síntese, fit, SOF e auditoria temporal da UART de bancada
```

O executor HDL usa a imagem Docker local quando as ferramentas nativas não
estiverem disponíveis. `make uart` não requer os vetores ou fontes de AES/CTR.
O `.sof` está em `build/de10_lite/uart_scope/uart_scope.sof`; seu status deve
ser `PASS` no `build-status.txt` da mesma pasta antes de carregar no Programmer.
Um arquivo SOF antigo pode permanecer no disco após uma compilação que falhou.

## O que esse circuito faz

O gerador interno envia **0x55 a cada 100 ms**, independentemente de RX.
O sinal sai em **9600 baud, 8N1**, LSB primeiro, usando o clock de 50 MHz.
Há UART RX/TX, reset sincronizado, temporizador de estímulo, um heartbeat no
`LEDR[0]` e LEDs de diagnóstico. `LEDR[1]` registra o início de uma transmissão.
Não há FIFO, AES, GPS ou retransmissão automática nesse projeto.

```text
temporizador + byte 0x55 → UART TX → pino TX → osciloscópio
                                        │
                                  jumper opcional
                                        ↓
LEDs ← UART RX ← pino RX ←───────────────┘
```

`make fpga` continua compilando o projeto separado RX → FIFO → TX; para este
ensaio, selecione `uart_scope.qpf` ou `make uart-fpga`.

## Ligações

| Medição/conexão | Posição acessível em JP1 | Pino FPGA |
| --- | --- | --- |
| TX / ponta do CH1 | **2**, GPIO[1] | W10 |
| RX / jumper vindo de TX | **1**, GPIO[0] | V10 |
| GND / garra de terra | **12 ou 30** | Terra da placa |

Conferir a orientação do pino 1 no conector. W10/V10 são nomes dos contatos do
encapsulamento; medir no JP1. A garra de terra vai ao GND. Alimentar e programar
a placa normalmente. Os GPIOs são de 3,3 V. Quando usar o jumper TX → RX,
deixar GPS e qualquer outro transmissor desconectados desse RX.

Pinagem conferida no [manual Terasic da DE10-Lite, pp. 24–27 e 30–31](https://www.mouser.com/datasheet/2/598/DE10-Lite_User_Manual-1100361.pdf).

## Teste 1: somente TX e osciloscópio

1. Programar o SOF e pressionar/soltar KEY0. A transmissão começa após cerca de
   100 ms e se repete; não é preciso adaptador USB–UART.
2. Usar ponta ×10 (com o fator correspondente no instrumento), acoplamento DC,
   cerca de 1 V/div e 200 µs/div para ver o quadro inteiro.
3. Usar trigger de descida próximo de 1,6 V; captura Single/Normal. Se o trigger
   prender em um bit de dados, usar holdoff maior que o quadro (por exemplo 2 ms)
   ou trigger de início UART, se o instrumento oferecer.
4. Conferir níveis baixo/alto, start, oito dados e stop. O quadro esperado é:

   ```text
   repouso  start   d0 d1 d2 d3 d4 d5 d6 d7  stop  repouso
      1       0     1  0  1  0  1  0  1  0    1      1
   ```

   O bit dura **104,16 µs**, o quadro **1,0416 ms** e o intervalo entre starts
   consecutivos **100 ms**. Para a repetição, usar uma base de tempo maior.
   No decodificador UART, selecionar 9600 / 8N1 / polaridade normal; esperar
   `0x55` (ASCII `U`). Estes valores são previstos pelo RTL, a medir na bancada.

## Teste 2: RX por jumper externo

1. Ligar JP1 pino 2 (TX) ao pino 1 (RX) e resetar com KEY0.
2. O `LEDR[0]` deve alternar continuamente, mesmo sem jumper, confirmando
   clock, configuração e ligação dos LEDs.
3. Após cerca de 100 ms, `LEDR[1]` deve acender e permanecer aceso, confirmando
   que o transmissor iniciou pelo menos um quadro.
4. Depois de um quadro válido, `LEDR[7:2]` mostra os bits 7:2 de `0x55`,
   portanto os LEDs 2, 4 e 6 ficam ativos.
5. LED 8 acende após receber um quadro válido. LED 9 deve ficar apagado.

| LEDs | Significado neste projeto |
| --- | --- |
| 0 | Heartbeat do clock; não faz parte do byte recebido |
| 1 | Pelo menos um quadro TX iniciado desde o reset |
| 7:2 | Bits 7:2 do último byte recebido |
| 8 | Pelo menos um quadro com stop válido recebido desde o reset |
| 9 | Erro persistente: stop inválido **ou** byte diferente de 0x55 |

LED 8 sozinho não é aprovação: um byte diferente de 0x55 acende também LED 9.
Sem jumper/fonte, LED 8 apagado é esperado, mas o heartbeat do LED 0 continua.
O teste não possui timeout de RX;
desconectar o jumper depois de um acerto não apaga o LED 8. Resetar a cada ensaio.

O jumper verifica o caminho pelos pinos, mas RX e TX compartilham o mesmo
clock. Complementar com fonte UART independente (GPS, gerador digital ou
microcontrolador) para testar a recepção assíncrona. Nesse caso, LEDs 7:2
mostram os bits 7:2 do byte da fonte, com os LEDs 0 e 1 reservados ao heartbeat
e ao diagnóstico de TX;
LED 9 também acende para bytes diferentes do padrão.
RX não é ecoado para TX neste projeto.

## Registro mínimo

Guardar SHA do commit, versão Quartus, hash do SOF, foto das ligações e captura
do osciloscópio com escalas. Anotar duração do bit/quadro e os LEDs após reset
e loopback. Somente então marcar a bancada no cronograma como concluída.

GTKWave exibe ondas de simulação. As saídas `build/uart_top.vcd` e
`build/uart_scope.vcd` contêm sinais públicos para evitar arquivos enormes com
50 milhões de transições de clock por segundo. O teste automatizado confere a
duração dos bits, período de 100 ms, RX independente, erros e reset.

O relatório de recursos deste top inclui gerador e LEDs. Ele não substitui o
baseline GPS/FIFO/controle usado para medir o custo do AES no artigo.
