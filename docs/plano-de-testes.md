# Plano de testes e registro de resultados

Este é o documento vivo dos ensaios do projeto. Cada teste deve ser atualizado
com a data, o commit do RTL, a configuração usada, o resultado e a evidência
correspondente. Simulação, compilação e bancada física são resultados
diferentes e não devem ser misturados.

Atualização de escopo em 29/09: sensor u-blox NEO-M9N-00B-00; somente
DE10-Lite/MAX 10 no experimento ativo; Cyclone IV abandonada e M8 fora do
escopo. A UART mudou de 9600 para 38400/8N1. Os resultados P01/P02, P03/P04 e
P05/P06 anteriores continuam como evidência histórica a 9600; P01 já foi
repetido a 38400 para quadro e temporização, enquanto P02–P06 ainda precisam
ser executados na configuração vigente. Os testes funcionais AES independentes do link
serial permanecem válidos. Em 29/09, `make check` passou com 36 testes Python
e oráculos AES/CTR; `make integration-gps` passou para baseline e secure em
50 MHz/38400 nos 309 bytes sintéticos. O P01 físico a 38400 passou no nível de
quadro: o AD2 capturou e permitiu decodificar `0x55` em 8N1; a periodicidade
entre quadros não foi medida. P02–P06 e a captura física do M9N seguem
pendentes. Tempos de host incluem PC/USB e não são latência isolada da FPGA.

## Configuração fixa

- Placa: DE10-Lite, MAX 10 `10M50DAF484C7G`.
- Clock: 50 MHz.
- Sensor: u-blox NEO-M9N-00B-00; configuração UART padrão 38400/8N1.
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

### P01 — UART autônoma a 38400 baud — 29/09/2026

**Resultado: aprovado para temporização e conteúdo do quadro.** O `uart_scope`
na DE10-Lite/MAX 10 (50 MHz) transmite `0x55` em 38400/8N1. A captura AD2
corrigida mostra o sinal no CH2; a análise usou cruzamentos de 1,65 V e os
centros de bit.

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
| Conclusão | Quadro, padrão de dados e temporização aprovados; periodicidade de 100 ms não medida |

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

**Limite e próximo passo:** os 819,1 µs capturam só um quadro e não confirmam
que o `uart_scope` repete a transmissão a cada 100 ms. Antes de P02, fazer uma
captura em Record mode no CH2 a aproximadamente 400 kS/s por pelo menos 250 ms
(cerca de 100 mil amostras), com trigger de descida a 1,5 V. Critério: observar
ao menos três inícios de quadro e medir dois intervalos próximos de 100 ms.
Depois, P02 verifica TX→RX por jumper, LEDs de recepção/erro e o quadro a 38400.

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
- Próxima aquisição de P01: Record mode, CH2, ~400 kS/s, ≥250 ms e trigger de
  descida a 1,5 V; registrar pelo menos três inícios de quadro.

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

Para as próximas repetições, `scripts/serial_bench.py` envia quatro quadros de
cinco bytes, observa uma guarda de 10 ms para bytes extras e produz um relatório
JSON com tamanho, igualdade, timeout, extras e hashes. O tempo do host não será
usado como latência da FPGA. A porta é armada depois da programação e suas filas
são limpas antes do primeiro quadro.

Nos tops integrados da Cyclone IV, os LEDs ativos em zero são: `LED[0]`
heartbeat, `LED[1]` configuração/atividade, `LED[2]` overflow persistente e
`LED[3]` framing persistente. Essa associação é idêntica no baseline e no
secure.

### P04 — Baseline no osciloscópio ou Analog Discovery 2

Com o baseline recebendo o vetor de teste, medir a saída em `W10` na DE10-Lite
ou em J3 `PIN_100` na Cyclone IV. Se houver dois canais, medir também a entrada
em `V10` na DE10-Lite ou J3 `PIN_103` na Cyclone IV:

