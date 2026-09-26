# Testes físicos até 25/09 e artigo no fim de semana — setembro de 2026

Objetivo: adquirir GPS NEO-M8N-010 por UART e medir o custo do AES-128-CTR em
DE10-Lite/MAX 10 e Cyclone IV, com um build sem cifra e outro com cifra por
placa. **Freeze dos testes físicos em 25/09; redação em 26–27/09; submissão
até 30/09.**

## Situação em 22/09/2026

**Atualização de bancada em 25/09:** a DE10-Lite foi reprogramada com
`uart_scope` e o Analog Discovery 2 capturou um quadro completo `0x55`, com
aproximadamente 104 µs por bit. A referência diferencial da captura ainda
precisa ser corrigida: a tensão apareceu entre 0 e −2,77 V, portanto o nível
elétrico do TX não foi validado por esse registro. O CSV bruto, o hash, a
configuração do instrumento e a próxima verificação estão em
[bancada DE10-Lite + AD2](bancada-de10-lite-ad2-2026-09-25.md). O WaveForms
foi aberto e reconheceu o AD2; o `dwfcmd` não consegue adquirir enquanto a
interface ocupa o dispositivo. Esta repetição não encerra P03/P04 dos tops
integrados, nem os ensaios secure/GPS.

**Revisão técnica:** as duas plataformas são obrigatórias. A segunda FPGA é a
Cyclone IV E `EP4CE6E22C8N`, montada na placa ZRTECH/WXEDA V2.00. O perfil de
48 MHz, 9600/8N1 e a pinagem de bancada foram confirmados pelo JTAG, pela
programação e pelo período medido no TX. O secure otimizado agora cabe no fit e
os três projetos Cyclone IV já geram SOF; isso ainda não substitui os testes
físicos integrados.
O prazo continua concentrado na bancada até 25/09, com redação no fim de semana
e submissão/contingência até 30/09. Ver [revisão completa](revisao-completa-2026-09-20.md)
e o [roteiro específico da Cyclone IV](bancada-cyclone4-2026-09-21.md).

Antes de retomar os ensaios físicos, a instrumentação foi definida em torno de
um único adaptador USB–TTL CP2102. O novo host PC envia quatro quadros de cinco
bytes, aguarda 10 ms para detectar bytes extras e compara baseline/secure com
uma biblioteca independente. Na Cyclone IV, os quatro LEDs dos tops integrados
mostram heartbeat, atividade/configuração, overflow persistente e framing
persistente. O datapath, a pinagem e a força de saída UART não foram alterados.
Os builds baseline/secure e a regressão de integração passaram; isso prepara,
mas não conclui, o P04 físico.

Para a DE10-Lite, o roteiro P03–P06 foi fechado com pinagem JP1, ordem segura
de programação, quatro tentativas por variante, valores secure esperados e
verificação automática do relatório do CP2102. A preparação não altera o status físico:
baseline e secure integrados ainda precisam ser programados nessa placa.
O script arma a porta depois da programação e limpa as filas seriais antes do
primeiro quadro, sem consumir bytes/contexto antes da captura.
O teste em PTY de baseline/secure e o replay GPS passaram; a regressão `make check`
foi repetida com 34 testes Python. Isso valida o host, mas ainda não é evidência
física do CP2102.
Os dois SOFs foram regenerados no commit `746b085`, passaram pela auditoria de
timing nos três cantos e tiveram seus hashes registrados no plano de testes.
Em 22/09, o WaveForms 3.25.1 e o Adept Runtime 2.30.1 foram instalados no
Ubuntu amd64. O Analog Discovery 2 ainda não estava conectado, portanto a
instalação do software foi concluída, mas a enumeração e os ensaios P04/P06 com
esse instrumento continuam pendentes. O procedimento está no
[guia do AD2](analog-discovery-2-waveforms.md).

