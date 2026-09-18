# Bancada DE10-Lite — 18/09/2026

## Estado do ensaio

| Etapa | Resultado | Evidência |
| --- | --- | --- |
| USB-Blaster detectado | **Concluído** | `jtagconfig`: `USB-Blaster [1-3]` |
| Dispositivo identificado | **Concluído** | JTAG ID `0x031050DD`; `10M50DA(.\|ES)/10M50DC` |
| Quartus da UART autônoma | **Concluído** | `make uart-fpga`; 0 erros, 2 avisos de I/O |
| Timing do projeto | **Concluído** | Três cantos auditados, nenhum caminho violado |
| SOF programado | **Concluído** | `quartus_pgm`: configuração de `10M50DAF484@1` bem-sucedida |
| TX medido no osciloscópio | **Pendente** | Executar Teste 1 abaixo |
| RX por loopback TX → RX | **Pendente** | Executar Teste 2 abaixo |
| GPS real | **Pendente** | Depende da integração baseline/secure e da captura serial |

Este marco comprova que o computador, Quartus, USB-Blaster e FPGA estão
conectados e que o SOF foi aceito pelo dispositivo. Ainda não comprova a forma
de onda no pino, a recepção UART nem o funcionamento do GPS.

## Configuração utilizada

- Placa: DE10-Lite com MAX 10 `10M50DAF484C7G`;
- clock: 50 MHz;
- UART: 9600 baud, 8N1;
- projeto: `fpga/de10_lite/uart_scope/uart_scope.qpf`;
- top: `de10_lite_uart_scope_top`;
- circuito: gerador de `0x55` → UART TX e UART RX para os LEDs;
- SOF: `build/de10_lite/uart_scope/uart_scope.sof`;
- SHA-256 do SOF: `3aa552c5004c35cb42602608ec8c2ab387418a98789f9bb0d080f543c7e6ec5f`;
- Quartus Prime: 25.1std.0 Build 1129;
- fonte: commit `a7127b0` antes do teste físico.

O SOF foi carregado por JTAG e é volátil. Após desligar a placa, será necessário
programá-lo novamente, salvo se ele for gravado posteriormente na configuração
não volátil.

## Resultado do Quartus

O fit selecionou o dispositivo correto e terminou sem erros. O relatório pós-fit
indicou 213 elementos lógicos, 95 registradores, 14 pinos utilizados e nenhum
bloco de memória/PLL neste top. Esses números são da UART autônoma, não do
projeto GPS com FIFO e AES-CTR.

| Análise | Pior margem | Canto |
| --- | ---: | --- |
| Setup | `12,824 ns` | slow 1200 mV, 85 °C |
| Hold | `0,148 ns` | fast 1200 mV, 0 °C |
| Recovery | `16,773 ns` | slow 1200 mV, 85 °C |
| Removal | `0,427 ns` | fast 1200 mV, 0 °C |

O clock de 50 MHz tem período de 20 ns. A análise temporal ficou totalmente
constrained para setup e hold. O Quartus emitiu dois avisos de requisito de
I/O de 3,3 V no fit; eles são avisos do banco/pinos e devem ser mantidos na
revisão da pinagem, não ignorados em um projeto com GPS conectado.

## Teste 1 — TX no osciloscópio

### Ligações

1. Manter o SOF programado e pressionar/soltar `KEY0` para resetar.
2. Conectar a ponta do canal 1 ao `JP1` pino 2, `GPIO[1]` / `UART_TX`.
3. Conectar a garra de terra ao `JP1` pino 12 ou 30.
4. Não conectar GPS nem outro transmissor ao `UART_RX` durante este teste.

Usar ponta ×10, acoplamento DC, aproximadamente 1 V/div e 200 µs/div para
capturar um quadro. Trigger de descida próximo de 1,6 V. Para observar o
intervalo entre quadros, aumentar a base de tempo; o gerador repete o byte a
cada 100 ms.

### O que deve ser observado

O gerador envia `0x55` (`01010101`), LSB first, em 8N1:

```text
repouso  start   d0 d1 d2 d3 d4 d5 d6 d7  stop
   1       0     1  0  1  0  1  0  1  0    1
```

Valores nominais calculados a partir do RTL:

- bit: `50.000.000 / 5.208 = 9.608,3 baud`, aproximadamente `104,16 µs`;
- quadro: 10 bits, aproximadamente `1,0416 ms`;
- início do próximo quadro: aproximadamente `100 ms` depois.

Registrar na tabela abaixo os valores do instrumento. O teste só deve ser
marcado como aprovado depois de salvar uma captura com escala, nível baixo,
nível alto, start, oito bits e stop identificáveis.

| Medida | Esperado | Medido | Evidência |
| --- | ---: | ---: | --- |
| Período do bit | ~104,16 µs | — | captura do osciloscópio |
| Duração do quadro | ~1,0416 ms | — | captura do osciloscópio |
| Nível baixo/alto | compatível com I/O 3,3 V | — | captura do osciloscópio |
| Intervalo entre starts | ~100 ms | — | captura de repetição |
| Decodificação | `0x55`, 9600/8N1 | — | decodificador/instrumento |

## Teste 2 — loopback TX → RX

1. Desconectar a ponta do TX se ela atrapalhar o acesso ao conector.
2. Ligar `JP1` pino 2 (`UART_TX`) diretamente ao `JP1` pino 1 (`UART_RX`).
3. Resetar com `KEY0` e esperar pelo menos um quadro.
4. Conferir os LEDs.

Resultado esperado:

- `LEDR[0]` alterna como heartbeat independente da UART;
- `LEDR[7:1]` registra os bits 7:1 de `0x55`, portanto LEDs 2, 4 e 6 ativos;
- LED 8 aceso: pelo menos um quadro válido recebido;
- LED 9 apagado: nenhum framing error e nenhum byte diferente de `0x55`.

| Observação | Resultado |
| --- | --- |
| `LEDR[0]` alterna como heartbeat | — |
| `LEDR[7:1]` mostram os bits 7:1 de `0x55` | — |
| LED 8 acende | — |
| LED 9 permanece apagado | — |
| Resultado do loopback | Pendente |

Resetar antes de repetir o ensaio. O LED 8 é retido depois de uma recepção
válida; portanto, não desligar o jumper e concluir que o RX continua recebendo.
O loopback confirma o caminho pelos pinos da placa, mas não substitui um teste
com uma fonte UART independente.

## Próximo passo após os dois testes

Com TX e RX confirmados, programar o futuro wrapper baseline da arquitetura
GPS e testar primeiro a retransmissão sem AES. Depois carregar a variante com
AES-CTR, provisionar chave/nonce por uma interface definida no wrapper e usar o
PC para comparar os bytes recuperados. Esses projetos ainda não têm SOF de
bancada; não usar o SOF `uart_scope` como evidência do sistema integrado.

## Reprodução do marco

```bash
make uart-fpga
sha256sum build/de10_lite/uart_scope/uart_scope.sof
jtagconfig
quartus_pgm -c 'USB-Blaster [1-3]' -m jtag \
  -o 'p;build/de10_lite/uart_scope/uart_scope.sof'
```

Fontes e relatórios utilizados estão identificados no manifesto
[`de10-lite-uart-scope-2026-09-18.sha256`](evidence/de10-lite-uart-scope-2026-09-18.sha256).
