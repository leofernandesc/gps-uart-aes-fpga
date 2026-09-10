# Primeiro teste na DE10-Lite — ponte sem cifra

Abrir `uart_bridge.qpf` no Quartus ou executar `make fpga` na raiz do projeto.
O resultado é `build/quartus/uart_bridge.sof`. Compilar não exige placa;
programar e validar o sinal externo exigem a montagem real.

O top `de10_lite_uart_top` fixa 50 MHz, 9600 baud, 8N1 e FIFO de 1.024 bytes.
KEY0 reinicia RX, TX, FIFO e diagnósticos. Pressionar e soltar KEY0 depois de
carregar o `.sof`; deixar a entrada em repouso alto por pelo menos um bit antes
de enviar a primeira mensagem.

## Pinagem do build

| Sinal | Recurso da DE10-Lite | Pino FPGA | Uso |
| --- | --- | --- | --- |
| `MAX10_CLK1_50` | Oscilador de 50 MHz | P11 | Clock interno |
| `KEY0_N` | Botão KEY0 | B8 | Reset ativo baixo |
| `GPS_RX` | GPIO[0], pino físico 1 de JP1 | V10 | Entrada serial do GPS ou de uma fonte de teste |
| `UART_TX` | GPIO[1], pino físico 2 de JP1 | W10 | Saída serial para o PC |
| GND | Pino físico 12 ou 30 de JP1 | — | Referência comum dos sinais |

Fonte: manual da **Terasic**, edição de 05/06/2020, pp. 5, 24–27 e 30–31
([PDF hospedado pela Mouser](https://www.mouser.com/datasheet/2/598/DE10-Lite_User_Manual-1100361.pdf)).
GPIO[0] e GPIO[1] são escolhas deste projeto entre os pinos livres do conector.
Confirmar a orientação do pino 1 na placa. O receptor foi identificado pelo usuário
como NEO-M8N-010; a pinagem do conector de sua placa de suporte ainda precisa ser
conferida fisicamente.

Os sinais usam I/O de 3,3 V; KEY0 usa o padrão Schmitt Trigger da placa. A RX
tem pull-up fraco para manter repouso quando desconectada. A força de saída de
UART/LEDs foi explicitada em 8 mA, igual ao default observado no primeiro fit.
Os GPIOs não usados são entradas em alta impedância.

## Como testar quando a placa chegar

1. Usar o Programmer para carregar o `.sof` por JTAG e reiniciar com KEY0.
2. Fazer inicialmente PC → fonte UART 3,3 V → `GPS_RX` → FPGA → `UART_TX` →
   receptor USB do PC. Um adaptador USB–UART full-duplex pode atender esse
   loopback; um microcontrolador com ponte serial verificada também pode servir.
3. Enviar uma sequência conhecida em modo binário e conferir os bytes devolvidos,
   sem conversão de fim de linha ou eco local no terminal. LEDs 6 e 7 devem
   permanecer apagados. Um eco visual sozinho não verifica perda de dados.
4. Depois, substituir a fonte de teste pelo GPS M8 e capturar em paralelo o sinal
   original para comparação. Essa comparação requer um segundo canal de captura,
   como discutido em [bancada](../../docs/bancada.md).

O cabo USB do USB-Blaster atende à programação; esta implementação transporta os
dados pelos pinos UART. O software automatizado de captura ainda será escrito.

## Indicadores

| LED | Significado |
| --- | --- |
| 0 | Reset liberado |
| 1 / 2 | Alterna a cada byte recebido / transmissão concluída |
| 3 | Há bytes na FIFO |
| 4 | TX ocupado |
| 5 | FIFO cheia neste instante |
| 6 | Ocorreu overflow desde o último reset |
| 7 | Ocorreu erro de stop desde o último reset |
| 8 / 9 | Ocupação máxima atingiu 512 / 1.024 bytes |

Os indicadores de atividade podem parecer acesos ou com brilho médio sob fluxo
rápido. LEDs são diagnóstico visual, não contadores de bytes nem medição de
latência. A ocupação máxima exata existe no core; esta versão ainda não a exporta
ao PC. Overflow descarta o byte novo; os bytes já guardados mantêm sua ordem.
Uma captura com LED 6 ou 7 aceso é inválida, mesmo se o tráfego continuar.

## Interface da FIFO e da ponte

`sync_fifo` aceita escrita quando há espaço, inclusive no ciclo de leitura de
uma fila cheia. Leitura aceita entrega `rd_data` com `rd_valid` após a borda;
leitura da fila vazia não faz bypass de uma escrita simultânea. O teste cobre
leitura/escrita no mesmo endereço com devolução do dado antigo. A RAM não é
zerada no reset, mas seus dados ficam invalidados pelos ponteiros/contagem.

A ponte reserva o TX enquanto aguarda a leitura síncrona da FIFO. Seu
`tx_enable` interno pode pausar novos pedidos; um pedido já aceito será
transmitido. No top da placa ele está fixo em 1. A FIFO não pausa o GPS nem
compensa indefinidamente uma entrada cuja taxa média exceda a capacidade de saída.

## Alcance da análise temporal

O SDC define o clock de 20 ns e exceções apenas para a entrada assíncrona até
os primeiros registradores de sincronização e para as saídas assíncronas UART/LED.
RX meta → sync e liberação interna de reset continuam sujeitos a timing.
O script verifica setup, hold, recovery e removal nos três cantos disponíveis,
falha com slack negativo/cobertura ausente e verifica caminhos sem restrição.

`check_timing` ainda lista ausência de delays síncronos para dois pinos de
entrada, onze saídas e ausência de clock virtual. Isso é esperado neste contrato
assíncrono e não foi ocultado com delays fictícios. A auditoria só aceita essas
quantidades; outros problemas interrompem `make fpga`. Timing externo dos cabos,
níveis elétricos, erros de transmissão e recepção de GPS real ficam para a bancada.
