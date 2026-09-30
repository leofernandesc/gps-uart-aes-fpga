# GPS + UART + AES-128-CTR em FPGA

Projeto do artigo para o BTSym’26: aquisição de dados de um GPS real e avaliação
do custo de acrescentar confidencialidade em hardware à comunicação serial.

**Estado em 30/09/2026:** UART v2, ponte RX → FIFO de 1.024 bytes → TX, núcleo
AES-128 e adaptador AES-CTR por byte implementados. O AES passou pelos 866
vetores de comparação independente, incluindo 284 casos oficiais NIST;
ver [contrato do núcleo](docs/aes128.md).
A ponte já tem `.sof` para a DE10-Lite; o AES tem projeto separado de análise.
A regressão completa e o fit/timing interno do AES passaram em 09/09;
ver [resultados e limites deste marco](docs/validacao-aes-2026-09-09.md).
O CTR passou em 60 fluxos, com 19.009 bytes comparados e recuperados no PC por
biblioteca independente; ver
[validação do CTR](docs/validacao-ctr-2026-09-10.md).
O teste UART autônomo gera 0x55 a cada 100 ms para observar TX no osciloscópio,
com RX e LEDs para loopback por jumper. Seu SOF e a auditoria temporal passaram;
ver [revisão e resultados de 14/09](docs/revisao-2026-09-14.md).
Os ensaios físicos anteriores da UART e das variantes baseline/secure foram
feitos na DE10-Lite a 9600 baud. Na configuração vigente, o P01 da UART
autônoma foi repetido a 38400/8N1: o AD2 capturou e decodificou `0x55`, com
26,038 µs/bit. Uma segunda captura também decodificou `0x55`, medindo
26,0388 µs/bit. Em uma aquisição posterior, dez buffers no modo Repeated
decodificaram `0x55`; os horários indicam intervalo médio de 99,33 ms entre
quadros (93–107 ms). P01 está concluído, com ressalva sobre a seleção do
trigger no arquivo salvo. A captura P02 a 38400 decodificou `0x55` em 10/10
buffers, com bit time médio de 26,040 µs e intervalo médio de 99,56 ms entre
quadros. A captura usa apenas C1, o que basta para observar a linha comum
TX→RX unida pelo jumper. A verificação visual confirmou LEDR8 (recepção válida)
aceso e LEDR9 (erro) apagado; P02 está concluído. P03 baseline passou no
CP2102 com 20/20 bytes em quatro transações. P04 também passou: a captura AD2
decodifica os cinco bytes em RX e TX a 38400 baud, com bit time de ~26,0 µs.
P05 secure a 38400 passou: quatro transações, 20/20 bytes cifrados e recuperados
exatamente no PC. P06 também passou: o CP2102 recebeu os cinco bytes cifrados e
o AD2 decodificou simultaneamente estímulo em RX e ciphertext em TX. P07 validou
a aquisição NEO-M8N→FPGA→PC e a saída baseline com sentenças NMEA válidas. Em
P10, os replays baseline e secure da referência GPS armazenada passaram com
32.768 bytes. No baseline, a saída coincidiu byte a byte com a referência; no
secure, o ciphertext foi distinto e a decifragem independente recuperou todos
os bytes originais. O GPS ficou desconectado durante os replays: são testes de
transferência de uma captura real armazenada, não aquisição GPS ao vivo.
Os vetores independentes AES/CTR continuam válidos e foram reexecutados na
regressão. A Cyclone IV foi
retirada da matriz experimental; seus registros permanecem arquivados. Ver o
[plano de testes](docs/plano-de-testes.md).

Em 30/09, P11 confirmou bloqueio após reset de um contexto consumido e
recuperação com contexto/SOF novos. P12 e P13 validaram aquisição GPS ao vivo
nos modos baseline e secure: 8.192 bytes e 127 sentenças NMEA completas em
cada ensaio. No P13, a decifragem independente passou e LEDR6/LEDR7 ficaram
apagados. A entrada ao vivo não foi capturada em paralelo; igualdade byte a
byte foi estabelecida nos replays determinísticos, e as capturas ao vivo
curtas não representam um teste de estabilidade prolongada.