- nível de repouso alto;
- start, oito bits e stop;
- aproximadamente `104,17 µs` por bit;
- aproximadamente `1,0417 ms` por quadro de um byte;
- aproximadamente `5,208 ms` para os cinco bytes, sem contar o repouso;
- vários bytes consecutivos sem quadro truncado;
- intervalo entre RX e TX, se os dois canais estiverem disponíveis.

**Situação: concluído na DE10-Lite em 29/09/2026; captura equivalente na
Cyclone IV pendente.** A captura e o eco byte a byte da DE10-Lite estão
registrados abaixo. Na primeira observação foram vistos aproximadamente
`30 µs` entre picos na visão afastada e `680 ns` entre picos de uma borda na
visão aproximada; a descida foi de cerca de `−32 ns` até a estabilização em
`800 ns`, isto é, aproximadamente `0,83 µs` de acomodação. Esses números ainda
não são o bit time. Repetir com ponta ×10 e massa curta, medindo as bordas
lógicas estáveis até obter aproximadamente `104,17 µs`. Também foram observados
picos preliminares de `−1,52 V` e `4,92 V`; como excedem os trilhos de 3,3 V,
devem ser tratados como possível artefato da sonda até a repetição com massa
curta.

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
P04 baseline integrado e instrumental aprovado na DE10-Lite. Para fechar P04
nas duas plataformas, repetir a aquisição na Cyclone IV (RX em `PIN_103`, TX em
`PIN_100`, perfil de 48 MHz); depois seguir para P05 secure com contexto
criptográfico registrado.

### P05 — Secure na placa

1. Programar `uart_secure.sof`.
2. Resetar com KEY0 e aguardar a configuração automática.
3. Confirmar atividade/configuração e manter apagados os LEDs persistentes de
   overflow e framing.
4. Enviar a mesma sequência usada no baseline.
5. Observar a saída cifrada em `W10` na DE10-Lite ou J3 `PIN_100` na Cyclone IV.
6. Capturar exatamente cinco bytes, decifrar no PC com o contexto registrado e
   comparar com `55 A5 00 FF 3C`.

No contexto público de bring-up, a primeira resposta esperada é
`5B 72 25 65 E1`. O comparador do `scripts/serial_bench.py` exige sequência
consecutiva, ausência de erros e recuperação CTR exata; quatro tentativas
também atravessam a primeira fronteira de bloco de 16 bytes.

**Resultado DE10-Lite, 29/09/2026, 14:02 (Manaus): PASS, 5/5 bytes.** O vetor
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
dados. Esta é uma execução física de cinco bytes, não um teste de estabilidade.

**Situação:** P05 aprovado na DE10-Lite; pendente na Cyclone IV.

### P06 — Secure no osciloscópio ou Analog Discovery 2

Repetir a medição nos pinos específicos da plataforma. Na DE10-Lite, usar CH1
em `V10` e CH2 em `W10`; na Cyclone IV, CH1 em J3 `PIN_103` e CH2 em J3
`PIN_100`. A forma de onda deve continuar sendo 9600/8N1; o conteúdo cifrado
será verificado no PC, não visualmente no osciloscópio. Timestamps do host
serial não substituem essa medição de latência.

**Resultado DE10-Lite, 29/09/2026, 14:02 (Manaus): PASS instrumental.** O CSV
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

**Situação:** P06 aprovado na DE10-Lite; captura equivalente pendente na Cyclone IV.

O AD2, a instalação do WaveForms e o formato das evidências estão descritos no
[guia específico de instrumentação](analog-discovery-2-waveforms.md). A
enumeração do dispositivo e a abertura do aplicativo não encerram P04/P06 sem
captura dos sinais da placa; a captura P06 acima comprova apenas a DE10-Lite.

### P07 — Entrada física do GPS M9N

Executar após compilar e programar a UART/baseline da DE10-Lite a 38400 baud:

1. Conferir os rótulos e a pinagem do breakout. O módulo NEO-M9N-00B-00 exige
   VCC dentro de 2,7–3,6 V e seus I/O são referidos a VCC; isso **não** define
   a tensão de entrada do pino VCC de uma placa breakout. Seguir a documentação
   da placa concreta, não conectar alimentação por suposição.
