# Execução e submissão até 25/09 — setembro de 2026

Objetivo: adquirir GPS NEO-M8N-010 por UART e medir o custo do AES-128-CTR em
DE10-Lite/MAX 10 e Cyclone IV, com um build sem cifra e outro com cifra por
placa. **Submissão em 24/09; contingência e encerramento em 25/09.**

## Situação em 20/09/2026

UART, FIFO, AES e CTR estão integrados em um módulo comum para baseline e
secure. A saída serial foi comparada no PC, incluindo simulação em 50 MHz/9600.
O gravador/comparador binário passou em testes com porta virtual Linux.
Em 18/09, a DE10-Lite foi identificada, o SOF `uart_scope` foi recompilado e
programado, e TX no osciloscópio e loopback TX→RX foram concluídos. Os tops
integrados `baseline` e `secure` estão separados em projetos Quartus e seus
builds foram concluídos, com recursos e timing registrados. Não há registro de
aquisição GPS.

A documentação anterior foi consolidada em 15/09; suas simulações e compilações
UART foram executadas na noite de 14/09, conforme o relatório de revisão.

Decisão arquitetural em 15/09: retirar o bloco de sessão do datapath. O fluxo
principal passa a ser `GPS → UART RX → FIFO → passagem direta ou AES-CTR → UART
TX → PC`; chave, nonce e tamanho da captura ficam registrados como parâmetros
do experimento no PC.

A integração prevista inicialmente para 13/09 foi validada em RTL em 16/09.
A bancada prevista para 15/09 foi reagendada: a DE10-Lite foi disponibilizada
em 18/09, identificada, programada e validada no TX/loopback. Software, os
builds MAX 10 e o artigo seguem em paralelo, mantendo o encerramento em 25/09.

| Data | Entrega | Critério de conclusão | Situação |
| --- | --- | --- | --- |
| 07–10/09 | UART, FIFO, AES e CTR isolados | Testes e evidências dos marcos abaixo | Concluído em RTL; ponte e AES analisados no Quartus |
| 14/09 | Revisão e teste UART autônomo | Simulação, SOF e timing do alvo UART; documentação revisada | Concluído em simulação e Quartus |
| 16–18/09 | UART na DE10-Lite | Captura TX no osciloscópio, 0x55/104,16 µs, RX por jumper e indicadores registrados | Concluído em 18/09 — relatório da bancada |
| 16–17/09 | Identificar Cyclone IV | Modelo, part number, clock, pinos e esquema confirmados | Pendente — Leonardo; reagendado de 15/09 |
| 16/09 | Integração RTL e comparador | Replay serial recuperado sem divergências nos dois modos; testes PC | Concluído em simulação/PTY; ver marco abaixo |
| 17–18/09 | Contexto e preparação dos builds | Wrapper carrega contexto de bring-up e projetos baseline/secure separados | Concluído para DE10-Lite — aplicação de contexto privado validada em 20/09 |
| 18/09 | Builds DE10-Lite | Baseline/secure com recursos e timing rastreáveis | Concluído — dois SOFs, recursos e timing registrados |
| 19/09 | Contexto e registro no PC | Contextos privados e registro persistente de nonces testados | Concluído — `make context` e `make pc` |
| 20/09 | Replay NMEA | Fixture público validado e integrado ao ensaio RTL/PC | Concluído em simulação/PC; GPS físico pendente |
| 19–20/09 | Experimentos | Três replays físicos por configuração e captura GPS contínua com comparação byte a byte | Pendente — bancada/verificação |
| 21–22/09 | Resultados e manuscrito | Tabelas, gráficos, discussão de latência/taxa útil e versão completa | Pendente — artigo |
| 23/09 | Revisão com orientador | Comentários incorporados e versão congelada | Pendente |
| 24/09 | Submissão principal | Envio e comprovante preservados | Pendente |
| **25/09** | **Contingência e encerramento** | **Correções de envio, eventual reenvio e confirmação final** | **Pendente** |

