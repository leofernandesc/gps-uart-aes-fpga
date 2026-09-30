# Plano de testes e registro de resultados

Este é o documento vivo dos ensaios do projeto. Cada teste deve ser atualizado
com a data, o commit do RTL, a configuração usada, o resultado e a evidência
correspondente. Simulação, compilação e bancada física são resultados
diferentes e não devem ser misturados.

Atualização de escopo em 29/09: receptor u-blox NEO-M8N; somente DE10-Lite/MAX
10 no experimento ativo; Cyclone IV fora do escopo. O perfil do receptor e da
UART do projeto é 38400/8N1. Os resultados anteriores a 9600
permanecem históricos. Na configuração vigente, P01 e P02 foram concluídos; o
P03 baseline passou no eco serial do CP2102: 20/20 bytes em quatro quadros. A
primeira captura AD2 era curta; a recaptura a 800 kS/s e 8.192 amostras contém
todo o burst e decodifica os cinco bytes nas linhas RX e TX. **P04 também está
concluído a 38400/8N1.** P05 secure passou com 20/20 bytes cifrados e
recuperação CTR exata. P06 também passou: 5/5 bytes cifrados foram recuperados
no PC e a captura AD2 decodifica estímulo e ciphertext nos dois canais. A captura
física do NEO-M8N foi iniciada: P07 validou a passagem das sentenças NMEA pelo
baseline; P08 concluiu três repetições de replay exato; P09 secure passou com
recuperação exata dos 4.096 bytes e ciphertext distinto da referência. Faltam
registrar os indicadores físicos, executar o replay longo secure e validar
reset. Em 29/09, o replay baseline P10 de 32.768 bytes também passou sem perdas
ou divergência; isso valida a transferência longa da captura armazenada, não
uma nova aquisição GPS ao vivo. Os
testes funcionais AES independentes do link
serial permanecem válidos. Em 29/09, `make check` passou com 37 testes Python
e oráculos AES/CTR; `make integration-gps` passou para baseline e secure em
50 MHz/38400 nos 309 bytes sintéticos. O P01 físico a 38400 foi concluído:
dez buffers AD2 decodificam `0x55` e indicam período de quadro médio de
99,33 ms (93–107 ms). Há uma ressalva de configuração do trigger registrada
abaixo. P02 foi repetido a 38400 e concluído com confirmação visual de LEDR8
aceso e LEDR9 apagado; P03/P04 baseline estão concluídos na DE10-Lite a 38400.
P05 e P06 estão concluídos. P07 validou o caminho físico GPS→FPGA→PC por NMEA;
P08 concluiu 3/3 replays exatos e P09 secure recuperou exatamente os 4.096
bytes, com ciphertext diferente da referência. No P10, os replays baseline e
secure da captura GPS de 32.768 bytes passaram sem perda ou divergência; no modo
secure, a decifragem independente recuperou a referência byte a byte. Os replays
usaram uma captura armazenada, sem GPS conectado. Permanecem pendentes o registro
dos LEDs/diagnósticos de erro e overflow e o teste físico de reset. Tempos de
host incluem PC/USB e não são latência isolada da FPGA.

## Configuração fixa

- Placa: DE10-Lite, MAX 10 `10M50DAF484C7G`.
- Clock: 50 MHz.
- Sensor: u-blox NEO-M8N; perfil UART do experimento 38400/8N1, confirmado
  após ciclo de energia.
- UART FPGA/host: 38400 baud, 8N1.
- Caminho baseline: `UART RX -> FIFO -> UART TX`.
- Caminho secure: `UART RX -> FIFO -> AES-128-CTR -> UART TX`.
- Entradas e saídas da DE10-Lite: RX em `V10` e TX em `W10`.
- Instrumentação física: osciloscópio de bancada ou Analog Discovery 2; os
  bytes são fornecidos/recebidos por um único CP2102 em nível de 3,3 V.
- Variantes FPGA: projetos Quartus separados em `fpga/de10_lite/baseline/` e
  `fpga/de10_lite/secure/`. `fpga/cyclone4/` contém somente material histórico
  e não tem builds ativos.

O contexto fixo atualmente presente no wrapper secure é apenas para bring-up:

```text
key      = 000102030405060708090a0b0c0d0e0f
nonce    = 101112131415161718191a1b
counter  = 00000001
```

Ele não representa um protocolo de provisionamento de chaves. Para os ensaios
com GPS, o contexto usado na captura deverá ser registrado separadamente no PC
e o nonce não poderá ser reutilizado com a mesma chave.

## Critério de evidência

Um teste só pode ser marcado como concluído quando houver uma evidência
reproduzível: log, vetor, relatório Quartus, captura do osciloscópio, arquivo
de bytes ou registro de programação da placa. Um resultado de simulação não
substitui um resultado físico.

## Testes de simulação e verificação RTL

| ID | Teste | Método | Critério de aprovação | Situação/evidência |
| --- | --- | --- | --- | --- |
| S01 | UART RX | `make uart` e testbench do receptor | Receber bytes válidos em 8N1, detectar stop inválido e resetar corretamente | **Concluído** — regressão UART registrada em `docs/validacao-integracao-2026-09-16.md` |
| S02 | UART TX | `make uart` e decodificador serial independente | Start, oito bits LSB-first e stop com duração correta | **Concluído** — regressão UART aprovada |
| S03 | FIFO | Testes de profundidade 2, 8 e 1024 | Ordem preservada, leitura síncrona retida, overflow sinalizado | **Concluído** — `make bridge` |
| S04 | AES-128 | Vetores AES e CAVP | Ciphertext igual ao vetor independente | **Concluído** — 866 vetores, conforme relatório de integração |
| S05 | AES-CTR | Testbench do gerador de máscaras e fluxo por byte | Máscaras, contador, pausa e exaustão corretos | **Concluído** — 60 fluxos e 19.009 bytes recuperados |
| S06 | Ponte baseline | `uart_ctr_bridge_tb` com `ENABLE_AES=0` | A saída serial é idêntica à entrada, sem módulos AES na elaboração | **Concluído** — simulação, Yosys e PC |
| S07 | Ponte secure | `uart_ctr_bridge_tb` com `ENABLE_AES=1` | PC recupera exatamente o texto de entrada após CTR | **Concluído** — simulação e comparação independente |
| S08 | Fluxos curtos e de fronteira | 1, 15, 16, 17, 70, 255 e 2.049 bytes | Não perder bytes nas fronteiras da máscara ou da FIFO | **Concluído** — integração RTL |
| S09 | Pausa e cancelamento | Pausar TX, abortar e resetar em diferentes ciclos | Nenhum byte antigo reaparece; o contexto é invalidado | **Concluído** — 32 cancelamentos por variante acelerada |
| S10 | Framing e overflow | Stop inválido e FIFO cheia | Aquisição interrompida e flag retida até abort/reset | **Concluído** — integração RTL |
| S11 | Replay NMEA sintético | Sentença NMEA incluída no vetor de integração | Bytes de uma sentença são preservados no baseline e recuperados no secure | **Concluído no núcleo** — replay de 70 bytes; wrapper físico ainda pendente |
| S12 | Wrapper baseline | Lint e síntese estrutural do top DE10-Lite | Top elabora sem AES e sem latch/problema estrutural | **Concluído em 18/09** — `make integration`; AES ausente na hierarquia baseline |
| S13 | Wrapper secure | Lint e síntese estrutural do top DE10-Lite | Top elabora com AES-CTR e sem latch/problema estrutural | **Concluído em 18/09** — `make integration` |
| S14 | Regressão final | `make check` após a mudança para 38400 | Nenhuma regressão nos módulos já aprovados | **Concluído em 29/09** — código 0; UART, FIFO, AES/CTR, wrappers, integração, estrutura e 36 testes Python |
| S15 | Contexto do ensaio | `make context` e `make pc` | Contexto privado, nonce novo e registro sem chave em claro | **Concluído em 20/09** — 7 testes de contexto; a suíte Python atual tem 36 testes |
| S16 | Contexto no wrapper | Testbench do top DE10-Lite com parâmetros substituídos | Ciphertext observado no TX corresponde ao contexto de elaboração | **Concluído em 19/09** — `make integration`, `0x55 -> 0xe2` |
| S17 | Contexto no build Quartus | `CONTEXT_FILE=... make secure-fpga` e validação do pacote gerado | O JSON é validado, o modo é conferido e o pacote privado entra no SOF | **Concluído em 20/09** — baseline/secure compilados; programação física pendente |
| S18 | Replay NMEA estruturado | `make gps-replay`, `make integration` e testes PC | Sentenças ASCII com checksum válido são convertidas para CRLF e preservadas nos modos baseline/secure | **Concluído em 20/09** — 5 sentenças, replay sintético de 309 bytes, RTL/PC; GPS físico pendente |
| S19 | Replay GPS em clock de produção | `make integration-gps` e `--verify-gps` | Os 309 bytes do replay atravessam baseline e secure em 50 MHz/38400 sem perda, overflow ou divergência | **Concluído em 29/09** — FIFO máxima 1 byte; RX válido→início TX 80 ns; RX válido→fim TX 260.480 ns; início RX→início TX 247.503 ns; físico pendente |
| S20 | Validação de captura NMEA | `scripts/gps_capture.py` e `make pc` | Captura bruta completa, ASCII, CRLF, checksum e limite NMEA aprovados antes do experimento | **Concluído em 20/09** — validação por testes automatizados; suíte Python atual com 36 testes; captura física ainda pendente |

Comandos principais:

```bash
make uart
make bridge
make aes
make ctr
make integration
make gps-capture-check GPS_CAPTURE=data/private/ensaio01/gps-reference.bin
make check
```

## Testes de compilação e métricas FPGA