Em 29/09, o replay NMEA público de cinco sentenças (309 bytes com CRLF) passou
em simulação de produção a 50 MHz/38400 nos modos baseline e secure, sem
divergências ou overflow. O par pós-fit selecionado em 30/09 registra 331 LE/212
registradores e Fmax mínima de 117,56 MHz no baseline, contra 5.591 LE/913
registradores e 92,61 MHz no secure. Os dois atendem a 50 MHz. São resultados RTL/Quartus, não medições
físicas; veja a [validação do replay](docs/validacao-replay-nmea-2026-09-29.md)
e as [métricas FPGA](docs/metricas-fpga-2026-09-30.md).

A execução anterior de integração com 2.681 bytes por modo e os relatórios
9600-baud permanecem como histórico, não como resultados da configuração final.
O gravador binário, comparador do PC e validador de captura NMEA continuam
disponíveis para os ensaios físicos. Replays determinísticos da captura GPS
preservam uma entrada repetível, mas não substituem a aquisição direta do sensor.
O validador de captura bruta verifica CRLF, ASCII, checksum NMEA, sentenças
completas e hash; foi usado em P07 e segue disponível para novas capturas.
Os rascunhos em inglês e português possuem uma checagem das tabelas e resumos
contra uma seleção versionada de métricas, com hashes das fontes e dos
relatórios. Com builds locais, a checagem confirma também os artefatos; em um
clone sem esses arquivos, informa que verificou apenas a seleção publicada.
O gerador de contexto do PC e o registro persistente de nonces foram
implementados e testados. O wrapper aceita `CONTEXT_KEY`, `CONTEXT_NONCE` e
`CONTEXT_COUNTER` como parâmetros de elaboração, e o build DE10-Lite aceita
`CONTEXT_FILE` para gerar esse pacote privado a partir do JSON. O valor padrão
continua sendo apenas o contexto de bring-up. A aquisição GPS baseline e secure
foi validada em P07/P12/P13. O reset e a recuperação foram concluídos em P11;
os indicadores de framing/overflow permaneceram apagados em P13. A ocupação
física da FIFO não foi registrada.

A [revisão de 20/09](docs/revisao-completa-2026-09-20.md) identificou excesso
de área no secure anterior. O AES agora calcula chaves durante as rodadas,
sem armazenar onze chaves. Após a reconciliação com o remoto, a regressão,
o replay nominal, os builds DE10-Lite e a extração de métricas passaram; os resultados estão em
[validação das correções](docs/validacao-correcoes-2026-09-20.md). Após o
primeiro consumo de dados, um reset não rearma o mesmo contexto CTR: cada novo
ensaio exige contexto novo e um SOF correspondente. O bloqueio não persiste
após desligar ou reprogramar a FPGA; repetir o mesmo SOF pode reutilizar a máscara.
O sensor definido para esta etapa é o u-blox NEO-M8N, operando a 38400/8N1.
O perfil do receptor foi confirmado após ciclo de energia. Os testes físicos
P01–P06 da UART e das variantes baseline/secure passaram na DE10-Lite a
38400/8N1; P07 validou a integração física direta GPS→FPGA→PC no baseline.

Em 18/09, a DE10-Lite foi detectada pelo USB-Blaster, o projeto `uart_scope`
foi recompilado e o SOF foi programado com sucesso no `10M50DAF484C7G`. A
medição do TX no osciloscópio e o loopback TX→RX foram concluídos; os resultados
estão em [relatório da bancada](docs/bancada-de10-lite-2026-09-18.md). Os tops
integrados baseline/secure foram separados em projetos próprios. Naquele
marco, ainda aguardavam validação física, posteriormente concluída em P03–P13.

Os registros da Cyclone IV feitos em 21/09 são históricos e não pertencem mais
ao experimento ativo. Em 26/09, o diagnóstico
de P04 na DE10-Lite encontrou o pino TXD do CP2102 permanentemente alto
durante envios do PC; veja o [registro instrumental](docs/diagnostico-p04-de10-2026-09-26.md).

O host PC `scripts/serial_bench.py` envia vetores ou replays GPS, recebe a saída
e compara baseline/secure. Agora usa 38400/8N1 por padrão, permitindo também
selecionar uma taxa ao repetir ensaios antigos.

## Configuração do protótipo