A chamada pública do BTSym consultada em 14/09 informa 30/09/2026 como prazo
externo. Confirmar modalidade e template no portal antes do envio. O planejamento
interno termina em 25/09 independentemente dessa folga.
[Chamada de trabalhos](https://lcv.fee.unicamp.br/virtual-btsym26-home/btsym26-call-for-paper/).

## Marco em 18/09: DE10-Lite conectada e programada

- `jtagconfig` encontrou `USB-Blaster [1-3]` e o dispositivo `10M50DA(.|ES)/10M50DC`,
  com JTAG ID `0x031050DD`.
- `make uart-fpga` recompilou o top autônomo para `10M50DAF484C7G` com Quartus
  Prime 25.1std.0 Build 1129. O fit terminou sem erros; o relatório indicou
  213 elementos lógicos, 95 registradores e 14 pinos.
- O timing foi auditado nos três cantos, sem violações: pior setup `12,824 ns`,
  hold `0,148 ns`, recovery `16,773 ns`, removal `0,427 ns`.
- O SOF SHA-256 `3aa552c5004c35cb42602608ec8c2ab387418a98789f9bb0d080f543c7e6ec5f`
  foi programado por JTAG; o Quartus confirmou configuração bem-sucedida de
  `10M50DAF484@1`.
- A forma de onda do TX e o loopback TX→RX foram observados e registrados:
  bit de `104,22 µs`, quadro de aproximadamente `1,042 ms`, intervalo de `0,1 s`
  e loopback aprovado. Portanto, a UART autônoma física está `Concluída`.

O procedimento e os valores medidos estão no
[relatório da bancada](bancada-de10-lite-2026-09-18.md). O plano completo,
incluindo simulação, compilação e testes físicos, está em
[plano de testes](plano-de-testes.md).

## Bancada concluída: UART autônoma

1. Com o SOF programado, resetar com KEY0 e medir TX diretamente.
2. Colocar o jumper TX → RX e registrar LEDs/forma de onda.
3. Guardar as condições no relatório de bancada.
4. Programar os novos tops baseline e secure para iniciar a validação integrada.

O [roteiro UART](../fpga/de10_lite/uart_scope/README.md) descreve a montagem;
o [cadastro Cyclone IV](../fpga/cyclone4/README.md) lista os dados ainda necessários.

Os builds integrados da DE10-Lite foram concluídos em 18/09:

| Variante | Recursos | Fmax no pior canto | Pior setup | SOF |
| --- | --- | ---: | ---: | --- |
| Baseline | 342 LE, 215 FF, 8.192 bits, 14 pinos | 132,61 MHz | 12,459 ns | `build/de10_lite/baseline/uart_baseline.sof` |
| Secure | 6.984 LE, 2.196 FF, 8.192 bits, 14 pinos | 82,19 MHz | 7,833 ns | `build/de10_lite/secure/uart_secure.sof` |

Detalhes, hashes e todas as margens estão no [plano de testes](plano-de-testes.md).

## Entrega concluída em 18/09

`make integration`, `make baseline-fpga` e `make secure-fpga` foram executados.
Os relatórios de recursos e timing e o [plano de testes](plano-de-testes.md)
foram atualizados. A próxima etapa física é programar os tops baseline e
secure na DE10-Lite e realizar o ensaio integrado com uma fonte UART; o GPS
continua pendente.

## Marco em 19/09: contexto de experimento no PC

- `scripts/context.py` cria contextos `baseline` e `aes-128-ctr` para cada
  captura, com tamanho, contador, chave e nonce quando aplicável.
- O nonce secure é gerado aleatoriamente quando não é informado; o registro
  persistente guarda somente o fingerprint SHA-256 da chave e rejeita o mesmo
  par chave/nonce.
- Contexto, registro e lock são privados (`0600`), com atualização bloqueada e
  substituição atômica. Limites do contador e colisões foram testados.
- Os tops DE10-Lite passaram a aceitar `CONTEXT_KEY`, `CONTEXT_NONCE` e
  `CONTEXT_COUNTER` como parâmetros de elaboração; o testbench confirmou um
  contexto diferente do padrão (`0x55` recebido e `0xe2` transmitido).
- `make context` passou com sete testes; `make pc` passou com 15 testes; a
  integração baseline/secure e o wrapper parametrizado continuaram aprovados.

Essa etapa prepara os ensaios sem depender da placa. A configuração do wrapper
é estática no build: `CONTEXT_FILE` gera o pacote privado e o incorpora ao SOF.
Não há configuração em tempo de execução, GPS real nem validação física dos
tops integrados neste marco.

## Marco em 20/09: contexto privado aplicado ao Quartus

- `scripts/quartus_build.sh` passou a aceitar `CONTEXT_FILE` nos alvos baseline
  e secure, validar o modo e gerar `context_params.sv` com permissão `0600`.
- `make baseline-fpga` foi repetido com o pacote de bring-up: 0 erros, SOF e
  três cantos temporais aprovados.
- Um build secure recebeu um JSON privado temporário: o Quartus reconheceu o
  pacote, gerou o SOF e não apresentou violações temporais. O contexto foi
  removido depois do ensaio e o secure foi recompilado com o contexto público.
- A evidência detalhada está em
  [validação do build com contexto](validacao-build-contexto-2026-09-20.md).

Essa entrega encerra a implementação sem placa desta etapa. Ainda faltam
programar os tops integrados, transmitir uma sequência de teste, validar o
secure com o mesmo contexto registrado no PC e, depois, conectar o GPS real.

## Marco em 20/09: replay NMEA reproduzível sem placa

- Foi adicionado `reference/gps/neo-m8n-nmea-sample.txt` com cinco sentenças
  públicas/sintéticas do formato esperado do NEO-M8N: RMC, GGA, GSA, GSV e TXT.
- `scripts/gps_fixture.py` valida ASCII, checksum NMEA, limite de 82 caracteres
  e transforma as linhas de referência em uma transmissão CRLF de 309 bytes.
- O replay passou a ser o caso NMEA do vetor comum de integração. Baseline e
  secure processaram 9 streams/2.681 bytes no modo acelerado e 4 streams/49
  bytes em 50 MHz/9600, sem divergências.
- A suíte do PC passou com 16 testes. A evidência está em
  [validação do replay NMEA](validacao-replay-nmea-2026-09-20.md).

Esta entrega valida apenas o contrato de dados e o caminho RTL/PC. Não é
captura do GPS, não testa nível elétrico, nem altera a pendência dos ensaios
P07–P11 na bancada.

## Ensaio auxiliar — DE10-Nano

Em 18/09 foi disponibilizada uma DE10-Nano para repetir a medição da UART
isolada na FPGA Cyclone V. O alvo `fpga/de10_nano/uart_scope/` foi preparado
com o mesmo RTL, clock de 50 MHz, 9600 baud, 8N1 e estímulo `0x55` da
DE10-Lite. A compilação no dispositivo `5CSEBA6U23I7` foi concluída com
sucesso e o `.sof` foi gerado. A programação via JTAG e a medição no
osciloscópio ainda estão pendentes; portanto, este marco está **Pronto para
bancada** e não representa validação física.

O ensaio é auxiliar: serve para comparar período do bit, duração do quadro,
intervalo entre quadros e níveis/arestas observados no osciloscópio. Ele não
substitui os quatro builds do artigo nem constitui validação do GPS/AES-CTR.
Os números e o procedimento estão registrados em
[bancada da DE10-Nano](bancada-de10-nano-uart-2026-09-18.md).

## Marco antecipado em 07/09: preparação sem placa

- UART v2 revalidado, preservando suas fontes.
- FIFO de 1.024 bytes e ponte serial sem cifra implementadas; leitura síncrona,
  ocupação máxima, indicação persistente de overflow e erro de stop.
- Testes independentes de FIFO e retransmissão, inclusive 50 MHz/9600 baud.
- Projeto Quartus, pinagem do lado FPGA e restrições temporais definidos.
- `.sof` gerado; análise de setup, hold, recovery e removal nos três cantos.

Evidências em [validação da ponte](validacao-ponte-quartus-2026-09-07.md).
Isso antecipa a preparação da baseline física; não conclui sua validação de
bancada. O núcleo AES previsto para 08–11/09 foi implementado no marco seguinte.

## Marco em 08–09/09: AES isolado

1. Ordem de bytes e interface de chave/bloco documentadas em [AES](aes128.md).
2. S-box, ShiftRows, MixColumns e expansão testados separadamente.
3. Onze chaves de rodada armazenadas; preparação medida em 10 ciclos.
4. Datapath de 128 bits reutilizado, duas fases por rodada: 20 ciclos por bloco,
   intervalo mínimo de iniciação de 21 ciclos, ambos conferidos pelo testbench.
5. 866 vetores de comparação independente, incluindo 284 NIST CAVP.
6. Projeto Quartus separado para recursos e timing interno; não é o sistema GPS.

Validação final em 09/09: 18 simulações passando, lint e estrutura aprovados;
6.482 LEs, 1.813 registradores e menor Fmax interna de 77,91 MHz. Setup, hold,
recovery e removal internos positivos nos três modelos. Ver [relatório](validacao-aes-2026-09-09.md)
para as fronteiras excluídas, ferramentas e reprodução.

## Marco em 10/09: CTR e adaptador por byte

- Gerador de máscaras com nonce de 96 bits, contador de 32 bits e bloqueio
  depois do último contador permitido.
- Adaptador com duas reservas de máscara, transferência por `valid/ready` e
  descarte do contexto em cancelamento/reset.
- 36 contextos do gerador, 73 máscaras e 60 fluxos de 1 a 4.097 bytes conferidos
  com `cryptography`/OpenSSL, incluindo o exemplo oficial NIST.
- 19.009 bytes efetivamente produzidos pelo RTL recuperados no PC; zero divergências.
- 140 momentos de cancelamento/reset testados, seguidos de rearmamento.
- `make check` concluído com código 0: 20 simulações, lint de quatro tops,
  checagem estrutural e verificação independente no PC.

Evidências e comandos no [relatório CTR](validacao-ctr-2026-09-10.md);
interface documentada em [CTR](ctr.md). O teste do PC lê arquivos da simulação;
configuração e captura de portas seriais ainda serão implementadas.


## Marco em 14/09: UART de bancada e revisão

- `uart_scope`: gerador de 0x55 a cada 100 ms, RX independente, último byte nos
  LEDs e flags persistentes. Sem FIFO ou cifra no alvo de teste.
- Testbench com decodificador externo, RX independente, modelo de jumper,
  entrada desconectada, duração de cada bit, período, erro e reset.
- `make uart`, `make uart-waves` e `make uart-fpga` selecionam somente a UART.
  Corrigida a geração VCD ausente no testbench do top.
- Ponte recebe clock/baud por parâmetros de elaboração; top da DE10-Lite
  continua explicitamente em 50 MHz, 9600/8N1.
- Build/auditoria temporal selecionados por alvo. Erros atualizam o status e
  alertam sobre SOF antigo. Cyclone IV e builds ainda ausentes falham de forma
  explícita.
- Comparação ampliada para quatro configurações no mesmo repositório; docs,
  HTML de quatro telas e arquitetura ajustados nesta entrega.
- Quartus da UART: 213 LEs, 95 registradores, zero memória/PLLs, menor Fmax
  139,35 MHz; setup, hold, recovery e removal positivos nos três modelos.

Evidências consolidadas em [revisão e validação](revisao-2026-09-14.md).
Esses resultados não representam programação de placa ou captura GPS.

## Marco em 16/09: integração serial e software de captura

- `uart_ctr_bridge`: seleção baseline/secure por elaboração, leitura da FIFO
  com reserva/retenção de byte e consumo de máscara no aceite do TX.
- Framing/overflow interrompem a aquisição; abort/reset descartam dados
  pendentes. O último quadro termina antes de parar por esgotamento do contador.
- Quatro simulações integradas: nove fluxos por modo no teste acelerado e
  quatro por modo em 50 MHz/9600 com FIFO de 1.024 bytes. A execução histórica
  foi preservada; o replay atual é documentado no marco de 20/09.
- Cancelamento em 32 situações por modo acelerado, falhas e recuperação
  byte a byte com contexto novo. Baseline sem módulos AES confirmado pelo Yosys.
- Gravador binário Linux e comparador com contagens, hashes e primeira
  divergência; a execução atual também inclui o contrato do replay NMEA.
- Regressão completa: 27 simulações, sete configurações de lint, estrutura e
  conferência independente; 15 testes PC; evidências no [relatório](validacao-integracao-2026-09-16.md).
- Antes da consolidação desta etapa, `git fetch origin` foi executado e
  `origin/main` permaneceu alinhada ao histórico local; nenhum conteúdo remoto
  novo precisou ser incorporado.

O [contrato RTL](integracao-uart-ctr.md) e o [guia PC](captura-pc.md) delimitam
o que está pronto. O wrapper e o build já aceitam contexto privado estático por
`CONTEXT_FILE`; um JSON ainda não configura a FPGA em tempo de execução. O
registro persistente de nonces e o início alinhado seguem prontos para a
bancada; validação física e GPS continuam pendentes. `make check` foi repetido
em 20/09 e terminou com código 0.

## Contrato da integração e pendências de bancada

- FIFO de 1.024 bytes, resposta de leitura retida até aceite do próximo estágio.
- AES-CTR com nonce de 96 bits, contador de 32 bits e duas reservas de máscara;
  consumir máscara só no handshake. Não esperar 16 bytes de GPS para cifrar.
- Cada ensaio terá seu tamanho N definido pela captura no PC. O início e o fim
  do replay são metadados do experimento, não um bloco adicional no datapath.
- Usar nonce novo a cada captura com a mesma chave, inclusive após reset, e
  bloquear wrap. O PC manterá registro persistente; chave/nonce de simulação
  não são configuração para capturas reais.
- Framing, overflow ou reset invalidam a captura; recomeçar com novo contexto.
- Captura da referência GPS independente; PC decifra e compara cada byte,
  salva primeira divergência, contagens e hashes.

O comparador é **UART + FIFO + interfaces de fluxo** versus **o mesmo sistema + AES-CTR**
em cada FPGA. A UART para osciloscópio e a ponte atual são preparatórias.
A [arquitetura](arquitetura.md) detalha os alvos e a comparação entre clocks.

## Experimentos, escrita e dependências

Planejar três repetições do mesmo replay por configuração, preservando bytes
e intervalos. Acrescentar captura GPS contínua com duração registrada; almejar
uma hora por configuração quando a bancada permitir. Guardar configuração,
recursos pós-fit, Fmax, slacks, latência em ciclos e µs, taxa útil, erros/perdas e
ocupação da FIFO. Latência USB/SO não é latência interna da FPGA.

Introdução, trabalhos relacionados e metodologia avançam durante os ensaios.
A contribuição é a avaliação experimental reprodutível da integração.

A Cyclone IV depende da confirmação de placa/clock e de acesso ao hardware.
Se esses dados não chegarem ou uma etapa atrasar, registrar o impedimento e
revisar a execução com o orientador; não tratar um alvo genérico ou replay
sintético como bancada real. Submissão e contingência permanecem até 25/09.