| ID | Teste | Método | Dados registrados | Situação |
| --- | --- | --- | --- | --- |
| F01 | Compilação baseline | `make baseline-fpga` | Versão Quartus, SHA, SOF, warnings e status | **Concluído em 29/09 a 38400** — Quartus PASS, SOF gerado, não programado |
| F02 | Compilação secure | `make secure-fpga` | Versão Quartus, SHA, SOF, warnings e status | **Concluído em 29/09 a 38400** — Quartus PASS, SOF gerado, não programado |
| F03 | Timing baseline | Auditoria Quartus em todos os cantos | Setup, hold, recovery, removal, Fmax e caminhos não cobertos | **Concluído em 29/09** — todos os slacks positivos; setup mínimo 11,494 ns |
| F04 | Timing secure | Auditoria Quartus em todos os cantos | Setup, hold, recovery, removal, Fmax e caminhos não cobertos | **Concluído em 29/09** — todos os slacks positivos; setup mínimo 10,327 ns |
| F05 | Recursos baseline | Relatório pós-fit | Elementos lógicos, registradores, memória e pinos | **Concluído em 29/09** — 331 LE, 212 FF, 8.192 bits, 14 pinos |
| F06 | Recursos secure | Relatório pós-fit | Elementos lógicos, registradores, memória e pinos | **Concluído em 29/09** — 5.603 LE, 913 FF, 8.192 bits, 14 pinos |
| F07 | Comparação | `secure - baseline` | Custo absoluto e percentual da inclusão do AES | **Concluído em 29/09** — +5.272 LE (+1.592,75%), +701 FF (+330,66%) |
| F08 | Extração reprodutível | `make metrics` | JSON/Markdown gerados diretamente dos relatórios Quartus | **Concluído em 29/09** — Fmax 117,56/103,38 MHz; [métricas](metricas-fpga-2026-09-29.md) |
| F09 | UART autônoma Cyclone IV | Comandos Cyclone removidos dos alvos ativos | Registro de versão/placa anterior | **Fora do escopo atual** — resultado de 21/09 preservado somente no histórico |
| F10 | Baseline/secure Cyclone IV | Builds Cyclone removidos dos alvos ativos | Registro dos SOFs/relatórios anteriores | **Fora do escopo atual** — sem novos builds nem bancada |
| F11 | Métricas Cyclone IV | Métricas não pertencem à comparação do artigo | Preservar relatório antigo para auditoria | **Fora do escopo atual** — valores de 22/09 são históricos |

Os relatórios de F01–F07 devem ficar em `build/` e ser resumidos em uma tabela
do artigo. Os resultados da UART autônoma não devem ser usados como se fossem
os resultados do sistema GPS integrado.

### Resultado atual dos builds DE10-Lite — 29/09/2026, 38400 baud

| Métrica pós-fit | Baseline | Secure | Diferença secure − baseline |
| --- | ---: | ---: | ---: |
| Elementos lógicos | 331 | 5.603 | +5.272 (+1.592,75%) |
| Registradores | 212 | 913 | +701 (+330,66%) |
| Memória | 8.192 bits | 8.192 bits | 0 |
| Pinos | 14 | 14 | 0 |
| Fmax mínima | 117,56 MHz | 103,38 MHz | −14,18 MHz (−12,06%) |

Os resultados detalhados e hashes estão em
[`metricas-fpga-2026-09-29.md`](metricas-fpga-2026-09-29.md). Os SOFs foram
gerados, mas ainda não programados após a alteração de baud.

### Resultado histórico dos builds DE10-Lite — 20/09/2026, 9600 baud

Os valores abaixo pertencem ao build de 9600 baud e não devem ser usados como
métricas da configuração final. Substituir/acompanhar com o relatório novo de
50 MHz/38400 depois de concluir F01–F08.

| Métrica pós-fit | Baseline | Secure | Diferença secure − baseline |
| --- | ---: | ---: | ---: |
| Elementos lógicos | 347 | 5.622 | +5.275 (+1.520,2%) |
| Registradores | 216 | 917 | +701 (+324,5%) |
| Memória | 8.192 bits | 8.192 bits | 0 |
| Pinos | 14 | 14 | 0 |
| Fmax mínima nos três cantos | 123,00 MHz | 98,23 MHz | −24,77 MHz |

As duas variantes operam a 50 MHz com margem positiva. Piores margens
registradas:

| Análise | Baseline | Secure |
| --- | ---: | ---: |
| Setup | 11,870 ns | 9,820 ns |
| Hold | 0,102 ns | 0,101 ns |
| Recovery | 14,454 ns | 13,688 ns |
| Removal | 0,439 ns | 2,256 ns |

Os SOFs e relatórios estão em `build/de10_lite/baseline/` e
`build/de10_lite/secure/` (o diretório `build/` não é versionado):

```text
baseline uart_baseline.sof
SHA-256: f878f884b264c2f02a4d720c6ef3120f85ed88c3b52c3f87da7421c90437161c

secure uart_secure.sof
SHA-256: 320357adffc3f530f7908fd0abcc2016d41d5cd123b3aa22dc25b4af9db0a91a
```

Os hashes acima pertencem aos builds `PASS` gerados a partir do commit
`746b0852ecf3ea0f049cf3adefec470723ed810a`. O Quartus 25.1 compilou as duas
revisões sem erros. Os avisos do fit ficam
preservados nos logs; incluem o aviso de requisitos elétricos dos pinos de
3,3 V e a mensagem de licença LogicLock. Eles não produziram violação temporal.

### Resultado dos builds Cyclone IV — 22/09/2026

Perfil compilado: ZRTECH/WXEDA V2.00, `EP4CE6E22C8N`, clock de
48 MHz, 9600/8N1. Os números abaixo são pós-fit e não representam medição de
bancada.

| Métrica pós-fit | Baseline | Secure | Diferença secure − baseline |
| --- | ---: | ---: | ---: |
| Elementos lógicos | 299 | 5.580 | +5.281 (+1.766,2%) |
| Registradores | 189 | 889 | +700 (+370,4%) |
| Memória | 8.192 bits | 8.192 bits | 0 |
| Fmax mínima nos três cantos | 104,08 MHz | 83,56 MHz | −20,52 MHz |

Os três SOFs estão em `build/cyclone4/` (diretório local e ignorado pelo Git):

```text
build/cyclone4/uart_scope/uart_scope.sof
build/cyclone4/baseline/uart_baseline.sof
build/cyclone4/secure/uart_secure.sof
```

Antes de conectar GPS ou fonte serial externa, executar C0 e P01 conforme o
[roteiro da bancada Cyclone IV](bancada-cyclone4-2026-09-21.md). Com 48 MHz,
o período esperado de cada bit em 9600 baud é aproximadamente `104,17 µs`.

## Registros de bancada — DE10-Lite e Cyclone IV

O cronograma de 21–25/09 para duas plataformas foi supersedido pela decisão de
29/09: a matriz ativa é somente a DE10-Lite e o prazo vigente é 30/09. A seguir,
P01 registra primeiro a captura atual a 38400; os resultados antigos a 9600
ficam identificados separadamente como históricos.

### P01 — UART autônoma a 38400 baud — capturas de 29/09/2026

**Resultado da captura inicial:** quadro `0x55` e bit time aprovados; naquele
arquivo isolado, a cadência ainda não podia ser avaliada. O `uart_scope` na
DE10-Lite/MAX 10 (50 MHz) transmite `0x55` em 38400/8N1. A captura AD2 corrigida
mostra o sinal no CH2; a análise usou cruzamentos de 1,65 V e os centros de bit.

| Dado | Resultado |
| --- | ---: |
| Instrumento/configuração | AD2, 10 MS/s, 8.192 amostras, 0,1 µs/amostra, CH2, 1 V/div, offset 0 V, modo Average |
| Janela da aquisição | 819,1 µs; insuficiente para medir o intervalo de repetição de 100 ms |
| Cadência configurada no estímulo | 100 ms entre inícios de quadro (`PERIOD_CYCLES = CLK_FREQ / 10`), independente do baud |
| Níveis observados | −0,0787 a 3,3728 V (patamares próximos de 0 e 3,33 V) |
| Período médio de bit | 26,0381 µs, calculado a partir de 9 intervalos de borda |
| Baud inferido | 38.405 baud; erro aproximado +0,014% contra 38400 |
| Decodificação nos centros | start 0, dados LSB-first `1 0 1 0 1 0 1 0`, stop 1 = `0x55` |
| Trigger no arquivo | Channel 1, falling, 1,5 V; traço exportado no Channel 2 — alinhar fonte de trigger ao CH2 no próximo ensaio |
| Conclusão nesta captura inicial | Quadro, padrão e bit time aprovados; este arquivo isolado não mede a cadência de 100 ms |