| Item | Decisão |
| --- | --- |
| Placa | DE10-Lite / MAX 10, clock de 50 MHz |
| GPS | u-blox NEO-M8N; breakout alimentado a 3,3 V |
| Serial | 38400 baud, 8N1, fixo na implementação ativa |
| Criptografia | AES-128-CTR, núcleo RTL próprio e iterativo |
| Receptor | PC com decifragem por biblioteca independente |
| Avaliação | Dois builds na DE10-Lite: baseline e secure, com o mesmo RTL |
| Instrumentação física | Osciloscópio de bancada ou Analog Discovery 2; captura serial pelo CP2102 |
| Prazo | Submissão BTSym’26 até 30/09/2026 |

AES-CTR fornece **confidencialidade**, não autenticação, proteção contra
alteração/replay do tráfego ou contra falsificação do sinal GNSS. O protótipo
não deve ser apresentado como um produto de comunicação segura completo.

## Executar a validação

No Linux, a partir deste diretório:

```bash
make check
```

Executa simulações para UART a 38400 baud, FIFO, ponte, AES, CTR e integração;
o total exato é impresso pelo executor. Inclui testes históricos de compatibilidade,
bancada/FIFO/ponte, dois testbenches AES, dois de CTR e cinco da integração/wrapper.
Inclui nove configurações de lint, checagem estrutural, verificação no PC dos
bytes CTR e do TX integrado, além dos testes Python de captura, contexto,
replay, validação NMEA e consistência das métricas dos manuscritos. A execução
`make pc` de 30/09 passou nos 46 testes de software.
Falhas abortam o comando com código não zero.
Resultados locais ficam em `build/`, sem entrar no versionamento.

O executor usa ferramentas nativas se todas estiverem disponíveis; caso contrário,
usa a imagem Docker **já instalada** `isaiassh/unic-cass-tools:1.0.7`.
Não baixa dependências nem usa a rede. O container recebe as fontes somente para
leitura e pode escrever apenas no diretório de resultados e no seu `/tmp`.
É necessário ter acesso autorizado ao Docker.
Os geradores dos vetores AES/CTR também requerem Python 3 e `cryptography` no host
(já disponíveis neste ambiente). Usam uma biblioteca independente do RTL;
as referências públicas NIST estão incluídas no repositório.

```bash
HDL_RUNNER=docker make check
HDL_RUNNER=native make check
make test
make lint
make synth
make reference
make uart    # Somente UART RX/TX, top e gerador de bancada; sem AES/FIFO
make uart-waves  # Gera os VCDs da UART isolada e do teste para osciloscópio
make bridge  # Apenas os novos testes de FIFO/ponte e lint do top da placa
make aes     # Vetores independentes, componentes, núcleo, lint e estrutura AES
make ctr     # Máscaras, fluxo por byte, lint, estrutura e conferência no PC
make integration  # Caminho serial completo sem/com AES; teste em 50 MHz/38400
make integration-gps # Replay NMEA completo no timing de produção; separado por ser lento
make metrics # Extrai recursos, Fmax e slacks dos builds Quartus existentes
make metrics-snapshot METRICS_SNAPSHOT=docs/evidence/nova-selecao.json # Congela um par revisado sem sobrescrever
make pc      # Comparador, gravação binária e testes de contexto no PC
make context # Testes do gerador, registro e pacote SystemVerilog privado
make gps-replay # Valida o fixture NMEA público e sua conversão para CRLF
make gps-capture-check GPS_CAPTURE=arquivo.bin # Valida uma captura NMEA bruta
make serial-bench CP2102_PORT=/dev/ttyUSB0 CONTEXT_FILE=contexto.json RECEIVED=saida.bin REPORT=relatorio.json BAUD=38400 # vetor conhecido
make manuscript-check # Confere tabelas/resumos, fontes e hashes dos builds selecionados
make baseline-fpga  # SOF DE10-Lite sem AES, com FIFO
make secure-fpga    # SOF DE10-Lite com AES-128-CTR
# Exemplo de contexto privado aplicado ao build:
# CONTEXT_FILE=data/private/ensaio01/contexto.json make secure-fpga
```

A síntese Yosys é apenas uma verificação estrutural do RTL. **Não é fluxo ASIC**
e não substitui síntese, place-and-route e análise temporal do Quartus para a
DE10-Lite. Não usar suas células genéricas como LUTs/LEs, Fmax ou potência FPGA.