2. Ligar GND comum e alimentar o breakout com a tensão nele especificada.
   Antes de conectar ao FPGA, medir em TX repouso alto e níveis compatíveis com
   a entrada 3,3 V da DE10-Lite.
3. Conectar GPS TX a `V10` (JP1 pino físico 1). Para salvar referência no PC,
   conectar também esse TX a CP2102 RXD (ambos são entradas). Manter CP2102 TXD
   e FPGA W10 desconectados desse nó; não unir saídas.
4. Gravar 512 bytes a 38400/8N1 e validar as sentenças NMEA completas incluídas
   na captura. Verificar perdas e overflow; uma captura curta não prova
   estabilidade sob o volume de mensagens habilitado.
5. Confirmar LEDR2 alternando, LEDR7 (framing) e LEDR6 (overflow) apagados.

O [datasheet u-blox NEO-M9N-00B](https://content.u-blox.com/sites/default/files/NEO-M9N-00B_DataSheet_UBX-19014285.pdf)
declara UART padrão 38400/8N1 e VCC 2,7–3,6 V. O [manual de integração](https://content.u-blox.com/sites/default/files/NEO-M9N_Integrationmanual_UBX-19014286.pdf)
recomenda não operar abaixo da taxa padrão e adverte sobre perda se o volume de
mensagens exceder a largura de banda configurada.

Comando de captura de referência, após confirmar alimentação e ligações:

```bash
python3 scripts/capture.py record \
  --port /dev/ttyUSB0 \
  --baud 38400 \
  --output data/private/de10-2026-09-29/p07-gps-direct-512b-01.bin \
  --bytes 512 \
  --timeout 60 \
  --report data/private/de10-2026-09-29/p07-gps-direct-512b-01-report.json

python3 scripts/gps_capture.py \
  --input data/private/de10-2026-09-29/p07-gps-direct-512b-01.bin \
  --allow-partial-edges \
  --report data/private/de10-2026-09-29/p07-gps-direct-512b-01-nmea-report.json
```

**Situação em 29/09/2026:** P01 da UART autônoma foi medido a 38400, mas nenhum
teste físico do GPS foi feito. O baseline programado anteriormente é de 9600
baud e não deve ser conectado ao TX do M9N antes de ser recompilado e programado
com a configuração nova. A pinagem/alimentação do breakout deve ser conferida;
nenhum dado GPS foi capturado nesta etapa.

### P08 — GPS no baseline

Capturar uma referência independente das sentenças GPS, executar o baseline e
comparar byte a byte a entrada com a saída. Repetir pelo menos três vezes.

Registrar número de bytes, perdas, framing errors, overflow, latência e maior
ocupação da FIFO.

**Situação: pendente.**

### P09 — GPS no secure

Repetir o mesmo replay no secure, capturar o ciphertext e decifrá-lo no PC com
o mesmo contexto registrado no experimento. A saída recuperada deve ser
idêntica à referência GPS original.

**Situação: pendente.**

### P10 — Estabilidade contínua

Manter o GPS transmitindo por uma duração registrada e comparar todos os bytes
recebidos e recuperados. O ensaio deve registrar perdas, erros, overflow,
ocupação máxima da FIFO e primeira divergência, se houver.

**Situação: pendente.**

### P11 — Reset e recuperação física

Repetir um ensaio após pressionar KEY0, confirmando que:

- o TX volta ao nível ocioso;
- bytes da captura anterior não são transmitidos;
- a configuração é carregada novamente;
- uma nova captura funciona com um novo contexto.

**Situação: pendente.**

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
vetor original; P06 decodificou entrada e saída completas em captura AD2, com
bit time próximo de 104,17 µs e níveis lógicos próximos de 0–3,3 V. O próximo
passo ativo é concluir P07 na DE10-Lite: capturar/validar bytes reais do GPS e
observar os indicadores RX/framing/overflow. P08/P09 usarão depois a mesma
referência bruta no baseline e no secure; a validação física GPS segue sujeita
ao S20 antes da comparação.

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