O erro de baud é aproximado: a amostragem é de 0,1 µs e o instrumento estava
em modo Average. O pequeno mínimo negativo observado (−78,7 mV) não representa
o patamar lógico; os níveis estáveis estão claramente próximos de 0/3,3 V.
Para referência, o MAX 10 especifica, em 3,3-V LVTTL, VIL máximo de 0,8 V,
VIH mínimo de 1,7 V e faixa de entrada até 3,6 V ([datasheet Intel MAX 10](https://www.intel.com/programmable/technical-pdfs/max10-handbook.pdf)).
Como este P01 mede o TX em circuito aberto, isso contextualiza os níveis para
uma futura entrada/loopback, sem substituir a verificação elétrica sob carga.

Capturas preservadas em `docs/evidence/`:

- CSV: `de10-lite-m9-p01-2026-09-29.csv`, SHA-256
  `99faee86e72e23bc8652dcbb39aa6477e52d05f97090e9b3c18fc3e233ac4e7d`.
- Workspace WaveForms: `de10-lite-m9-p01-2026-09-29.dwf3work`, SHA-256
  `08493f88224cffa9e925ee9a8585f61e85febc0a3da22fe6423367647d8793b2`.

**Limite da captura inicial:** os 819,1 µs contêm apenas um quadro, portanto
esse arquivo não permite avaliar a repetição a cada 100 ms. A aquisição
Repeated registrada às 16:57 fechou essa lacuna; veja abaixo. A repetição P02
de TX→RX a 38400 está registrada na seção correspondente, aguardando apenas a
confirmação visual dos LEDs de recepção/erro.

#### Repetição P01 — captura AD2 às 16:39:36.927

O segundo CSV preserva metadados e amostras em volts, facilitando a análise:
CH2, 10 MS/s, 8.192 pontos, 1 V/div, offset 0 V e modo Average. Com limiar de
1,65 V e interpolação linear, foram medidos dez cruzamentos e nove intervalos
de bit; a média foi **26,03881 µs** (**38.404,21 baud**, erro aproximado
**+0,011%** contra 38400). A amostragem nos centros confirma `0x55` em 8N1.
As tensões extremas foram −0,086045 e 3,372845 V. A janela continua em 819,1 µs,
insuficiente para medir a repetição de 100 ms; portanto P01 segue aprovado para
baud e quadro, mas parcial quanto à cadência.

- CSV: `de10-lite-m9-p01-repeat-2026-09-29-1639.csv` (SHA-256
  `f19ebb8ca50fab6f051f1688020b21fb14feaa58be837641188aaa5a714639c0`).
- O CSV não registra a configuração do trigger; a captura não substitui uma
  aquisição longa destinada a medir o intervalo entre quadros.
- A aquisição repetida posterior fechou a cadência; veja a subseção seguinte.

#### Aquisição repetida P01 — workspace WaveForms às 16:57

O workspace mais recente preserva dez buffers, cada um com 8.192 amostras a
10 MS/s (819,2 µs por aquisição). No CH2, todos os dez quadros foram decodificados
como `0x55` em 8N1. A análise de 90 intervalos de borda deu período médio de
bit **26,0397 µs**, baud inferido **38.402,85** (erro **+0,0074%** ante 38400),
e extremos −0,0934 a 3,3802 V.

Os metadados temporais dos buffers correspondem a 16:57:06.244, .339, .438,
.545, .642, .737, .841, .947, 16:57:07.045 e .138. Os nove intervalos são
95, 99, 107, 97, 95, 104, 106, 98 e 93 ms; média **99,33 ms** (faixa 93–107 ms).
Assim, a captura confirma a cadência configurada de 100 ms, com resolução de
1 ms e dez quadros observados. Foi usado Run/Repeated e os dez buffers foram
guardados pelo WaveForms em ordem temporal; **Record mode não era necessário**
(ver [manual oficial do WaveForms](https://digilent.com/reference/software/waveforms/waveforms-3/reference-manual)).

O workspace indica `C1=off`, `C2=on`, mas `trigger source=Channel 1`. Isso não
impediu a análise dos quadros CH2 nem dos horários armazenados, mas é uma
inconsistência a corrigir antes do próximo ensaio: selecionar CH2 como trigger.

- Evidência: `docs/evidence/de10-lite-m9-p01-repeated-2026-09-29-1657.dwf3work`.
- SHA-256: `005c6c286f53bbb735fb466b7fba0e1a0538ba52a60a0809e093a0585b4c10ea`.
- `Documents/testerecordad2.csv` não serve para a cadência: não traz cabeçalho,
  taxa de amostragem nem timestamps e contém somente parte do quadro.

### Evidências físicas históricas — executadas a 9600 baud

Os registros P01–P06 abaixo documentam a bancada anterior e são preservados
para rastreabilidade. Eles não concluem os ensaios físicos na configuração
vigente de 38400/8N1. Para o status atual e os critérios de repetição, use a
matriz no início deste documento e o [cronograma](cronograma.md).

### P01 — UART autônoma (histórico)

Este foi o primeiro ensaio físico, feito com `uart_scope`.

| Medida | Esperado | Resultado |
| --- | ---: | --- |
| Período do bit | aproximadamente `104,16 µs` | **`104,22 µs`** |
| Quadro 8N1 | aproximadamente `1,0416 ms` | **aproximadamente `1,042 ms`** |
| Intervalo entre quadros | aproximadamente `100 ms` | **`0,1 s`** |
| Nível elétrico | I/O de 3,3 V | **`ΔY = 3,58 V`**, canal em alta impedância |
| Dados | `0x55` | **Decodificação correta** |

Configuração: ponta ×10, canal em alta impedância, `200 µs/div`. Evidência
completa em [`bancada-de10-lite-2026-09-18.md`](bancada-de10-lite-2026-09-18.md).

### P02 — Loopback da UART autônoma

Na variante Cyclone IV `j3_scope`, TX foi ligado ao RX por jumper entre
`PIN_100` e `PIN_103`. O heartbeat, o início de TX, a recepção de `0x55` e a
ausência de erro foram confirmados pelos LEDs.

Na DE10-Lite, o `uart_scope` foi repetido com jumper de `JP1` pino 2/W10 (TX)
para pino 1/V10 (RX). O AD2 registrou dez quadros `0x55` em 8N1, com período
médio de bit de `104,153 µs` e níveis medianos de `3,325 V`/`−0,026 V`. Os
indicadores mostraram recepção válida (LED8 aceso) e nenhum erro (LED9 apagado);
os LEDs 2, 4 e 6 corresponderam aos bits de `0x55`. Os arquivos brutos e hashes
estão no [registro da bancada DE10-Lite + AD2](bancada-de10-lite-ad2-2026-09-25.md).

**Resultado: concluído nas duas plataformas** — Cyclone IV em 21/09/2026 e
DE10-Lite em 26/09/2026 (capturas de 25/09). Este ensaio valida as UARTs
autônomas e o loopback físico; não valida ainda FIFO, AES ou GPS.

#### Repetição P02 — DE10-Lite, UART 38400 baud (29/09/2026)

O workspace atual do AD2 contém dez buffers de 8.192 amostras a 11,11111 MS/s
(janela de 737,28 µs por buffer). Cada buffer foi decodificado como um quadro
8N1 válido `0x55`, incluindo start e stop bits. O período médio medido a partir
das transições é **26,0400 µs/bit** (mediana 26,0383 µs; faixa 26,0338–26,0444
µs), consistente com a configuração de 38400 baud. As medianas dos patamares
ficaram entre 3,318–3,322 V no alto e −0,062–−0,059 V no baixo; o CSV teve
extremos de −0,092 a 3,362 V. A pequena excursão abaixo de zero é medida do
instrumento, não uma tensão negativa produzida pela FPGA.

Os timestamps dos dez buffers foram ordenados cronologicamente (o arquivo
armazena o buffer mais antigo como índice 9). Os nove intervalos entre quadros
foram **98, 97, 97, 107, 96, 107, 94, 96 e 104 ms**, média **99,56 ms** e faixa
94–107 ms, coerentes com a cadência de 100 ms do estímulo.

Evidências brutas preservadas: [workspace AD2](evidence/de10-lite-m9-p02-ad2-repeated-2026-09-29-1726.dwf3work)
(SHA-256 `c2f66afdbe48064b716545259404cf98bfe7cb824d1ae9ea8129aad8c8ae531d`)
e [CSV exportado](evidence/de10-lite-m9-p02-ad2-repeated-2026-09-29-1726.csv)
(SHA-256 `bcfb47c9a296af9665daffb5c9380293549f438fa587502ec7e1050198d0cd79`).
O CSV foi capturado às 17:26:12, a 11,11111 MS/s, com 8.192 pontos; o
workspace registra dez aquisições no modo Repeated.

**Interpretação:** o workspace usa C1 e deixa C2 desligado, mas isso não é uma
limitação para o loopback: com TX e RX unidos pelo jumper, ambos compartilham
o mesmo nó elétrico e um canal basta para observar a forma de onda. A captura
confirma o sinal nessa linha; por si só, não comprova que o receptor UART
interno reconheceu o quadro. Na verificação visual durante a execução, LEDR8
(recepção válida) acendeu e LEDR9 (erro) permaneceu apagado. Com a decodificação
AD2 de 10/10 quadros e os indicadores confirmados, **P02 está concluído**. A
observação dos LEDs foi visual; não há fotografia anexada.

### P03 — Baseline na placa

1. Compilar e programar `uart_baseline.sof`.
2. Manter a fonte UART inativa até a configuração estar concluída.
3. Confirmar LED de configuração/atividade.
4. Apresentar bytes por uma fonte UART independente no RX da plataforma.
5. Observar a retransmissão no TX com o host PC e o CP2102.
6. Registrar erros, eventos, ocupação e comportamento após reset.

O registro anterior por microcontrolador é histórico. A execução operacional
será feita com o CP2102: TXD→RX da placa, RXD←TX da placa e GND comum, sem
jumper entre os sinais.

**Tentativa de programação em 29/09/2026:** o SOF baseline existente
(`build/de10_lite/baseline/uart_baseline.sof`, SHA-256
`3132e0097eccd4194bf54f5041c992eff1fed41c0efde03e9b60902f1e5caaf7`) foi
enviado ao Quartus Programmer pelo agente, mas o comando retornou
`Error (213013): Programming hardware cable not detected`. `jtagconfig` e
`quartus_pgm -l` ficaram presos em `Connecting to server(s)` até o timeout, e
`lsusb` não conseguiu inicializar libusb (`-99`) neste ambiente. Portanto, a
conexão física do JTAG foi confirmada como normal, mas o processo do agente não
tem `/dev/bus/usb` disponível; isso não diagnostica defeito na placa nem no
cabo. Após desconectar e reconectar a FPGA e o AD2, a nova tentativa de
programação — repetida também com o caminho absoluto do `.sof` — retornou o
mesmo erro 213013.

**Programação confirmada em 29/09/2026 às 17:44:** executada no terminal do
host com o Quartus Programmer 25.1, cabo `USB-Blaster [1-3]`, arquivo
`uart_baseline.sof`, checksum Quartus `0x0029C5BB`, dispositivo
`10M50DAF484@1` (JTAG ID `0x031050DD`). Resultado: `Configuration succeeded`,
0 erros e 0 avisos. A placa está programada para o baseline a 38400/8N1; o
ensaio P03 de eco com o CP2102 ainda está pendente.

**Resultado DE10-Lite em 26/09/2026: P03 aprovado** — o CP2102 em
`/dev/ttyUSB0` enviou quatro quadros `55 A5 00 FF 3C`; a FPGA devolveu os 20
bytes exatamente, sem timeout, perda ou extras. O tempo do host não é latência
isolada da FPGA. A confirmação visual mostrou LEDR0 piscando, LEDR1/LEDR5
acesos e LEDR6/LEDR7 apagados; a FIFO estava vazia ao final. P04 (forma de
onda/bit time) e P05–P06 (secure) seguem pendentes. Detalhes, hashes e
artefatos locais estão no
[roteiro integrado da DE10-Lite](bancada-de10-lite-integrada-2026-09-22.md).

**Repetição física em 29/09/2026, 12:51:** `serial_bench.py` registrou
`PASS`, com o vetor `55 A5 00 FF 3C` retornado integralmente (5/5, sem timeout
ou extras). Relatório `data/private/de10-2026-09-29/p04-baseline-5b-report-05.json`,
SHA-256 `69fd7e010c715bed17e0cfaaca552cc4e443f292641b6d42d3b6843e58317e25`;
contexto `1eb6f17d795349c18d0910e9b03b6738`. O tempo de 16,753 ms é medido pelo
host, não é latência da FPGA. A interpretação como eco da placa pressupõe que o
jumper local TXD↔RXD do CP2102 foi removido durante a execução; o relatório
serial não identifica o caminho elétrico.

**P03 baseline — repetição serial e captura AD2 em 29/09/2026, 17:47 (Manaus):**
o relatório do CP2102 registrou quatro transações de cinco bytes; todas
retornaram exatamente `55 A5 00 FF 3C`, totalizando **20/20 bytes** e status
`PASS`, sem timeout, perda ou extras. O tempo total observado pelo host foi
259,046 ms e inclui driver/USB; não é latência isolada da FPGA. Relatório
privado `data/private/de10-2026-09-29/p03-baseline-20b-report-01.json`
(SHA-256 `e90e47e439c4eb87c3dfa56166fff061842e791e53aa5880e60baeb2e21c24d9`);
arquivo recebido (20 bytes, SHA-256
`1ec8f144575a9c265334dfa2c385532741170ab730f39f5e38a9fae7f8517e5d`).

O CSV do AD2 foi capturado às 17:47:48.755, a 11,11111 MS/s, com 8.192
amostras por canal e modo Average. A janela vai de −0,310382 a +0,426808 ms em
relação ao trigger (**0,737190 ms** no total); trigger: CH1, borda de descida,
1,65 V. CH1 variou de −0,0956 a 3,4254 V e CH2 de −0,0529 a 3,3728 V,
compatíveis com atividade entre níveis próximos de 0 e 3,3 V. Há cruzamentos de
1,65 V nos dois canais, mas o recorte não contém os quatro quadros completos.
Um quadro de cinco bytes em 38400/8N1 requer aproximadamente **1,302 ms** de
tempo serial, antes de considerar a margem de captura. Portanto, o ensaio
byte-a-byte P03 está aprovado; a aquisição não serve como evidência de forma de
onda integral e P04 permanece pendente.

Para repetir a forma de onda de **um** burst: Single, 1 MS/s, 8.192 amostras
(8,192 ms), trigger CH1 na descida em 1,65 V, com CH1 em CP2102 TXD/V10 e CH2 em
W10/CP2102 RXD. Isso dá cerca de 26 amostras por bit. Armar a captura antes de
iniciar o envio. Para guardar as quatro transações, espaçadas em 50 ms, usar
Record; o relatório indica cerca de 259 ms para o ensaio todo, então a gravação
deve cobrir pelo menos 300 ms.

Capturas arquivadas: [CSV AD2](evidence/de10-lite-m9-p03-baseline-ad2-2026-09-29-1747.csv)
(SHA-256 `2ba21d94c607a4915fe3b60f5903da6f4434b8b4366255854f188ec5fa3bf574`)
e [workspace WaveForms](evidence/de10-lite-m9-p03-baseline-ad2-2026-09-29-1747.dwf3work)
(SHA-256 `727b5e6a76773d578f6bc15a074dd6ca39ae20130c008b1d9c41e7526a9849e9`).

**Recaptura P03/P04 — AD2 e CP2102 em 29/09/2026, 18:00 (Manaus):** um novo
contexto baseline de cinco bytes foi usado para enviar uma transação. O CP2102
recebeu `55 A5 00 FF 3C` sem divergências (5/5, `PASS`); relatório privado
`data/private/de10-2026-09-29/p03-baseline-5b-report-02.json` (SHA-256
`3eb1644bbdf055ac7580be2fdcdafb2ee59eb793703e9fb6571534421e02b16f`). O host
registrou 70,237 ms na execução completa, incluindo software/USB; isso não é
latência isolada da FPGA.

O CSV AD2 tem 8.192 amostras a 800 kS/s, amostragem de 1,25 µs e janela de
10,23875 ms (−4,98637 a +5,25238 ms em relação ao trigger). O trigger é CH1,
borda de descida em 1,65 V. Nos dois canais foram decodificados, em 38400/8N1,
os cinco bytes `55 A5 00 FF 3C`, com start, oito bits e stop válidos. O período
estimado pelas transições foi aproximadamente **26,00 µs/bit no CH1** e
**26,03 µs/bit no CH2**, compatível com o nominal de 26,04 µs; os quadros têm
cerca de 260 µs por byte. O início de TX no CH2 ocorreu aproximadamente
**247,5 µs** após o início de RX no CH1. Esse é o atraso físico entre inícios
dos quadros e inclui a recepção UART, não a latência interna isolada do AES.

CH1 variou de −0,0919 a 3,4403 V e CH2 de −0,0455 a 3,3876 V; os níveis ficam
próximos de 0/3,3 V, com pequenas excursões medidas pelo AD2. Assim, P03 está
aprovado na comparação de bytes e P04 está aprovado na captura de quadro/bit
time em ambos os sentidos, para a DE10-Lite e a configuração atual. Isso não
substitui os testes secure nem a captura do NEO-M8N real.

Capturas preservadas: [CSV AD2](evidence/de10-lite-m9-p03-baseline-ad2-2026-09-29-1800.csv)
(SHA-256 `6327bbff8d6feda1c301eaa672d60932cced5e95d69d66173c7d99e7361fb637`)
e [workspace WaveForms](evidence/de10-lite-m9-p03-baseline-ad2-2026-09-29-1800.dwf3work)
(SHA-256 `2652c30c0d41fb2abc2a1391288c4d507ffd5c92558209a1eec5b896046492e2`).

Para as próximas repetições, `scripts/serial_bench.py` envia quatro quadros de
cinco bytes, observa uma guarda de 10 ms para bytes extras e produz um relatório
JSON com tamanho, igualdade, timeout, extras e hashes. O tempo do host não será
usado como latência da FPGA. A porta é armada depois da programação e suas filas
são limpas antes do primeiro quadro.

Nos tops integrados da Cyclone IV, os LEDs ativos em zero são: `LED[0]`
heartbeat, `LED[1]` configuração/atividade, `LED[2]` overflow persistente e
`LED[3]` framing persistente. Essa associação é idêntica no baseline e no
secure.

### P04 — Baseline no osciloscópio/AD2 a 38400/8N1

Medir simultaneamente a entrada `V10` da DE10-Lite (CH1: CP2102 TXD) e a saída
`W10` (CH2: CP2102 RXD), com GND comum. Critérios: repouso alto; start, oito
bits e stop válidos; aproximadamente `26,04 µs` por bit, `260,4 µs` por byte e
`1,302 ms` para cinco bytes; quadros consecutivos sem truncamento; registrar a
diferença entre os inícios de RX e TX.

**Situação: concluído na DE10-Lite em 29/09/2026.** A recaptura P03/P04 das
18:00, descrita acima, decodifica `55 A5 00 FF 3C` nos dois canais e mede
aproximadamente `26,00–26,03 µs` por bit. O início do primeiro quadro TX ficou
~`247,5 µs` após o início do quadro RX. A janela de 10,239 ms cobre o burst com
margem. Os níveis medidos são compatíveis com lógica de 3,3 V. P04 está
aprovado para baseline na DE10-Lite; a Cyclone IV está fora do escopo atual.

Os registros de bancada anteriores a 38400 baud, inclusive as tentativas de
12:05–13:21, são históricos da configuração anterior (9600 baud) e não alteram
o resultado vigente acima.

No osciloscópio de bancada, usar ponta ×10, entrada de 1 MΩ, acoplamento DC,
massa curta ou mola de terra e, se disponível, limite de banda de 20 MHz. No
AD2, usar entradas diferenciais com o terminal negativo no GND, faixa compatível
com 0–3,3 V e salvar o CSV bruto junto da imagem da captura.
A força de saída permanece em 8 mA durante essa repetição. Somente
se duas capturas corretas ainda mostrarem excursões fora de `−0,3 V` a `3,6 V`
será criada uma variante experimental com 4 mA e slew rate lento; essa variante
deverá ser aplicada de forma idêntica ao baseline e ao secure antes de qualquer
comparação.

**Captura passiva em 29/09/2026, 11:51 (Manaus):** o CP2102 estava conectado,
mas não transmitiu bytes durante a aquisição. O arquivo
`~/CapturasWaveForms/TesteP04semocp2102.csv` contém 8.192 amostras/canal a
662.252 amostras/s, por 12,368 ms. O canal 1 variou de 3,2903 a 3,2978 V e o
canal 2 de 3,3234 a 3,3325 V; nenhum teve amostras abaixo de 1,5 V ou transições
no limiar de 1,65 V. Isso é compatível com as duas linhas UART em repouso alto
(~3,3 V) quando não há tráfego. O CSV não codifica a ligação física das pontas;
se CH1 estava em RX/V10 e CH2 em TX/W10, ambos os sinais ficaram inativos, como
esperado. O workspace correspondente é
`~/CapturasWaveForms/TesteP04semocp2102.dwf3work`. Os hashes estão no
[cronograma](cronograma.md#situação-em-29-09-2026). Esta captura confirma apenas
o nível de repouso e não mede start/data/stop bits, bit time ou eco; P04 segue
pendente até repetir a aquisição enquanto o CP2102 envia o vetor de teste.

**Ensaio ativo do baseline em 29/09/2026, 12:05 (Manaus):**
`serial_bench.py` abriu `/dev/ttyUSB0` e escreveu `55 A5 00 FF 3C` em
9600/8N1. O host recebeu 0/5 bytes em 1,0004 s (timeout, sem extras); o arquivo
`data/private/de10-2026-09-29/p04-baseline-5b-received.bin` tem zero bytes.
Relatório: `data/private/de10-2026-09-29/p04-baseline-5b-report.json`
(SHA-256 `43383bac09d3b1c3a812cff80882969a5b510357cd815e046af46a1323deabd7`),
contexto `context_id=1b2f05f338ef4758a8180201a9a219cb`. O envio ao driver serial
foi registrado, mas sem captura do AD2 não é possível confirmar que o TXD do
CP2102 alternou nem que o quadro chegou a V10. Consultar LEDs e waveform antes
de repetir; a causa não está isolada e P04 permanece pendente.

**Segunda tentativa/captura em 29/09/2026, 12:14 (Manaus):** novo envio de
`55 A5 00 FF 3C`, com retorno 0/5 em 1,001 s e sem extras. O CSV salvo do AD2,
porém, indica aquisição às 12:14:56.532, aproximadamente 29,8 s após o fim da
transação (12:14:26.723). Assim, os 8.192 pontos a 543.478 amostras/s — CH1
3,2883–3,2961 V e CH2 3,3220–3,3310 V, sem cruzamentos de 1,65 V — são apenas
uma captura posterior em repouso, não uma observação simultânea do envio. O
trigger também estava em subida a 0 V; para a próxima captura usar Single
armado antes do comando, trigger de descida em ~1,65 V e janela de 15–20 ms.
Os arquivos atuais são `~/CapturasWaveForms/TesteP04semocp2102.csv` e
`TesteP04semocp2102.dwf3work`; seus hashes estão no [cronograma](cronograma.md#situação-em-29-09-2026).
P04 permanece pendente.

Uma terceira tentativa às 12:20 de 29/09 também retornou 0/5 após 1,0005 s
(`data/private/de10-2026-09-29/p04-baseline-5b-report-03.json`), sem CSV novo
do envio. O Single não apresentou traço; verificar primeiro trigger e ligação
de CH1 antes de inferir ausência de sinal em V10.

Na quarta tentativa, às 12:26, o relatório
`data/private/de10-2026-09-29/p04-baseline-5b-report-04.json` registrou 0/5
com timeout de 1,0012 s. O CSV do AD2 tem timestamp 12:26:26.517, cerca de
4 s depois do relatório, e mostra apenas repouso alto (CH1 3,2876–3,2958 V;
CH2 3,3220–3,3307 V). O trigger salvo continuou em subida a 0 V. Portanto,
P04 segue sem captura simultânea. O teste diagnóstico seguinte é o loopback
TXD↔RXD do CP2102 fora da FPGA; P07 pode avançar independentemente, enquanto
P05/P06 aguardam um baseline físico reproduzível.

### Loopback local do CP2102 — 29/09/2026, 12:35–12:42

A primeira tentativa, às 12:35, retornou 0/5; o estado da ligação TXD↔RXD não
foi confirmado. A execução `-02`, às 12:41, também retornou 0/5, mas o usuário
esclareceu que rodou sem conectar TXD a RXD. Ela está registrada como inválida,
fora dos resultados do teste (relatório SHA-256
`a236f9c2dfe5459071eea30d76c84d5a2b5fc2ca1386cd79fc97ed1e5d7e2467`).

Na execução válida `-03`, com a FPGA desconectada e TXD jumpeado diretamente a
RXD no CP2102, `/dev/ttyUSB0` retornou exatamente os cinco bytes
`55 A5 00 FF 3C`: **PASS, 5/5**, sem timeout ou extras. A transação durou
15,853 ms conforme o relógio do host; esse número inclui a USB/driver e não é
latência da FPGA. Relatório:
`data/private/de10-2026-09-29/cp2102-self-loop-03-report.json` (SHA-256
`c947472d4428bd1e04357472bfd9c8bb80c3d16bd589b727d165933de28282b2`). O arquivo
recebido tem SHA-256 `086a1a8a2575a3f80eb8a942552cfaf94825e511f1ec0df2448b4bfc97b68b01`,
igual ao vetor de referência. Isso confirma o caminho serial do host, TXD e RXD
no loopback local; não valida a ligação com a FPGA.

**Próximo passo P04:** retirar o jumper local TXD↔RXD e ligar CP2102 TXD→V10
(UART RX da DE10-Lite), W10→CP2102 RXD (UART TX) e GND comum. Não conectar VCC
do adaptador à placa. Programar `build/de10_lite/baseline/uart_baseline.sof` e
repetir o vetor conhecido com captura simultânea de V10 e W10 no AD2. P05/P06
seguem aguardando P04 integrado reproduzível.

**Captura `TesteP04` em 29/09/2026, 12:51:** o CSV informa aquisição às
12:51:42.844, cerca de 7,96 s após o relatório de eco. Foram salvas 8.192
amostras a 2,85714 MHz (2,867 ms). CH1 variou de 3,3796 a 3,3934 V e CH2 de
3,3203 a 3,3304 V; nenhum canal cruzou 1,65 V ou apresentou transições. O
trigger ficou em borda de subida a 0 V, que não captura o start bit UART (borda
de descida). Arquivos: `~/CapturasWaveForms/TesteP04.csv` e
`TesteP04.dwf3work`; hashes CSV `8d0eebb2762b6603a747938713e8aa503aef8a377efff4353794e313bd26f64b`,
workspace `c2332475dd3f36a2048328feee68c0175e6c714f887a297891b03c2ecf495566`.
Se CH1 estava em V10 e CH2 em W10, a aquisição mostra apenas repouso alto.
Portanto, o relatório serial contém um retorno 5/5, mas a captura não confirma
os quadros nem o bit time. Repetir com trigger de descida em ~1,5 V e Single
armado antes de executar `serial_bench.py`; usar janela de pelo menos 15 ms.

**Captura `TesteP04` com trigger corrigido, 29/09/2026, 13:02:** o relatório
`data/private/de10-2026-09-29/p04-baseline-5b-report-06.json` passou 5/5, sem
timeout ou extras (SHA-256 `661d187ed18313d3e2f0cceabce755855733492277c4dd359e2e93a909180b14`;
contexto `bde161ccb4be4d36af5db7220436b0e8`). O CSV tem horário 13:02:52.586,
64 ms antes do término do relatório, 8.192 amostras a 2,85714 MHz e janela de
2,867 ms. O trigger foi corrigido para descida a 1,5 V e agora há transições
reais: tomando CH1=V10 e CH2=W10, CH1 tem período médio de transição de
104,075 µs (14 intervalos), CH2 104,212 µs (4 intervalos). A primeira descida
em W10 ocorre cerca de 0,989 ms após a primeira descida em V10, compatível com
um byte recebido e retransmitido. A captura, porém, contém só o primeiro trecho
do vetor e parte do primeiro byte de retorno, não os cinco quadros completos.

Níveis medidos: CH1 −0,064 a 3,418 V; CH2 1,149 a 3,545 V. O nível baixo de CH2
está elevado para a UART e precisa de verificação: confirmar CH2− no GND comum,
escala/configuração DC correta e, principalmente, que o jumper local TXD↔RXD do
CP2102 foi removido antes da ligação à FPGA. Se esse jumper ficou instalado, ele
pode unir a saída TXD do CP2102 à saída W10 e causar contenção. Não repetir até
confirmar a ligação e a referência. CSV `~/CapturasWaveForms/TesteP04.csv`
(SHA-256 `fe1f7283737d40a35ae3fa203223428d64b017dc3a5a602f2c9a54aef369a736`);
workspace `.dwf3work` (SHA-256
`72a4fa18b4fac058f33b448e4552d047954510225709f5d853fe86aa314316cf`). P04 tem
bit time preliminar, mas falta captura completa e validação dos níveis.

Tentativa de 26/09 às 01:18: o host enviou o primeiro burst pelo CP2102, mas
recebeu zero bytes em 1 s e abortou os três bursts restantes. Nenhuma captura
do AD2 foi salva; a causa ainda está em diagnóstico, então isto não é resultado
de forma de onda nem altera o P03 aprovado. Relatório: `data/private/de10-2026-09-26/p04-baseline-report.json`;
P04 continua pendente.

Após a tentativa, LEDR9 ficou aceso com LEDR0 piscando e LEDR2/3/6/7 apagados.
LEDR9 também sinaliza contexto bloqueado; essa foi apenas uma hipótese. O
baseline foi reprogramado via JTAG às 01:28, com sucesso (checksum
`0x002A0029`). Depois da gravação, foram relatados LEDR1/LEDR5 acesos e LEDR0
piscando. Nenhum byte foi reenviado; armar o AD2 antes de retomar P04.

### Retentativa P04 após armar o AD2 — 26/09/2026, 01:35

A primeira chamada com `--trials 1` foi barrada antes de acessar `/dev/ttyUSB0`
porque o contexto existente indicava 20 bytes e o payload solicitado tinha 5;
nenhum dado foi transmitido. Após criar um contexto baseline de 5 bytes,
executou-se um único burst `55 A5 00 FF 3C`: o CP2102 recebeu a mesma sequência,
5/5 bytes, sem timeout ou extras. O tempo de 16,929 ms é medido no host e não
representa latência isolada da FPGA. Relatório:
`data/private/de10-2026-09-26/p04-baseline-single-report.json`.
O retorno 5/5 ocorreu uma vez; salvar/analisar o traço do AD2 ainda é necessário
para concluir a medição de bit time, níveis e RX→TX.
O usuário relatou que nenhum traço apareceu no WaveForms; não há CSV/workspace
P04. A transferência 5/5 não será tratada como medição do osciloscópio.

### Segunda retentativa P04 — 26/09/2026, 01:53

Foi enviado novamente um burst `55 A5 00 FF 3C`; o host transmitiu 5 bytes e
recebeu 0 em 1,002 s (timeout, sem extras). Relatório:
`data/private/de10-2026-09-26/p04-baseline-retry2-report.json`.
Resposta intermitente ainda sem causa determinada. Conferir LEDR1/2/3/5/6/7/9
e confirmar se KEY0/reset foi acionado antes de programar ou retransmitir.
O usuário relatou somente LEDR9 aceso; o baseline foi reprogramado às 01:58
via JTAG, com sucesso (checksum `0x002A0029`), e confirmou depois que os LEDs
de atividade/configuração voltaram a acender. O estado de LEDR9 não foi
confirmado antes da tentativa repetida descrita abaixo.

Por solicitação do usuário, iniciou-se um ensaio com dez bursts a cada 250 ms.
O script enviou apenas o primeiro e abortou após timeout de 1,001 s sem retorno
(0/5 bytes recebidos); logo, não houve transmissão repetida. Relatório:
`data/private/de10-2026-09-26/p04-baseline-repeat10-report.json`. Aguardar o
estado atual dos LEDs e confirmar se KEY0 foi pressionado após a regravação.

### Estímulo repetitivo para inspeção do AD2 — 26/09/2026, 02:18

Com os canais aparentando constantes, o CP2102 enviou 200 bursts de
`55 A5 00 FF 3C` em 10,103 s, 9600/8N1, com pausa de 50 ms. A recepção não foi
avaliada e o buffer foi descartado ao final; é somente estímulo para captura,
não evidência de retorno ou validação elétrica. Aguardar confirmação visual e
salvar CSV/workspace para concluir P04.

Um segundo envio visual ocorreu por volta de 02:30: novamente 200 bursts
(1.000 bytes) do padrão, durante 10,100 s, com 50 ms entre bursts. O eco não
foi lido/avaliado; ainda não há confirmação do traço ou CSV do AD2.

### Verificação explícita de eco — 26/09/2026, 02:32

O baseline foi reprogramado via JTAG antes de enviar uma única transação, para
começar em estado conhecido após os estímulos anteriores. A guarda do wrapper
impede rearmar via KEY0 depois do primeiro byte recebido; a ponte não se
desativa automaticamente ao fim de cada burst. Programação bem-sucedida no
`10M50DAF484@1`, checksum `0x002A0029`. O CP2102 enviou `55 A5 00 FF 3C` em
9600/8N1, mas recebeu **0/5 bytes** em 1,501 s (timeout; nenhum byte extra).
Relatório: `data/private/de10-2026-09-26/p04-echo-report.json`; recepção vazia:
`p04-echo-received.bin`. Resultado **FAIL/inconclusivo quanto à causa**; não
prova se UART_RX deixou de reconhecer os quadros ou se a saída/caminho de
retorno está interrompido. Registrar agora LEDR1/2/3/5/6/7/8/9 e observar
simultaneamente RX/TX no AD2 antes de outra regravação ou envio.

O [diagnóstico físico de 02:41–02:54](diagnostico-p04-de10-2026-09-26.md)
isolou a falha antes do receptor UART: `uart_scope` foi recebido pelo host
em W10; a ponte antiga e um SOF que espelha V10 diretamente em W10 não
retornaram os bytes enviados pelo CP2102. Durante 500 bytes escritos pelo
host, o AD2 registrou 1.500.000 amostras do próprio TXD do CP2102 sempre
acima de 3,26 V; CH1 já estava no TXD, não diretamente no metal de V10.
Após reset USB do CP2102 o eco continuou 0/5. O próximo passo é substituir
temporariamente a fonte serial pelo DIO0 do AD2, retirando o fio TXD→V10
antes da nova conexão para evitar dois drivers no mesmo nó.
P04 permanece pendente.

**Captura completa P04 `-07`, 29/09/2026, 13:21 (Manaus):** o relatório
`data/private/de10-2026-09-29/p04-baseline-5b-report-07.json` passou: vetor
`55 A5 00 FF 3C`, 5/5 bytes, sem timeout, divergência ou extras. O contexto é
`data/private/de10-2026-09-29/p04-baseline-5b-context-07.json`; o recebido tem
SHA-256 `086a1a8a2575a3f80eb8a942552cfaf94825e511f1ec0df2448b4bfc97b68b01`, igual
à referência. O tempo da transação foi 16,863 ms no host e inclui Linux/USB;
não representa latência isolada da FPGA.

O CSV `~/CapturasWaveForms/TesteP04.csv` foi adquirido às 13:21:11.913, cerca de
54 ms antes do fim do relatório. Configuração: 8.192 amostras, 400 kS/s, janela
nominal de 20,48 ms, trigger CH1 em descida a 1,5 V, 1 V/div e offset 0 V nos
dois canais. Considerando a ligação CH1=V10/RX e CH2=W10/TX, a amostragem dos
bits em 9600 baud decodifica, em cada canal, os cinco bytes
`55 A5 00 FF 3C`, com start e stop válidos. CH1 variou de −0,103 a 3,425 V e
CH2 de −0,031 a 3,395 V; assim, o nível baixo de 1,149 V observado em `-06` não
se repetiu com os offsets zerados e escala de 1 V/div. Os inícios de quadro
indicam cerca de 104,1 µs/bit, compatível com os 104,167 µs nominais a 9600 baud.
O primeiro start de CH2 ocorre aproximadamente 0,990 ms após o de CH1. Essa
diferença é do caminho RX→TX observado e não deve ser reportada como latência
interna isolada da FPGA.

Relatório SHA-256 `e017188ef8a39056da9b2ea3112258ccb4b2d75852a18f26df832e304d51fd43`;
CSV SHA-256 `249f074f682950b91e95e5fd13aa1d5f01da967eb31f6deed4cc4bb2d301ebd0`;
workspace `.dwf3work` SHA-256
`fbf92e6423d2c17ab2100f9b253d821433f14c8423d572af9b2d7aeca7ec7176`. Resultado:
P04 baseline integrado e instrumental aprovado na DE10-Lite. A Cyclone IV foi
retirada do escopo ativo; P05 secure e P06 instrumental são executados somente
na DE10-Lite.

### P05 — Secure na placa

1. Programar `build/de10_lite/secure/uart_secure.sof` na DE10-Lite.
2. Antes de transmitir, pressionar e soltar KEY0 para carregar o contexto e
   confirmar que os LEDs persistentes de overflow/framing permanecem apagados.
3. Ligar CP2102 TXD→V10, W10→CP2102 RXD e GND comum; não instalar jumper
   CP2102 TXD↔RXD nem alimentar a placa pelo VCC do adaptador.
4. Enviar quatro quadros `55 A5 00 FF 3C` a 38400/8N1 (20 bytes no fluxo),
   usando contexto AES-CTR com nonce exclusivo.
5. Exigir 20 bytes recebidos sem perdas/extras e recuperação exata do texto
   original no PC. O conteúdo retornado pela FPGA deve ser ciphertext, não o
   eco em claro do estímulo.

O comparador do `scripts/serial_bench.py` verifica ciphertext/recuperação CTR;
quatro quadros totalizam 20 bytes e atravessam a fronteira do bloco de 16 bytes.
Uma repetição sempre exige nonce/contexto novo e o SOF correspondente.

**Registro histórico, 29/09/2026, 14:02 (Manaus): PASS, 5/5 bytes a
9600/8N1.** O vetor
`55 A5 00 FF 3C` retornou cifrado como `09 A3 46 AF 82`; a comparação CTR no PC
recuperou os cinco bytes originais, sem timeout, extras ou divergência. Contexto
`5aa86b553a1c43debe50b2a40de4ff10`; relatório privado
`data/private/de10-2026-09-29/p05-secure-5b-report-02.json` (SHA-256
`7b02e93f77fc01bb0d71874ad143e87a9d0196ba8f92c262c6687596d0fb99bb`); arquivo
recebido com SHA-256 `ca775cee0ddbb90e31f2da46cb6413950f4a1033e94a5ba606244ca9763546e3`.
O build secure foi feito para MAX 10 `10M50DAF484C7G`, 50 MHz/9600 baud, e
programado no dispositivo `10M50DAF484@1`; SOF SHA-256
`cf71a3db60d3bcfee699b85bab96c21fe0c8a2ce8ecd641d5759600d92c70d1b`.
O contexto privado (chave/nonce) permanece fora da documentação pública.
O tempo da transação no host foi 16,728 ms; inclui Linux/USB e não mede a
latência isolada da FPGA. O relatório também declara que CTR não autentica os
dados. Essa execução é do perfil antigo de 9600 baud e não encerra o P05 para
a configuração então vigente de 38400/8N1.

**Ensaio DE10-Lite, 29/09/2026, 18:16 (Manaus): FAIL.** O build secure atual
foi compilado para MAX 10 `10M50DAF484C7G`, 50 MHz/38400 baud; auditoria passou
nos três cantos temporais. SOF SHA-256
`a7971612b73df307dc6d00053a96bc424a3b1ab29e72256c7ceb9a834f463d25`. O
relatório privado
`data/private/de10-2026-09-29/p05-secure-20b-38400-report-01.json` registra
4/4 transações e 20/20 bytes sem timeout, perda ou extras, mas cada resposta
foi exatamente `55 A5 00 FF 3C`. O SHA-256 recebido coincide com o do estímulo
(`1ec8f144575a9c265334dfa2c385532741170ab730f39f5e38a9fae7f8517e5d`); a
recuperação CTR não coincide (`39caa78f90c0cf8c94a0b1142cd2c92cdb54ce70338aad1852fa153355cb5a3f`).
Portanto, o enlace serial retornou texto claro, não ciphertext. A simulação
`make integration` passou depois do ensaio para AES ligado/desligado a 50 MHz,
wrappers DE10-Lite e 36 testes Python; isso valida o RTL/modelo, não o bitstream
carregado na placa. O primeiro contexto foi reivindicado e não pode ser
reutilizado. Essa execução permanece registrada como tentativa reprovada; o
reteste posterior com nova programação e novo contexto está abaixo.

**Reteste P05 DE10-Lite, 29/09/2026 às 18:32 (Manaus): PASS.** O usuário
programou `build/de10_lite/secure/uart_secure.sof`; o Quartus confirmou
`Configuration succeeded` no MAX 10 `10M50DAF484@1`, checksum `0x0059B2E2`.
Com contexto/nonce novo, foram enviadas quatro transações de cinco bytes a
38400/8N1. Recebidos 20/20 bytes de ciphertext, sem perdas, extras ou timeout;
a decifragem independente no PC recuperou exatamente os 20 bytes de entrada.
SHA-256 da referência/recuperação:
`1ec8f144575a9c265334dfa2c385532741170ab730f39f5e38a9fae7f8517e5d`;
SHA-256 do ciphertext recebido:
`594d430e1a9e09a58cf6ff0e4a7f1f342a3ef1bb1b05a32a7e6823645793ad59`.
Relatório privado `data/private/de10-2026-09-29/p05-secure-20b-38400-report-02.json`.
Os 259,658 ms medidos pelo host incluem Linux/USB e não são latência interna
da FPGA. **Situação atual do P05: aprovado na DE10-Lite.**

### P06 — Secure no osciloscópio ou Analog Discovery 2

Depois de P05 aprovado, repetir a medição na DE10-Lite: CH1 em `V10` e CH2 em
`W10`, captura a 38400/8N1. Usar contexto novo e capturar o estímulo e a
resposta cifrada; a decifragem/igualdade deve ser verificada no PC, não apenas
pela inspeção visual. Timestamps do host serial não isolam a latência interna
da FPGA.

**Registro histórico, 29/09/2026, 14:02 (Manaus):** a captura abaixo foi feita
no perfil antigo 9600/8N1 e não conclui o P06 atual. O CSV
`~/CapturasWaveForms/TesteP05.csv` foi salvo às 14:02:47.533, com 8.192 amostras
a 400 kS/s (20,48 ms), trigger de descida do CH1 em 1,5 V, 1 V/div e offset
0 V. Com CH1 em V10/RX e CH2 em W10/TX, a amostragem nos centros dos bits
decodifica `55 A5 00 FF 3C` em CH1 e `09 A3 46 AF 82` em CH2; start/stop 8N1
válidos nos dez quadros. O bit time estimado pelos inícios dos quadros foi
104,063 µs em CH1 e 104,188 µs em CH2, compatível com 9600 baud dentro da
resolução de 2,5 µs/amostra. O primeiro quadro de saída começou cerca de
0,990 ms após o primeiro start de entrada; esse intervalo inclui a recepção
serial do byte e não é latência isolada da cifra.

Nos centros dos bits, CH1 apresentou nível baixo médio de −0,052 V e alto médio
de 3,390 V; CH2, baixo médio de 0,014 V e alto médio de 3,350 V. Considerando
todas as amostras, as faixas foram −0,096–3,433 V (CH1) e −0,034–3,391 V (CH2).
CSV SHA-256 `36a01fbab4b7ec70b6300afaaf4a9ec57d104c675a78661b899b5d45d28039ee`;
workspace `.dwf3work` SHA-256
`7655dbf33123385b9cdcc6d005eab07bf60fb024af99db171ddcacf92c4aed9a`. O CSV
identifica os canais como Channel 1/2; a associação V10/W10 vem da montagem da
bancada, não de metadados gravados no arquivo.

**Registro histórico:** a captura descrita acima valida somente o perfil
9600/8N1. Ela não conclui o P06 vigente a 38400; a Cyclone IV está fora do
escopo.

**P06 a 38400, 29/09/2026 às 19:03 (Manaus): PASS.** Foi usado contexto
AES-CTR privado novo para cinco bytes em
`data/private/de10-2026-09-29/p06-secure-5b-38400-context-01.json`; chave e
nonce permanecem privados. O build secure passou no Quartus e na auditoria dos
três cantos, sem violações. Pior slack de setup: 10,569 ns; menor slack de
hold: 0,096 ns. SOF:
`build/de10_lite/secure/uart_secure.sof` (SHA-256
`70bc00d47c4c9559e6fb4904c655783b123fa1ef036008ddc23139a63c129d00`).

Montagem usada: CP2102 TXD→V10, W10→CP2102 RXD e GND comum, sem jumper TXD↔RXD;
AD2 CH1+→V10, CH1−→GND; CH2+→W10, CH2−→GND. Captura DC, 1 V/div, offset
0 V, 800 kS/s, 8.192 amostras (10,239 ms), trigger de descida do CH1 em 1,5 V.
O comando de host executado foi:

```bash
make serial-bench CP2102_PORT=/dev/ttyUSB0 BAUD=38400 TRIALS=1 CONTEXT_FILE=data/private/de10-2026-09-29/p06-secure-5b-38400-context-01.json REGISTRY=data/private/nonce-registry.json RECEIVED=data/private/de10-2026-09-29/p06-secure-5b-38400-received-01.bin REPORT=data/private/de10-2026-09-29/p06-secure-5b-38400-report-01.json
```

O relatório privado
`data/private/de10-2026-09-29/p06-secure-5b-38400-report-01.json` registra
**5/5 bytes recebidos**, sem timeout, perda, extras ou divergência. Entrada:
`55 A5 00 FF 3C`; ciphertext recebido: `14 D8 F4 3D 63`. A decifragem CTR
independente recuperou exatamente a entrada. SHA-256 do ciphertext:
`e80f629d07586546353b05aa1d678916257dbc245442fb6f1e0bd554fca9e8e0`; SHA-256
da referência/recuperação:
`086a1a8a2575a3f80eb8a942552cfaf94825e511f1ec0df2448b4bfc97b68b01`.

O CSV do AD2, adquirido às 19:03:19 com 8.192 amostras a 800 kS/s, foi
decodificado independentemente nos centros dos bits: CH1 contém
`55 A5 00 FF 3C` e CH2 contém `14 D8 F4 3D 63`; os dez stop bits foram válidos.
O bit time estimado por ajuste das bordas é 26,000 µs em CH1 e 26,042 µs em
CH2. Faixas completas observadas: −0,092 a 3,433 V (CH1) e −0,045 a 3,388 V
(CH2). A ligação dos canais a V10/W10 é a usada na bancada e não está codificada
nos metadados do CSV. O início do primeiro TX ocorreu ~247,5 µs após o primeiro
start RX; esse intervalo inclui a recepção do byte e não isola a latência do
AES. Os 68,983 ms reportados pelo host incluem Linux/USB e também não são
latência interna da FPGA.

Capturas arquivadas no repositório: [CSV do AD2](evidence/de10-lite-m9-p06-secure-ad2-2026-09-29.csv)
e [workspace WaveForms](evidence/de10-lite-m9-p06-secure-ad2-2026-09-29.dwf3work).
SHA-256: CSV `cf33576897ec8a0db90663b26f8672ca95d05b13f33d307ac5b29a3eb2a74300`;
workspace `87192a501969b109b35ec28d4c8bd7c88e1df370c8267d8a7ebb44b1adb0bf21`;
relatório privado `b9e3da3deacb63f67d181e1380cd034212792e96c84cf2d2b4583af2b9f699ef`.
**Situação P06: concluído e aprovado na DE10-Lite.** Para uma nova execução,
criar contexto/nonce e SOF novos; não reutilizar o contexto reivindicado.

O AD2, a instalação do WaveForms e o formato das evidências estão descritos no
[guia específico de instrumentação](analog-discovery-2-waveforms.md). A
enumeração do dispositivo e a abertura do aplicativo não encerram P04/P06 sem
captura dos sinais da placa; a captura histórica P06 a 9600 acima comprova
somente a DE10-Lite e não conclui a configuração atual a 38400.

### P07 — Captura e entrada física do NEO-M8N

O receptor adotado é o u-blox NEO-M8N, com saída UART a 38400/8N1. O perfil foi
confirmado após ciclo de energia. P07 valida a ligação física direta com a
DE10-Lite, sem processamento intermediário por outro microcontrolador.

1. Com a FPGA desconectada, ligar GPS TX ao RXD do CP2102 e GND comum; manter
   TXD do adaptador sem conexão. Capturar a saída a 38400/8N1.
2. Validar a captura completa com `scripts/gps_capture.py`: bytes ASCII,
   terminações CRLF, checksums válidos e sentenças completas. Manter a captura
   privada se contiver dados de localização.
3. Programar o baseline a 38400/8N1. Ligar GPS TX→V10 (JP1 posição física 1),
   GND comum e W10 (TX da FPGA)→RXD do CP2102. Não unir saídas TX.
4. Confirmar atividade de recepção e ausência de framing/overflow; capturar no
   PC o fluxo que sai da FPGA e validar os bytes NMEA.

**Execução física em 29/09/2026 — DE10-Lite, 50 MHz, 38400/8N1:** a captura
direta de referência preservou 4.096 bytes; `gps_capture.py` validou 66
sentenças NMEA, CRLF e checksums, SHA-256
`d38b8617eab8315ddfd0c1299553159ddec9bf4de3e7b5fd4718e9c2811f9d34` (18 bytes
de fragmento final). Com o baseline programado, a saída física da FPGA também
preservou 4.096 bytes e passou a validação NMEA com 67 sentenças, SHA-256
`0a83593d473a5f8ea56f884935c5c124187c080ed0504b6f8ce4cddc4d60d0b6` (21 bytes
de fragmento final). Os tempos de aquisição do host foram 5,447 s e 5,750 s;
não representam latência da FPGA. Como as capturas GPS ocorreram em momentos
diferentes, não se compara o conteúdo/hash entre elas. **Resultado:** passagem
física e integridade NMEA aprovadas; falta anotar se LEDR6 (overflow) e LEDR7
(framing) permaneceram apagados. Arquivos binários e relatórios ficam em
`data/private/de10-2026-09-29/` e não devem ser publicados, pois contêm dados
GPS.

O [datasheet da família u-blox NEO-M8](https://content.u-blox.com/sites/default/files/NEO-M8-FW3_DataSheet_UBX-15031086.pdf)
e o [Receiver Description/Protocol Specification](https://content.u-blox.com/sites/default/files/products/documents/u-blox8-M8_ReceiverDescrProtSpec_UBX-13003221.pdf)
são referências da família adotada.

### P08 — GPS no baseline

Capturar uma referência independente das sentenças GPS, executar o baseline e
comparar byte a byte a entrada com a saída. Repetir pelo menos três vezes.

Registrar número de bytes, perdas, framing errors, overflow, latência e maior
ocupação da FIFO.

**Repetição 1/3 — 29/09/2026, DE10-Lite, baseline a 38400/8N1:** replay da
referência GPS privada de 4.096 bytes, com o CP2102 em full-duplex. **PASS**:
4.096/4.096 bytes recebidos, zero faltantes/extras, sem timeout e sem
divergência; SHA-256 da entrada e da resposta
`d38b8617eab8315ddfd0c1299553159ddec9bf4de3e7b5fd4718e9c2811f9d34`. Tempo da
transação observado pelo host: 1,078 s; tempo total no host: 1,135 s — ambos
incluem Linux/USB/CP2102 e não medem latência isolada da FPGA. Relatório
privado: `p08-baseline-4096-report-01.json`.

**Repetição 2/3 — 29/09/2026, DE10-Lite, baseline a 38400/8N1:** **PASS**,
4.096/4.096 bytes recebidos, zero faltantes/extras, sem timeout e sem
divergência. Os hashes SHA-256 da entrada e da resposta coincidem com a
referência (`d38b8617eab8315ddfd0c1299553159ddec9bf4de3e7b5fd4718e9c2811f9d34`).
Tempo da transação no host: 1,078 s; tempo total: 1,136 s, sem representar
latência isolada da FPGA. Relatório privado:
`p08-baseline-4096-report-02.json`.

**Repetição 3/3 — 29/09/2026, DE10-Lite, baseline a 38400/8N1:** **PASS**,
4.096/4.096 bytes recebidos, zero faltantes/extras, sem timeout e sem
divergência. Os hashes da entrada e da resposta coincidem:
`d38b8617eab8315ddfd0c1299553159ddec9bf4de3e7b5fd4718e9c2811f9d34`. Tempo
observado no host: 1,078 s por transação e 1,136 s total, incluindo Linux/USB/
CP2102. Relatório privado: `p08-baseline-4096-report-03.json`.

**Situação: replay baseline 3/3 aprovado.** Ainda falta registrar LEDR6/LEDR7
e, quando disponível, a indicação de ocupação da FIFO. Não colar a saída JSON
completa do replay em registros compartilhados: os campos hexadecimais contêm
o payload GPS.

### P09 — GPS no secure

Repetir o mesmo replay no secure, capturar o ciphertext e decifrá-lo no PC com
o mesmo contexto registrado no experimento. A saída recuperada deve ser
idêntica à referência GPS original.

**Preparação de hardware — 29/09/2026:** compilação secure concluída sem erros;
auditoria temporal aprovada nos três corners, sem paths violados. O arquivo
`build/de10_lite/secure/uart_secure.sof`, gerado para o contexto privado de
4.096 bytes, foi programado via JTAG no MAX 10 (`10M50DAF484@1`, checksum
`0x005973F4`).

**Execução — 29/09/2026, DE10-Lite secure, replay GPS de 4.096 bytes a
38400/8N1:** **PASS**, 4.096 bytes cifrados recebidos, zero faltantes/extras,
sem divergência; decifragem CTR recuperou exatamente a referência e o
ciphertext diferiu do texto original. Tempo observado pelo host: 1,078 s por
transação e 1,135 s total; inclui Linux/USB/CP2102, não é latência isolada da
FPGA. Relatório privado: `p09-secure-4096-report-01.json`.

**Situação: replay secure P09 aprovado.**

### P10 — Transferência longa da captura GPS

Reproduzir pela serial a captura NMEA previamente adquirida do GPS e comparar
todos os bytes recebidos e recuperados nos modos baseline e secure. Esse ensaio
verifica uma transferência contínua de 32 KiB com entrada determinística; como
o GPS não fica conectado durante o replay, ele não equivale a uma aquisição
prolongada ao vivo. Idealmente, registrar também erros, overflow e ocupação
máxima da FIFO.

**Referência longa — 29/09/2026:** captura direta do NEO-M8N a 38400/8N1,
32.768/32.768 bytes; validador aprovou 537 sentenças NMEA completas, com
fragmento final de 15 bytes preservado. SHA-256:
`d80dc4be9f143c9500dd5db3d4a968bb730871bfc49a7b57c509edb6c12985fd`. A
aquisição levou 41,336 s no host; não é latência da FPGA. Arquivos privados:
`p10-gps-reference-01.bin` e relatórios `p10-gps-reference-01-*.json`.

O SOF baseline foi programado via JTAG no MAX 10 (`10M50DAF484@1`, checksum
`0x0029C5BB`). **Replay baseline de 32 KiB — primeira tentativa, 30/09/2026:
falhou.** Foram recebidos 5.732 de 32.768 bytes; houve timeout e primeira
divergência no offset 4.617. **Repetição com a ferramenta lendo RX durante o
envio — aprovada.** O CP2102 recebeu os 32.768 bytes, sem perdas, extras,
timeout ou divergência; o SHA-256 coincide com a referência
(`d80dc4be9f143c9500dd5db3d4a968bb730871bfc49a7b57c509edb6c12985fd`). GPS
desconectado durante o replay. Tempo da transação: 8,545 s; tempo total do
host: 8,603 s, incluindo Linux/USB/CP2102; não é latência isolada da FPGA. A
tentativa inicial permanece registrada como falha; o resultado aprovado é da
repetição `p10-baseline-32768-report-02.json`.

**Replay secure de 32 KiB — 30/09/2026: aprovado.** O CP2102 transmitiu os
32.768 bytes da mesma referência armazenada e recebeu 32.768 bytes de ciphertext,
sem perdas, extras, timeout ou divergência. O ciphertext difere da referência;
a decifragem CTR independente recuperou exatamente os 32.768 bytes originais.
Tempo da transação: 8,546 s; tempo total do host: 8,604 s, incluindo
Linux/USB/CP2102, não uma medida isolada da latência FPGA. O GPS permaneceu
desconectado. Relatório e capturas privados em
`data/private/de10-2026-09-29/p10-secure-32768-report-01.json` e arquivos
adjacentes; não publicar dados de localização/ciphertext. O contexto CTR deste
ensaio foi consumido e não deve ser reutilizado.

**Estado do P10:** transferência longa baseline e secure aprovadas. Isso valida
o replay de uma captura GPS previamente armazenada, mas não encerra a campanha de
estabilidade: o registro dos indicadores físicos de erro/overflow e o teste de
reset e recuperação ainda estão pendentes (P11).

### P11 — Reset e recuperação física

O teste usa o modo secure e um contexto CTR recém-gerado. Ele verifica os dois
comportamentos do KEY0 e a proteção contra reutilização do mesmo fluxo
AES-CTR. O GPS fica desconectado; usar CP2102 em 38400/8N1, TXD→V10, W10→RXD e
GND comum.

1. Programar um SOF secure compilado com contexto novo. Sem enviar bytes,
   confirmar LEDR1 e LEDR5 acesos e LEDR9 apagado.
2. Pressionar e soltar KEY0 antes de qualquer byte. A configuração deve ser
   carregada novamente: LEDR1/LEDR5 acesos e LEDR9 apagado.
3. Enviar uma única carga conhecida de 5 bytes pelo ensaio serial. Confirmar
   cinco bytes de ciphertext, recuperação exata no PC e LEDR6/LEDR7 apagados;
   após a drenagem, LEDR8 também deve apagar.
4. Depois que TX retornar ao repouso, pressionar e soltar KEY0. Como o contexto
   já foi usado, o wrapper mantém esse estado fora do reset: LEDR1/LEDR5 devem
   apagar, LEDR9 deve acender e TX deve permanecer ocioso. Enviar um byte de
   sondagem e confirmar que não há resposta; essa sondagem testa o bloqueio e
   não é uma nova captura AES válida.
5. Para recuperar o serviço, gerar outro contexto com nonce novo, compilar e
   programar outro SOF secure. Confirmar LEDR1/LEDR5 acesos, LEDR9 apagado e
   validar uma nova carga conhecida. KEY0, sozinho, não deve rearmar um
   contexto já consumido.

Não reutilizar o primeiro contexto/nonce para uma nova captura após os 5 bytes
serem processados. Cada contexto secure deve ser exclusivo; preservar ambos os
relatórios e não publicar chave, nonce ou dados GPS privados.

**Etapas 1–3 — 30/09/2026: aprovadas.** A configuração iniciou corretamente;
KEY0 antes de qualquer dado permitiu rearmar o contexto. A captura secure de
5 bytes recebeu 5/5 bytes, sem extras, perdas ou timeout; a decifragem
independente recuperou exatamente o estímulo. Tempo da transação: 12,397 ms;
tempo total do host: 70,152 ms — inclui Linux/USB/CP2102 e não é latência
isolada da FPGA. Relatório privado: `p11-secure-pre-reset-5b-report-01.json`.
Os indicadores LEDR6/LEDR7/LEDR8 após a transmissão não foram registrados
separadamente.

**Etapa 4 — 30/09/2026: aprovada.** Após o envio dos 5 bytes, KEY0 foi
pressionado e o CP2102 enviou o byte de sondagem `0x55`. Não houve resposta;
LEDR0 continuou piscando e LEDR9 acendeu, conforme esperado para o contexto
consumido em bloqueio. Isso confirma o bloqueio após reset, não uma segunda
captura AES.

**Etapa 5 — 30/09/2026: aprovada.** Um contexto CTR com nonce novo foi
compilado em outro SOF secure e programado após o bloqueio. A nova carga passou:
5/5 bytes recebidos, sem extras, perdas ou timeout; a decifragem recuperou
exatamente o estímulo. Tempo de transação: 12,201 ms; tempo total do host:
64,826 ms — inclui Linux/USB/CP2102, não é latência isolada da FPGA. Relatório
privado: `p11-secure-recovery-5b-report-01.json`.

**P11 — sequência de reset, bloqueio e recuperação aprovada.** Os indicadores
LEDR6/LEDR7/LEDR8 após as transferências não foram registrados separadamente.

## Registro histórico da Cyclone IV — fora do escopo atual

Os ensaios seguintes foram executados antes da decisão de 29/09 e ficam
preservados para rastreabilidade. Não há requisito de completar nem repetir
P01–P11 nesta placa; a matriz ativa é somente a DE10-Lite.

A placa disponível é a ZRTECH/WXEDA V2.00 com `EP4CE6E22C8N`. O perfil de
48 MHz e os pinos J3 validados estão documentados em
[`bancada-cyclone4-2026-09-21.md`](bancada-cyclone4-2026-09-21.md). Os builds
`uart_scope`, `baseline` e `secure` já passaram no Quartus e geraram SOF. P01,
P02 e P03 possuem evidência física; P04–P11 ainda dependem da bancada.

Executar C0/P01/P02 primeiro. Só depois de confirmar JTAG, alimentação, pinagem
e aproximadamente `104,17 µs` por bit em `uart_scope` executar P03–P11 nos
projetos `cyclone4/baseline` e `cyclone4/secure`. Se a medição indicar cerca de
`416,7 µs`, interromper e revisar o clock/pinagem antes de continuar. Não
conectar o GPS enquanto a tensão lógica e o GND não forem confirmados.

## Diagnósticos da revisão — 20/09/2026

| Ensaio | Resultado | Limite |
| --- | --- | --- |
| `make check` | PASS: 27 simulações, 9 configurações de lint, 31 testes Python | Não comprova GPS/bancada integrada |
| Estudo de capacidade EP4CE6E22C8 | PASS: 351/6.272 LE baseline; 5.626/6.272 LE secure | Sem pinagem, SDC de bancada, SOF ou timing físico |
| Latência nominal GPS | RX válido → início TX: 80 ns; → fim TX: 1.041.680 ns; quadro → TX: 989.643 ns | RTL em 50 MHz/9600; não substitui o replay físico |
| Reset do contexto estático | Wrapper aceitou contexto inicial e bloqueou reuso após RX | Proteção validada em RTL; não é gerenciamento de chaves |
| Relatório temporal negativo injetado | Extrator rejeitou slack negativo e registros incompletos | Cópias de diagnóstico; relatórios reais preservados |
| Entradas NMEA inválidas | Identificador, controles ASCII, checksum e limite rejeitados | Validador corrigido; origem física ainda pendente |

Artefatos locais em `build/review-2026-09-20/`; referências às linhas de código
e próximos passos na [revisão](revisao-completa-2026-09-20.md).

## Registro de cada execução

Para cada teste futuro, acrescentar uma entrada com:

```text
Data/hora:
Commit do RTL:
Placa/dispositivo:
Projeto e SOF:
Entrada usada:
Contexto/nonce do ensaio:
Instrumentos e configuração:
Resultado:
Evidência:
Observações:
```

Última atualização: 29/09/2026. **Registro histórico a 9600 baud:** P01/P02 da
Cyclone IV, P01/P02 da DE10-Lite, P03/P04 baseline e P05/P06 secure da
DE10-Lite foram executados. Esses resultados não concluem os testes a 38400.
Na configuração anterior, P05 retornou 5/5 bytes cifrados e o PC recuperou o
vetor original; P06 também passou a 38400, com cinco bytes cifrados e
recuperados no PC e captura AD2 concordante. O próximo passo ativo é executar
P07 para validar bytes reais do GPS e observar os indicadores RX/framing/overflow. P08/P09
usarão depois a mesma referência bruta no baseline e no secure; a validação
física GPS segue sujeita ao S20 antes da comparação.

## Execuções registradas em 18–22/09/2026

| Comando | Resultado | Observação |
| --- | --- | --- |
| `make lint` | **Passou** | Lint UART, AES, CTR, bridge e tops DE10-Lite; acesso ao Docker local foi necessário |
| `make gps-replay` | **Passou em 20/09** | 5 sentenças NMEA, 309 bytes CRLF, checksums válidos |
| `make integration` | **Passou novamente em 22/09** | Baseline e secure em clock acelerado e 50 MHz/9600; 2.681 bytes por modo sem divergência; 34 testes PC aprovados |
| `make integration-gps` | **Passou em 20/09** | Replay completo de 309 bytes em 50 MHz/9600; FIFO máxima 2 bytes; baseline/secure recuperados no PC |
| `make baseline-fpga` | **Passou** | SOF, fit e auditoria temporal concluídos |
| `make secure-fpga` | **Passou** | SOF, fit e auditoria temporal concluídos |
| `make context` | **Passou** | 7 testes de criação, permissões, limites, renderização e reutilização de nonce |
| `make pc` | **Passou em 22/09** | 34 testes, incluindo captura, comparação, contexto, replay, bancada CP2102, métricas e validação NMEA bruta |
| `make gps-capture-check` | **Pronto em 20/09** | Requer `GPS_CAPTURE=...`; valida um arquivo real quando a captura estiver disponível |
| `make check` | **Passou novamente em 22/09** | Código 0; 27 simulações, nove configurações de lint, estrutura e 34 testes Python |
| `make cyclone4-uart-fpga` | **Passou em 21/09** | SOF `build/cyclone4/uart_scope/uart_scope.sof`; programação física e P01/P02 registrados |
| `make cyclone4-baseline-fpga` / `make cyclone4-secure-fpga` | **Passou em 22/09** | SOFs e auditoria de três cantos `PASS`; alvo `EP4CE6E22C8`, 48 MHz |
| `make cyclone4-metrics` | **Passou em 22/09** | Baseline 299 LE/104,08 MHz; secure 5.580 LE/83,56 MHz; métricas pós-fit, não bancada |
| `python3 -m unittest tb.test_serial_bench -v` | **Passou em 22/09** | Host CP2102 em porta virtual: baseline e secure full-duplex, contexto e relatório privado |
| `make uart` | **Parcial** | O primeiro teste `uart_rx` passou; a gravação seguinte parou com `No space left on device` no ambiente de execução |

O erro de espaço registrado na execução histórica de `make uart` ocorreu ao
gravar artefatos locais de teste, não em uma simulação com falha funcional. A
regressão global posterior passou sem esse erro.