## Compilar para a DE10-Lite sem a placa

Para o teste de **UART isolada**, sem depender de GPS ou adaptador USB–UART:

```bash
make uart-fpga
```

Abrir [uart_scope.qpf](fpga/de10_lite/uart_scope/uart_scope.qpf) no Quartus.
O resultado é `build/de10_lite/uart_scope/uart_scope.sof`. O top transmite
0x55 a cada 100 ms. O [roteiro de osciloscópio e jumper](fpga/de10_lite/uart_scope/README.md)
explica a montagem, as medidas esperadas e o significado dos LEDs.

Para a ponte histórica **UART + FIFO**, que retransmite o que recebe:

```bash
make fpga
```

Usa o Quartus instalado no Linux; se necessário, definir `QUARTUS_SH` com o
caminho do executável. Faz síntese, fit, geração do `.sof` e auditoria temporal
nos três cantos do dispositivo. Não executa o Programmer. Os resultados ficam
em `build/quartus/`, incluindo `uart_bridge.sof`, relatórios e `build-status.txt`.

Na interface gráfica, abrir **File → Open Project** e selecionar
[uart_bridge.qpf](fpga/de10_lite/uart_bridge.qpf). A configuração é fixa:
MAX 10 10M50DAF484C7G, 50 MHz, 38400 baud, 8N1.

Ver [pinagem e uso da ponte](fpga/de10_lite/README.md) e
[resultados deste marco](docs/validacao-ponte-quartus-2026-09-07.md).
As métricas dessa ponte histórica incluem FIFO e LEDs de diagnóstico. O
comparativo do artigo usa os projetos integrados baseline/secure abaixo.

Para os projetos integrados usados no artigo:

```bash
make baseline-fpga
make secure-fpga
```

Os resultados ficam, respectivamente, em `build/de10_lite/baseline/` e
`build/de10_lite/secure/`. Os dois tops usam a mesma pinagem e a mesma UART;
somente a presença do AES é alterada na elaboração.

Para o AES isolado:

```bash
make aes-fpga
```

Faz síntese, fit e análise de **timing interno** usando pinos virtuais. Não gera
`.sof` nem valida os caminhos de interface com o futuro CTR/UART. Abrir
[aes128_analysis.qpf](fpga/aes_analysis/aes128_analysis.qpf) no Quartus, se desejado.
Ver [alcance das estimativas](fpga/aes_analysis/README.md).

## Organização

```text
rtl/common/reset_sync.sv     reset: asserção assíncrona, liberação sincronizada
rtl/common/sync_fifo.sv      FIFO síncrona, ocupação máxima e overflow
rtl/uart/uart_rx.sv          RX sincronizado e amostragem central por quadro
rtl/uart/uart_tx.sv          TX com duração completa de cada bit
rtl/uart/uart_top.sv         interface de bytes e configuração de produção
rtl/bridge/uart_bridge.sv    ponte sem cifra, flags persistentes de erro
rtl/bridge/uart_ctr_bridge.sv integração baseline/secure, retenção de byte e cancelamento
rtl/aes/                    AES-128 iterativo e transformações de rodada
rtl/ctr/                    gerador de máscaras e adaptador CTR por byte
fpga/de10_lite/              top da placa, projeto Quartus, QSF e SDC
fpga/de10_lite/uart_scope/   UART autônoma para osciloscópio e loopback por jumper
fpga/de10_lite/common/       wrapper comum e instrumentação dos tops integrados
fpga/de10_lite/baseline/     projeto Quartus UART + FIFO sem AES
fpga/de10_lite/secure/       projeto Quartus UART + FIFO + AES-CTR
fpga/cyclone4/              fontes preservadas como arquivo histórico; alvo retirado
fpga/aes_analysis/           análise isolada do AES, sem pinagem de bancada
tb/                         fontes seriais e verificadores independentes
scripts/                    execução reproduzível dos testes e checagens
reference/uart-v1/           cópia imutável do UART anterior e checksums
reference/aes-cavp/          vetores públicos oficiais NIST e sua procedência
reference/ctr-sp800-38a/     exemplo público AES-128-CTR do NIST
reference/gps/               replay NMEA público/sintético para simulação e verificação PC
docs/                       contratos, cronograma, evidências e checklist de bancada
build/                      saídas geradas, ignoradas pelo Git
```