UART, FIFO, AES e CTR estão integrados em um módulo comum para baseline e
secure. A saída serial foi comparada no PC, incluindo simulação em 50 MHz/9600.
O gravador/comparador binário passou em testes com porta virtual Linux.
Em 18/09, a DE10-Lite foi identificada, o SOF `uart_scope` foi recompilado e
programado, e TX no osciloscópio e loopback TX→RX foram concluídos. Os tops
integrados `baseline` e `secure` estão separados em projetos Quartus e seus
builds foram concluídos, com recursos e timing registrados. O NEO-M8N está
disponível, mas ainda não há registro de aquisição física.

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
| 20–21/09 | Identificar Cyclone IV | Modelo da placa, clock, pinos e esquema confirmados | **Concluído inicialmente em 21/09** — placa ZRTECH/WXEDA V2.00, `EP4CE6E22C8N`, JTAG, perfil de 48 MHz e pinos de bancada registrados; revisão elétrica de borda continua no P04 |
| 20–21/09 | Revisão e adequação às duas plataformas | Secure cabe no EP4CE6; métricas, captura e regressão corrigidas | **Concluído em 21/09** — wrappers, QSF/SDC, `uart_scope`, baseline e secure compilados; `make cyclone4-metrics` aprovado |
| 16/09 | Integração RTL e comparador | Replay serial recuperado sem divergências nos dois modos; testes PC | Concluído em simulação/PTY; ver marco abaixo |
| 17–18/09 | Contexto e preparação dos builds | Wrapper carrega contexto de bring-up e projetos baseline/secure separados | Concluído para DE10-Lite — aplicação de contexto privado validada em 20/09 |
| 18–20/09 | Builds DE10-Lite | Baseline/secure com recursos e timing rastreáveis | Concluído — dois SOFs regenerados, manifests `PASS`, recursos e timing registrados |
| 19/09 | Contexto e registro no PC | Contextos privados e registro persistente de nonces testados | Concluído — `make context` e `make pc` |
| 20/09 | Replay NMEA / captura | Fixture integrado ao ensaio RTL/PC e validador de captura bruta implementado | Concluído em simulação/PC; GPS físico pendente |
| 21/09 | Preparação física das duas plataformas | Pinagem/clock/JTAG confirmados; bitstreams de bancada programáveis; UART isolada validada | **Concluído com avanço** — P01/P02 Cyclone IV, baseline programado e P03 histórico aprovado; P04 iniciado |
| 22/09 | Baseline nas duas plataformas | P03/P04 executados na DE10-Lite e Cyclone IV; bytes conhecidos, waveform, loopback e comparação no PC | **Em andamento** — P03 Cyclone IV aprovado; roteiro e verificador DE10-Lite preparados; faltam P03/P04 físicos na DE10-Lite e P04 definitivo na Cyclone IV |
| 23/09 | Secure nas duas plataformas | P05/P06 executados; ciphertext capturado, decifrado no PC e contexto/reset registrados | Pendente |
| 24/09 | GPS real e ensaio contínuo | P07–P10 executados nos quatro pares placa/configuração; três repetições e captura contínua | Pendente — depende do NEO-M8N e das interfaces seriais |
| **25/09** | **Falhas, reset e fechamento físico** | **P11, repetição de qualquer caso instável, matriz de evidências completa e freeze** | **Pendente — último dia de bancada** |
| 26–27/09 | Artigo | Tabelas, gráficos, resultados físicos, discussão, referências e versões PT/EN | Pendente — foco exclusivo na escrita |
| 28/09 | Revisão técnica | Conferência do orientador e incorporação de comentários | Pendente |
| 29–30/09 | Submissão e contingência | Template, arquivos finais, envio, comprovante e eventual correção | Pendente |

## Plano fechado de testes físicos — 21 a 25/09

O objetivo desta semana é encerrar toda a bancada na sexta-feira. Cada ensaio
deve gerar uma evidência no mesmo dia: log de programação, captura serial,
foto/arquivo da forma de onda, relatório do comparador e registro da placa,
clock, pinos, contexto e horário. Um teste só entra como concluído quando os
bytes forem comparados automaticamente; LED ou forma de onda isolada não basta.

