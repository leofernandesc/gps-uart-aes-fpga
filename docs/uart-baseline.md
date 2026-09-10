# UART revisado — contrato da baseline v2

Este documento registra o marco original do UART isolado. A ponte e a FIFO
foram acrescentadas depois, em módulos separados, conforme
[o marco Quartus](validacao-ponte-quartus-2026-09-07.md). O contrato abaixo e as
fontes do UART v2 permanecem válidos.

## O que mudou

| UART anterior | UART revisado | Motivo |
| --- | --- | --- |
| Tick de baud global compartilhado | Contador local em RX e TX, reiniciado por quadro | Remover a dependência da fase entre início do quadro e tick |
| Start do TX termina no próximo tick | Start, oito dados e stop duram um bit completo cada | Garantir temporização independentemente do instante do pedido |
| RX consulta o pino externo diretamente | Dois registradores em série antes da lógica RX | Reduzir o risco de propagação de metastabilidade |
| RX amostra nos ticks globais | Confirma start no meio do bit e amostra dados/stop a cada período | Alinhar a recepção ao quadro externo |
| Stop inválido é descartado silenciosamente | Pulso `rx_framing_error`; quadro não entregue | Tornar corrupção observável pelo futuro controle de sessão |
| Reset externo direto na lógica | Asserção assíncrona e liberação em dois clocks no top | Controlar a saída de reset no domínio de 50 MHz |
| Contador global de 32 bits | Contadores dimensionados para o divisor | Evitar largura desnecessária |
| Teste integrado alinhado ao DUT | Fonte e decodificador seriais independentes | Verificar o contrato externo, não reproduzir a mesma hipótese |

Não foi acrescentado oversampling 16×. O RX usa o clock de 50 MHz e uma amostra
por bit, aproximadamente central, relativa ao start já sincronizado. O circuito
de dois estágios não elimina a metastabilidade nem pode ser validado fisicamente
por simulação RTL; seu reconhecimento e suas restrições devem ser conferidos no
Quartus. Os atributos `preserve` não substituem a análise de CDC/timing.

## Interface de `uart_top`

Todos os sinais internos de controle e dados pertencem ao domínio de `clk`.
`rx` e `rst` são as entradas assíncronas tratadas pelo módulo.

| Sinal | Contrato |
| --- | --- |
| `clk` | 50 MHz na implementação final |
| `rst` | Ativo em nível alto; descarta quadro RX/TX em andamento |
| `tx_data[7:0]` | Byte a enviar, estável na borda de aceitação |
| `tx_start` | Pedido aceito na borda de subida em que `tx_ready=1` |
| `tx_ready` | Pode aceitar um byte; fica baixo no reset e durante transmissão |
| `tx_busy` | Alto desde a aceitação até completar o stop bit |
| `tx_done` | Pulso de um clock após os dez bits completos |
| `tx` | Repouso em 1, start em 0, dados LSB-first, um stop em 1 |
| `rx` | Entrada externa 8N1, sem controle de fluxo |
| `rx_data[7:0]` | Byte recebido; só muda em reset ou junto a `rx_done` |
| `rx_done` | Pulso de um clock ao validar o centro do stop bit |
| `rx_framing_error` | Pulso de um clock quando o stop é baixo; sem `rx_done` |

Não há fila de pedidos no TX. Um pulso de `tx_start` durante `tx_busy` é ignorado.
Se `tx_start` permanecer alto até uma borda com `tx_ready=1`, haverá nova
aceitação: a interface é um handshake por nível, não um detector de bordas.
O primeiro pedido seguinte pode ser aceito no clock imediatamente após `tx_done`.

O RX não tem `ready`: dados de um GPS não podem ser pausados por esta interface.
A próxima etapa deve escrever cada `rx_done` na FIFO e sinalizar overflow quando
ela estiver cheia. **FIFO e contador de perdas ainda não existem neste marco.**

## Reset, ruído e recuperação

- Após reset ou erro de stop, o RX exige nível alto contínuo por um bit antes de
  voltar a aceitar um start. Não iniciar a captura antes desse repouso inicial.
- Um pulso baixo que já voltou a alto no centro do start é ignorado.
- Um break contínuo após um quadro inválido gera um único erro, não uma sequência
  de bytes zero. O RX aguarda repouso válido para rearmar.
- Um reset interrompe o TX e força a linha alta sem gerar `tx_done` para o byte
  incompleto. O quadro parcial no receptor externo deve ser descartado.
- Isso não é um protocolo de recuperação de pacotes. Na futura sessão CTR,
  framing/overflow/reset invalidarão a aquisição e exigirão reinicialização
  explícita da sessão com nonce novo.

## Constantes e integração futura

`uart_top` mantém os parâmetros de elaboração `CLK_FREQ` e `BAUD_RATE` para
compatibilidade com o projeto anterior e aceleração dos testes. Defaults:
50.000.000 e 9.600; divisor inteiro 5.208. A placa usará apenas esses defaults.
Os módulos RX/TX recebem `CLKS_PER_BIT` como constante de elaboração, sem
registrador de configuração, switch ou multiplexador de taxas.

O `baud_gen` antigo não é mais necessário no caminho de produção.
Os dois contadores locais são enables temporais: **não geram novos clocks**.
O formato é sempre 8N1; não há paridade, RTS/CTS ou filtro de ruído por votação.

Na integração, `uart_top` pode ser usado como porta completa para o adaptador de
controle/saída. Um segundo `uart_rx` atenderá o GPS, recebendo o mesmo reset
sincronizado do domínio de 50 MHz. Isso evita criar dois domínios desnecessários.

O comparativo científico utilizará esta versão corrigida em ambos os caminhos,
com a mesma FIFO e o mesmo protocolo. A versão histórica é referência de
proveniência, **não** o comparador experimental de custo do AES.