O projeto original em
`/home/leofernandesc/uniccass-icdesign-tools/shared_xserver/projects/uart`
foi preservado. A referência contém apenas quatro fontes RTL, quatro testbenches
e a configuração antiga; não duplica runs ASIC, imagens ou binários.

## Documentos para continuar

- [Orientações de continuidade, cronograma e revisão de pulls](AGENTS.md)
- [Contrato e mudanças do UART](docs/uart-baseline.md)
- [Arquitetura e alvos ativos](docs/arquitetura.md)
- [UART isolada: roteiro para a bancada](fpga/de10_lite/uart_scope/README.md)
- [Revisão de código e validação em 14/09](docs/revisao-2026-09-14.md)
- [Interface, latência e limites do AES](docs/aes128.md)
- [Validação AES e recursos pós-fit](docs/validacao-aes-2026-09-09.md)
- [Interface e funcionamento do CTR](docs/ctr.md)
- [Contrato da integração UART–FIFO–CTR](docs/integracao-uart-ctr.md)
- [Captura binária e comparação no PC](docs/captura-pc.md)
- [Bancada full-duplex com um CP2102](docs/cp2102-serial-bench.md)
- [Validação do contexto e registro de nonces](docs/validacao-contexto-2026-09-19.md)
- [Validação do contexto no build Quartus](docs/validacao-build-contexto-2026-09-20.md)
- [Validação do replay NMEA a 38400](docs/validacao-replay-nmea-2026-09-29.md)
- [Replay NMEA histórico a 9600](docs/validacao-replay-nmea-2026-09-20.md)
- [Validação da captura NMEA](docs/validacao-captura-nmea-2026-09-20.md)
- [Validação das correções sem hardware](docs/validacao-correcoes-2026-09-20.md)
- [Validação dos manuscritos](docs/validacao-manuscrito-2026-09-20.md)
- [Métricas pós-fit selecionadas da DE10-Lite](docs/metricas-fpga-2026-09-30.md)
- [Métricas históricas de 29/09](docs/metricas-fpga-2026-09-29.md)
- [Métricas históricas da DE10-Lite a 9600](docs/metricas-fpga-2026-09-20.md)
- [Roteiro integrado da DE10-Lite](docs/bancada-de10-lite-integrada-2026-09-22.md)
- [Instrumentação anterior ao P04–P06](docs/validacao-instrumentacao-2026-09-22.md)
- [Instalação do WaveForms e uso do Analog Discovery 2](docs/analog-discovery-2-waveforms.md)
- [Rascunho do manuscrito BTSym](docs/manuscrito-btsym-draft.md)
- [Rascunho do manuscrito BTSym em português](docs/manuscrito-btsym-rascunho-pt.md)
- [Validação CTR e conferência no PC](docs/validacao-ctr-2026-09-10.md)
- [Resultados da primeira etapa](docs/validacao-2026-09-07.md)
- [Cronograma e critérios de conclusão](docs/cronograma.md)
- [Plano de testes e resultados](docs/plano-de-testes.md)
- [Diagnóstico físico histórico do P04](docs/diagnostico-p04-de10-2026-09-26.md)
- [Plano de execução e colaboração](docs/PLANO_DE_EXECUCAO.md)
- [Primeira bancada e materiais](docs/bancada.md)

A [apresentação para o orientador](docs/proposta_btsym_gps_fpga.html) está
versionada. A cópia local em
`/home/leofernandesc/Documents/proposta_btsym_gps_fpga.html` acompanha essa versão.

Próximo passo: fechar referências, template, figuras e PDF do artigo, usando
o par de métricas selecionado e os limites dos ensaios P01–P13. Melhorias de
análise de sincronizadores/MTBF e auditoria explícita de minimum pulse width
estão registradas no [cronograma](docs/cronograma.md) para uma próxima análise.
Procedimentos e evidências físicas estão no [plano de testes](docs/plano-de-testes.md).
Um contexto privado pode ser incorporado ao SOF com `CONTEXT_FILE`; isso é
provisionamento estático de build, não configuração em tempo de execução.
Simulação, fit e programação não substituem a medição física nem a captura GPS.