| Dia | Manhã | Tarde | Fechamento obrigatório |
| --- | --- | --- | --- |
| **Seg 21/09** | Confirmar Cyclone IV: código EP4CE6E22C8, oscilador, pinagem, alimentação, GND e JTAG. Preparar QSF/SDC e identificar os pinos RX/TX. | Programar um bitstream mínimo/`uart_scope` em cada placa. Repetir UART autônoma e loopback na Cyclone IV; preparar o baseline para o CP2102. | P01/P02 registrados; P03 histórico do baseline aprovado; P04 iniciado, com repetição elétrica necessária. |
| **Ter 22/09** | Repetir P04 com ponta ×10 e massa curta; medir bit time e amplitudes da borda no baseline das duas plataformas. | Consolidar captura no PC, waveform e três repetições por placa; corrigir qualquer instabilidade antes do secure. | P03/P04 do baseline classificados, comparação byte a byte e waveform arquivadas. |
| **Qua 23/09** | Programar o secure nas duas placas e carregar o contexto do ensaio. Repetir os bytes conhecidos. | Executar P05/P06: capturar ciphertext no PC, decifrar com o contexto registrado e medir RX→TX no osciloscópio ou AD2 quando possível. Testar reset antes do primeiro byte e bloqueio após o primeiro byte. | Ciphertext recuperado exatamente, contexto/nonce registrados sem chave em claro, três repetições secure por placa e evidência de reset. |
| **Qui 24/09** | Validar o NEO-M8N: VCC, GND, nível elétrico, atividade TX e 9600/8N1. Capturar a referência NMEA independente. | Executar P07–P09 nos quatro casos: DE10-Lite baseline/secure e Cyclone IV baseline/secure. Fazer três repetições, validar NMEA e comparar a entrada com a saída recuperada. | GPS físico comprovado, zero divergência, framing/overflow registrados e arquivos brutos/hash preservados. Se possível, iniciar P10 contínuo. |
| **Sex 25/09** | Completar P10: captura contínua por duração registrada nos quatro casos, com perdas, primeira divergência, FIFO e erros contabilizados. | Completar P11 em cada placa/configuração; repetir qualquer ensaio instável, salvar SOFs/logs/capturas e preencher a matriz final de evidências. | **Freeze físico:** P01–P11 classificados como aprovado, reprovado ou bloqueado com causa objetiva. Nenhuma nova alteração de RTL depois deste ponto. |

### Matriz de cobertura física

- **P01–P02:** UART autônoma, níveis, temporização, TX e loopback nas duas
  plataformas.
- **P03–P04:** baseline, retransmissão de bytes conhecidos, waveform e
  comparação no PC nas duas plataformas.
- **P05–P06:** secure, ciphertext, decifragem independente, latência e reset
  do contexto nas duas plataformas.
- **P07:** alimentação, terra, nível e formato serial do GPS.
- **P08–P09:** GPS real no baseline e no secure, três repetições por plataforma.
- **P10:** estabilidade contínua e contagem de perdas/erros/overflow/FIFO.
- **P11:** reset, descarte da captura anterior e recuperação com contexto novo.

O NEO-M8N, a Cyclone IV com pinagem confirmada, o osciloscópio, USB-Blaster,
cabos/jumpers e um adaptador USB–TTL com sinais de 3,3 V precisam estar disponíveis
antes do início de 21/09. Um CP2102 é suficiente: a referência GPS é capturada
primeiro e depois reapresentada à FPGA pelo mesmo módulo. Sem GPS ou
sem a identificação elétrica da Cyclone IV, o caso correspondente deve ser
marcado como **bloqueado**, nunca como aprovado por replay RTL.

Os testes de contador esgotado, overflow forçado e falhas internas permanecem
na validação RTL; fisicamente serão verificados apenas os efeitos observáveis
de framing, reset, perda de dados e estabilidade da comunicação.

