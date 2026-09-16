# Execução e submissão até 25/09 — setembro de 2026

Objetivo: adquirir GPS NEO-M8N-010 por UART e medir o custo do AES-128-CTR em
DE10-Lite/MAX 10 e Cyclone IV, com um build sem cifra e outro com cifra por
placa. **Submissão em 24/09; contingência e encerramento em 25/09.**

## Situação em 16/09/2026

UART, FIFO, AES e CTR estão integrados em um módulo comum para baseline e
secure. A saída serial foi comparada no PC, incluindo simulação em 50 MHz/9600.
O gravador/comparador binário passou em testes com porta virtual Linux.
Ainda faltam provisionamento do contexto, registro persistente de nonces,
builds completos e validação física. A UART autônoma e a ponte antigas mantêm
seus SOFs; não há registro de aquisição GPS nem dos quatro builds integrados.

A documentação anterior foi consolidada em 15/09; suas simulações e compilações
UART foram executadas na noite de 14/09, conforme o relatório de revisão.

Decisão arquitetural em 15/09: retirar o bloco de sessão do datapath. O fluxo
principal passa a ser `GPS → UART RX → FIFO → passagem direta ou AES-CTR → UART
TX → PC`; chave, nonce e tamanho da captura ficam registrados como parâmetros
do experimento no PC.

A integração prevista inicialmente para 13/09 foi validada em RTL em 16/09.
A bancada e a identificação da Cyclone IV, previstas para 15/09, não ocorreram;
a DE10-Lite ainda não está disponível. A janela foi ajustada abaixo, condicionada
ao acesso ao hardware. Software e preparação dos builds avançam sem a placa;
bancada e artigo devem seguir em paralelo, mantendo o encerramento em 25/09.

| Data | Entrega | Critério de conclusão | Situação |
| --- | --- | --- | --- |
| 07–10/09 | UART, FIFO, AES e CTR isolados | Testes e evidências dos marcos abaixo | Concluído em RTL; ponte e AES analisados no Quartus |
| 14/09 | Revisão e teste UART autônomo | Simulação, SOF e timing do alvo UART; documentação revisada | Concluído em simulação e Quartus; bancada pendente |
| 16–18/09 | UART na DE10-Lite | Captura TX no osciloscópio, 0x55/104,16 µs, RX por jumper e indicadores registrados | Pendente — Leonardo / acesso à placa; reagendado de 15/09 |
| 16–17/09 | Identificar Cyclone IV | Modelo, part number, clock, pinos e esquema confirmados | Pendente — Leonardo; reagendado de 15/09 |
| 16/09 | Integração RTL e comparador | Replay serial recuperado sem divergências nos dois modos; testes PC | Concluído em simulação/PTY; ver marco abaixo |
| 17/09 | Contexto e preparação dos builds | Provisionar chave/nonce no wrapper, registrar nonces e preservar início da captura | Pendente — frentes RTL e PC |
| 18/09 | Quatro builds | Baseline/secure em cada placa, com recursos e timing rastreáveis | Pendente — frente FPGA |
| 19–20/09 | Experimentos | Três replays por configuração e captura GPS contínua com comparação byte a byte | Pendente — bancada/verificação |
| 21–22/09 | Resultados e manuscrito | Tabelas, gráficos, discussão de latência/taxa útil e versão completa | Pendente — artigo |
| 23/09 | Revisão com orientador | Comentários incorporados e versão congelada | Pendente |
| 24/09 | Submissão principal | Envio e comprovante preservados | Pendente |
| **25/09** | **Contingência e encerramento** | **Correções de envio, eventual reenvio e confirmação final** | **Pendente** |

A chamada pública do BTSym consultada em 14/09 informa 30/09/2026 como prazo
externo. Confirmar modalidade e template no portal antes do envio. O planejamento
interno termina em 25/09 independentemente dessa folga.
[Chamada de trabalhos](https://lcv.fee.unicamp.br/virtual-btsym26-home/btsym26-call-for-paper/).

## Próxima bancada: ao receber a DE10-Lite

1. Abrir `fpga/de10_lite/uart_scope/uart_scope.qpf` ou executar `make uart-fpga`.
2. Programar o SOF da UART de bancada; resetar com KEY0; medir TX diretamente.
3. Colocar o jumper TX → RX e registrar LEDs/forma de onda.
4. Guardar SHA/SOF, captura e condições no relatório de bancada.
5. Informar o modelo e clock da Cyclone IV para elaborar seu projeto próprio.

O [roteiro UART](../fpga/de10_lite/uart_scope/README.md) descreve a montagem;
o [cadastro Cyclone IV](../fpga/cyclone4/README.md) lista os dados ainda necessários.

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
  quatro por modo em 50 MHz/9600 com FIFO de 1.024 bytes. São 4.982 bytes
  decodificados do fio TX, conferidos e recuperados no PC sem divergências.
- Cancelamento em 32 situações por modo acelerado, falhas e recuperação
  byte a byte com contexto novo. Baseline sem módulos AES confirmado pelo Yosys.
- Gravador binário Linux e comparador com contagens, hashes e primeira
  divergência; oito testes PC, incluindo porta virtual, timeout e arquivos privados.
- Regressão completa: 26 simulações, sete configurações de lint, estrutura e
  conferência independente; evidências no [relatório](validacao-integracao-2026-09-16.md).
- GitHub conferido antes do trabalho: nenhuma contribuição nova em relação
  a `bb0f15f`; não foi necessário pull. Histórico anterior preservado.

O [contrato RTL](integracao-uart-ctr.md) e o [guia PC](captura-pc.md) delimitam
o que está pronto. A interface `cfg_*` ainda precisa de um wrapper que receba
os parâmetros; um JSON no PC não configura sozinho a FPGA. Registro persistente
de nonces, início alinhado, builds completos e validação física seguem pendentes.

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