A chamada pública do BTSym consultada em 14/09 informa 30/09/2026 como prazo
externo. Confirmar modalidade e template no portal antes do envio. O planejamento
de bancada termina em 25/09; o fim de semana fica reservado para a redação e a
submissão deve ocorrer até 30/09.
[Chamada de trabalhos](https://lcv.fee.unicamp.br/virtual-btsym26-home/btsym26-call-for-paper/).

## Marco em 22/09: instrumentação preparada para P04–P06

- O host PC `scripts/serial_bench.py` foi implementado para o CP2102
  full-duplex. Cada tentativa transmite cinco bytes, espera até 1 s pela
  resposta e observa 10 ms para detectar bytes tardios ou duplicados.
- O relatório JSON registra sequência, modo, TX/RX, tamanho, timeout, extras,
  divergência e hashes. O tempo registrado é explicitamente do host, não
  latência física da FPGA; framing e overflow continuam vindo dos diagnósticos
  da placa e da instrumentação.
- O modo baseline verifica eco; o modo secure preserva o ciphertext para
  comparação independente no PC. O fluxo funciona tanto na DE10-Lite quanto na
  Cyclone IV, com o mesmo adaptador e pinagem específica de cada placa.
- Os LEDs integrados da Cyclone IV agora priorizam as flags persistentes:
  heartbeat, configuração/atividade, overflow e framing. O mapeamento é igual
  no baseline e no secure.
- `make check`, os dois builds Cyclone IV e `make cyclone4-metrics`
  passaram. Pós-fit: baseline 299 LE/189 registradores/Fmax 104,08 MHz; secure
  5.580 LE/889 registradores/Fmax 83,56 MHz; ambos operam a 48 MHz.
- O P04 continua pendente. A repetição deve usar ponta ×10, entrada de 1 MΩ,
  acoplamento DC e massa curta. Os 8 mA permanecem inalterados até existir uma
  captura correta e repetível que justifique testar 4 mA/slew lento.
- O novo [roteiro integrado da DE10-Lite](bancada-de10-lite-integrada-2026-09-22.md)
  separa P03–P06, impede confusão de cabo quando as duas FPGAs estão presentes
  e fixa quatro tentativas de `55 A5 00 FF 3C` por variante.
- O ambiente WaveForms/Adept foi instalado e verificado; a ausência do AD2 na
  porta USB foi registrada. A captura com AD2 será evidência física somente
  depois de `dwfcmd enumerate` listar o instrumento e os arquivos de captura
  serem preservados.
- Os SOFs baseline/secure foram regenerados a partir de `746b085`, com manifests
  `PASS`, timing aprovado nos três cantos e hashes conferidos. Isso ainda não
  representa programação ou funcionamento físico na DE10-Lite.
- `scripts/serial_bench.py` envia o vetor conhecido ou o replay NMEA, registra
  cada resposta e gera um relatório JSON: baseline exige eco exato; secure
  decifra todo o fluxo CTR e rejeita lacunas, corrupção ou bytes extras. Os
  testes unitários do host passaram; nenhum log físico da DE10-Lite foi
  produzido nesta preparação.

## Marco em 21/09: perfil Cyclone IV preparado para a bancada

- A placa foi identificada como **ZRTECH/WXEDA V2.00**, com FPGA
  `EP4CE6E22C8N`. A memória `W9864G6KH-6` é SDRAM externa e não participa do
  caminho UART/AES.
- O perfil validado usa clock de 48 MHz no `PIN_24`, reset ativo baixo no
  `PIN_89`, RX em J3 `PIN_103`, TX em J3 `PIN_100` e quatro LEDs nos pinos
  `PIN_1`, `PIN_2`, `PIN_3` e `PIN_144`. RX/TX foram deslocados dos pinos da
  referência pública para os pontos realmente acessíveis no J3.
- `make cyclone4-uart-fpga`, `make cyclone4-baseline-fpga` e
  `make cyclone4-secure-fpga` passaram no Quartus 25.1 e produziram os SOFs
  correspondentes. `make cyclone4-metrics` também passou.
- `j3_scope` foi programado e medido: aproximadamente `104 µs` por bit e
  `3,32 V` em nível alto. O loopback entre `PIN_100` e `PIN_103` passou.
- O baseline integrado foi programado e o P03 histórico passou pelo caminho
  externo, com retorno exato de `55 A5 00 FF 3C`. Não havia jumper local entre
  RX e TX. A repetição atual será feita pelo CP2102 full-duplex.
- A primeira observação de borda do P04 registrou overshoot/undershoot
  preliminar; ela não fecha o teste e motivou a instrumentação de 22/09.
- Evidência e sequência completa: [bancada Cyclone IV](bancada-cyclone4-2026-09-21.md).

## Marco em 20/09: endurecimento da validação e preparação da Cyclone IV

- O wrapper integrado da DE10-Lite passou a tratar o contexto provisionado como
  de uso único: KEY0 ainda pode rearmar um ensaio antes do primeiro byte, mas
  não recarrega a mesma chave/nonce depois do início da recepção. A guarda é
  reiniciada somente por novo carregamento do bitstream, e o reset de
  inicialização do FPGA ficou determinístico mesmo sem pressionar KEY0.
- A validação de métricas passou a exigir os manifests dos builds, hashes de
  fontes e artefatos, commit, dispositivo, clock, baud rate e status final.
  Falhas de fit, Fmax ausente/duplicado, slack negativo, arquivo obsoleto ou
  build incompleto agora interrompem a coleta em vez de produzir uma tabela
  parcial.
- Foi adicionado o estudo reproduzível de capacidade para o alvo
  `EP4CE6E22C8`. Ele gera projetos baseline/secure para síntese e fit, sem
  declarar pinagem, clock de bancada, SOF ou validação da placa Cyclone IV.
  A execução atual registrou 351 LE/216 registradores no baseline e
  5.626 LE/917 registradores no secure; esses números são apenas capacidade
  exploratória e serão substituídos pelos resultados da placa quando o modelo,
  pinagem e oscilador forem confirmados.
- A captura do experimento recebeu um modo pareado para armar fonte e saída
  antes do READY, reservar arquivos privados e registrar a captura uma única
  vez. O validador NMEA passou a analisar janelas brutas sem alterar os bytes,
  aceitar identificadores padrão e proprietários válidos e relatar prefixos ou
  sufixos parciais explicitamente.
- A suíte Python local passou a 31 testes aprovados. A regressão HDL, os builds
  Quartus, o replay GPS nominal e a auditoria de métricas passaram após a
  reconciliação; nada deste marco representa validação física da Cyclone IV ou
  do GPS.

## Marco em 20/09: redução de área do AES

- Removido o banco de onze chaves. O núcleo armazena a chave original e calcula
  as chaves de rodada durante cada bloco, mantendo a interface e os 20 ciclos
  de cifragem. Preparação da chave: um ciclo; intervalo mínimo entre blocos: 21.
- `make aes`: 866 vetores independentes aprovados, lint e checagem estrutural.
  `make ctr`: 60 fluxos / 19.009 bytes recuperados, incluindo stalls e resets;
  inicialização do CTR reduzida de 34 para 25 ciclos.
- Fit exploratório após essa alteração: 5.623 LE / 915 registradores no
  EP4CE6E22C8, aprovado. Evidência local:
  `build/review-2026-09-20/cyclone4-probe/output_files/resource_probe.fit.summary`.
  O ensaio manteve o wrapper de 50 MHz, sem pinagem/SDC de bancada e sem SOF;
  não fornece uma validação da placa nem do oscilador provável de 48 MHz.
- O contrato atualizado está em [AES](aes128.md) e [CTR](ctr.md).

### Ponto de retomada

As correções de wrapper, reset, métricas, captura, validação NMEA e o estudo de
capacidade da Cyclone IV foram integrados ao histórico remoto no merge
`b065ba8`. A regressão completa, os builds baseline/secure e a auditoria de
métricas foram repetidos antes de atualizar as tabelas dos manuscritos. Os
artefatos locais não substituem a confirmação de modelo, oscilador e pinagem da
Cyclone IV nem os ensaios físicos do GPS.

## Marco intermediário em 20/09: correções sem hardware (superado)

Este registro foi escrito antes da reconciliação e preserva o diagnóstico
intermediário. Os pendentes descritos abaixo foram encerrados no marco de
endurecimento da validação, acima.

- `scripts/fpga_metrics.py` passou a rejeitar slack negativo, auditoria
  incompleta, ausência de Fmax por canto e status de build não aprovado; foram
  adicionados testes negativos em `tb/test_fpga_metrics.py`.
- O validador NMEA passou a rejeitar identificador inválido, controles ASCII,
  corpo vazio e sentenças acima de 82 bytes incluindo CRLF. O replay público
  continua com 5 sentenças e 309 bytes.
- O replay de produção foi separado do estímulo com pausas artificiais; a nova
  latência foi medida em Linux no ensaio nominal.
- O wrapper DE10-Lite não rearma o mesmo contexto estático após um reset
  operacional; nova programação é necessária antes de outro ensaio. Isso é
  proteção contra reutilização acidental, não gerenciamento de chaves.
- Evidência: [validação das correções](validacao-correcoes-2026-09-20.md).
- O conjunto final passou com 31 testes Python, `py_compile`, `git diff --check`,
  regressão HDL, replay GPS, builds DE10-Lite e `make metrics`.

O próximo passo é a validação física: executar C0/P01/P02 na Cyclone IV,
começando pela programação do `uart_scope` e pela medição do bit time. Enquanto
isso não ocorrer, os SOFs e as métricas continuam sendo evidência de Quartus,
não de funcionamento elétrico da placa.

## Marco em 20/09: revisão completa e identificação do EP4CE6

- `make check` passou novamente: 27 simulações, nove configurações de lint,
  checagens estruturais e 19 testes PC. Isso não substitui bancada integrada.
- Compilação exploratória do secure para `EP4CE6E22C8`: síntese concluída;
  fit reprovado, com 6.520 funções combinacionais para 6.272 disponíveis.
  Não houve SOF, programação, pinagem real ou análise temporal válida desse alvo.
- A latência de 169.269 ciclos registrada no replay abaixo inclui pausas
  artificiais do TX. Deve ser mantida como evidência histórica desse estímulo,
  não utilizada como latência nominal no artigo antes de nova medição.
- Testes adicionais reproduziram reutilização de máscara CTR após reset,
  aceitação de slack negativo pelo extrator de métricas e falhas do validador
  NMEA. O RTL não foi modificado nesta revisão; correções continuam pendentes.
- Um CP2102 com sinais de 3,3 V foi definido como o único host serial da
  bancada. A captura direta do GPS e o replay para a FPGA continuam pendentes.
- Próximo passo sem placa: adequar a área do AES compartilhado e os testes;
  em paralelo, Leonardo confirma placa/oscilador/pinagem e prepara as interfaces.

Detalhes, fontes, evidências e prioridades na
[revisão completa](revisao-completa-2026-09-20.md). Os marcos anteriores abaixo
preservam o que foi executado; esta revisão qualifica suas limitações.

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
- A simulação dedicada processou os 309 bytes do replay em 50 MHz/9600 nos dois
  modos, com FIFO máxima de 1 byte e latência nominal de 80 ns do RX válido ao
  início do TX e 1.041.680 ns até o fim do TX; a recuperação no PC não apresentou
  divergências.
- `make metrics` consolidou recursos, Fmax e slacks dos builds baseline/secure;
  a tabela está pronta para a seção de resultados do artigo.
- Os rascunhos em inglês e português foram consolidados com os resultados
  atuais e a marcação explícita das evidências físicas ainda pendentes.
- A suíte Python passou com 31 testes. A evidência está em
  [validação do replay NMEA](validacao-replay-nmea-2026-09-20.md).

Esta entrega valida apenas o contrato de dados e o caminho RTL/PC. Não é
captura do GPS, não testa nível elétrico, nem altera a pendência dos ensaios
P07–P11 na bancada.

## Marco em 20/09: validação de captura NMEA

- `scripts/gps_capture.py` valida arquivos binários produzidos pela captura
  serial: sentença completa, ASCII, CRLF, checksum e limite de 82 caracteres.
- O relatório registra tipos de sentença, quantidade, tamanho e SHA-256, com
  permissão `0600` e sem sobrescrever um ensaio anterior.
- O replay público foi usado como teste de contrato, com 31 testes Python aprovados.
  Isso deixa o procedimento pronto para o NEO-M8N, mas ainda não comprova uma
  captura física.
- O comando de bancada será:

  ```bash
  make gps-capture-check GPS_CAPTURE=data/private/ensaio01/gps-reference.bin
  ```

  A referência só entra no experimento depois desse comando e do registro da
  montagem física.

## Marco em 20/09: consolidação dos manuscritos

- As versões em inglês e português incorporam as métricas pós-fit da DE10-Lite,
  o replay de 309 bytes, a latência RTL e as limitações atuais.
- O plano de validação física agora exige validar a referência NMEA e guardar o
  relatório/hash antes da comparação baseline/secure.
- `make manuscript-check` passou nos dois rascunhos e verifica que o replay
  sintético e a pendência da validação física continuam declarados.
- A seção de resultados físicos permanece em aberto; não foi substituída por
  simulação ou síntese.

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

A Cyclone IV já possui um perfil e SOFs preparados, mas a aprovação do alvo
depende do acesso JTAG, da confirmação dos pinos e da medição física do clock.
Se algum ponto falhar, registrar o impedimento e revisar a execução com o
orientador; não tratar um SOF compilado ou replay sintético como bancada real.
A bancada fecha em 25/09; a redação ocorre em 26–27/09 e a
submissão/contingência fica em 29–30/09.
