# Plano de testes e registro de resultados

Este é o documento vivo dos ensaios do projeto. Cada teste deve ser atualizado
com a data, o commit do RTL, a configuração usada, o resultado e a evidência
correspondente. Simulação, compilação e bancada física são resultados
diferentes e não devem ser misturados.

Revisão em 22/09: a reconciliação com o remoto foi concluída, as correções de
área, métricas, contexto/reset e aquisição foram testadas e os resultados foram
regenerados. Na Cyclone IV, a variante de bancada foi programada e os ensaios
físicos de TX e loopback foram aprovados com o acesso J3. O host ESP32/ESP-IDF
foi compilado, gravado e usado para validar o baseline por um caminho externo,
sem jumper entre `PIN_100` e `PIN_103`, com GND comum conectado. A validação
física do secure, a conclusão do P04 e o GPS continuam pendentes. Antes desses
ensaios, o host recebeu coleta por eventos, prazo e guarda de bytes extras; os
LEDs integrados da Cyclone IV passaram a expor overflow e framing persistentes.
A latência nominal abaixo não contém pausas artificiais.

## Configuração fixa

- Placa principal: DE10-Lite, MAX 10 `10M50DAF484C7G`.
- Clock: 50 MHz.
- Segundo alvo obrigatório: Cyclone IV E `EP4CE6E22C8N`, placa ZRTECH/WXEDA V2.00;
  perfil de 48 MHz, com pinagem de bancada registrada em
  [`docs/bancada-cyclone4-2026-09-21.md`](bancada-cyclone4-2026-09-21.md).
- UART: 9600 baud, 8N1.
- Caminho baseline: `UART RX -> FIFO -> UART TX`.
- Caminho secure: `UART RX -> FIFO -> AES-128-CTR -> UART TX`.
- Entradas e saídas da DE10-Lite: RX em `V10` e TX em `W10`.
- Variantes FPGA: projetos Quartus separados em `fpga/de10_lite/baseline/` e
  `fpga/de10_lite/secure/`; para a Cyclone IV, `fpga/cyclone4/uart_scope/`,
  `fpga/cyclone4/baseline/` e `fpga/cyclone4/secure/`.

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
| S14 | Regressão final | `make check` após a reconciliação | Nenhuma regressão nos módulos já aprovados | **Repetido em 22/09** — código 0; 27 simulações, lint, estrutura e PC |
| S15 | Contexto do ensaio | `make context` e `make pc` | Contexto privado, nonce novo e registro sem chave em claro | **Concluído em 20/09** — 7 testes de contexto; a suíte atual tem 31 testes PC |
| S16 | Contexto no wrapper | Testbench do top DE10-Lite com parâmetros substituídos | Ciphertext observado no TX corresponde ao contexto de elaboração | **Concluído em 19/09** — `make integration`, `0x55 -> 0xe2` |
| S17 | Contexto no build Quartus | `CONTEXT_FILE=... make secure-fpga` e validação do pacote gerado | O JSON é validado, o modo é conferido e o pacote privado entra no SOF | **Concluído em 20/09** — baseline/secure compilados; programação física pendente |
| S18 | Replay NMEA estruturado | `make gps-replay`, `make integration` e testes PC | Sentenças ASCII com checksum válido são convertidas para CRLF e preservadas nos modos baseline/secure | **Concluído em 20/09** — 5 sentenças, replay sintético de 309 bytes, RTL/PC; GPS físico pendente |
| S19 | Replay GPS em clock de produção | `make integration-gps` e `--verify-gps` | Os 309 bytes do replay atravessam baseline e secure em 50 MHz/9600 sem perda, overflow ou divergência | **Concluído em 20/09** — FIFO máxima de 1 byte; 80 ns de RX válido até início do TX e 1.041.680 ns até fim; físico pendente |
| S20 | Validação de captura NMEA | `scripts/gps_capture.py` e `make pc` | Captura bruta completa, ASCII, CRLF, checksum e limite NMEA aprovados antes do experimento | **Concluído em 20/09** — 31 testes Python; captura física ainda pendente |

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
| F01 | Compilação baseline | `make baseline-fpga` | Versão Quartus, SHA, SOF, warnings e status | **Regenerado em 20/09** — sem erros; manifest `PASS` no commit reconciliado |
| F02 | Compilação secure | `make secure-fpga` | Versão Quartus, SHA, SOF, warnings e status | **Regenerado em 20/09** — sem erros; manifest `PASS` no commit reconciliado |
| F03 | Timing baseline | Auditoria Quartus em todos os cantos | Setup, hold, recovery, removal, Fmax e caminhos não cobertos | **Concluído em 18/09** — todos os slacks positivos |
| F04 | Timing secure | Auditoria Quartus em todos os cantos | Setup, hold, recovery, removal, Fmax e caminhos não cobertos | **Concluído em 18/09** — todos os slacks positivos |
| F05 | Recursos baseline | Relatório pós-fit | Elementos lógicos, registradores, memória e pinos | **Regenerado em 20/09** — 347 LE, 216 FF, 8.192 bits, 14 pinos |
| F06 | Recursos secure | Relatório pós-fit | Elementos lógicos, registradores, memória e pinos | **Regenerado em 20/09** — 5.622 LE, 917 FF, 8.192 bits, 14 pinos |
| F07 | Comparação | `secure - baseline` | Custo absoluto e percentual da inclusão do AES | **Concluído em 20/09** — tabela pós-merge abaixo |
| F08 | Extração reprodutível | `make metrics` | JSON/Markdown gerados diretamente dos relatórios Quartus | **Concluído em 20/09** — hashes e manifests conferidos; [relatório de métricas](metricas-fpga-2026-09-20.md) |
| F09 | UART autônoma Cyclone IV | `make cyclone4-uart-fpga` / `make cyclone4-j3-uart-fpga` | SOF, dispositivo, clock, pinagem e auditoria temporal | **P01/P02 aprovados em 21/09** — TX em `PIN_100`, RX em `PIN_103`, 48 MHz/9600 baud, loopback físico aprovado |
| F10 | Baseline/secure Cyclone IV | `make cyclone4-baseline-fpga` e `make cyclone4-secure-fpga` | Quatro builds comparáveis, manifests e SOFs separados | **Regenerado em 22/09 no Quartus** — ambos `PASS`, com LEDs de erro; bancada secure pendente |
| F11 | Métricas Cyclone IV | `make cyclone4-metrics` | LE, registradores, memória, Fmax e slacks dos dois builds | **Regenerado em 22/09** — baseline 299 LE/104,08 MHz; secure 5.580 LE/83,56 MHz; dados em `build/cyclone4/metrics.md` |

Os relatórios de F01–F07 devem ficar em `build/` e ser resumidos em uma tabela
do artigo. Os resultados da UART autônoma não devem ser usados como se fossem
os resultados do sistema GPS integrado.

### Resultado dos builds DE10-Lite — 20/09/2026

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
SHA-256: ffe074b4dcd50ad50edacd4f6b817bc9a614477fafad8485736f02bdd577c8ad

secure uart_secure.sof
SHA-256: 5f54cffcc5a5b8ca776b32c067896fb8971d41e3d88155c4913788303e879c89
```

O Quartus 25.1 compilou as duas revisões sem erros. Os avisos do fit ficam
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

## Testes físicos — DE10-Lite e Cyclone IV

O cronograma fechado para executar P01–P11 nas duas plataformas entre 21 e
25/09 está em [`docs/cronograma.md`](cronograma.md). O freeze físico ocorre na
sexta-feira; o fim de semana fica reservado à redação do artigo.

### P01 — UART autônoma

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

**Resultado: concluído em 21/09/2026.** Esse ensaio valida os pinos e a UART
autônoma; não valida ainda FIFO, AES ou GPS.

### P03 — Baseline na placa

1. Compilar e programar `uart_baseline.sof`.
2. Pressionar e soltar KEY0.
3. Confirmar LED de configuração/atividade.
4. Apresentar bytes por uma fonte UART independente em J3 `PIN_103`.
5. Observar a retransmissão em J3 `PIN_100` com o host ESP32.
6. Registrar erros, eventos, ocupação e comportamento após reset.

No ensaio de 21/09, o ESP32 enviou `55 A5 00 FF 3C` pela GPIO17 e o monitor
recebeu o mesmo vetor com cinco bytes. A configuração usada foi ESP32 UART2,
9600/8N1, GPIO17→J3 `PIN_103`, J3 `PIN_100`→GPIO16 e GND comum.

**Situação: aprovado para o caminho externo.** Não havia jumper entre J3
`PIN_100` e `PIN_103`; o vetor retornou pelo enlace ESP32 → FPGA → ESP32.
Registro completo:
[`validacao-esp32-cyclone4-2026-09-21.md`](validacao-esp32-cyclone4-2026-09-21.md).

Para as próximas repetições, o host ESP32 coleta por fila de eventos: cinco
bytes devem chegar em até 30 ms e uma guarda de 10 ms detecta bytes extras. O
log `RESULT` registra tamanho, igualdade, timeout, extras, framing, paridade,
overflow e falhas do host; `SUMMARY` acumula os contadores. A entrada é limpa
somente uma vez na inicialização para não esconder bytes tardios. O campo
`host_window_us` é tempo do driver/RTOS e não será usado como latência da FPGA.

Nos tops integrados da Cyclone IV, os LEDs ativos em zero são: `LED[0]`
heartbeat, `LED[1]` configuração/atividade, `LED[2]` overflow persistente e
`LED[3]` framing persistente. Essa associação é idêntica no baseline e no
secure.

### P04 — Baseline no osciloscópio

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

**Situação: pendente.** Falta medir a forma de onda do baseline no osciloscópio
com o enlace externo. Na primeira observação foram vistos aproximadamente
`30 µs` entre picos na visão afastada e `680 ns` entre picos de uma borda na
visão aproximada; a descida foi de cerca de `−32 ns` até a estabilização em
`800 ns`, isto é, aproximadamente `0,83 µs` de acomodação. Esses números ainda
não são o bit time. Repetir com ponta ×10 e massa curta, medindo as bordas
lógicas estáveis até obter aproximadamente `104,17 µs`. Também foram observados
picos preliminares de `−1,52 V` e `4,92 V`; como excedem os trilhos de 3,3 V,
devem ser tratados como possível artefato da sonda até a repetição com massa
curta.

Configuração obrigatória para fechar o P04: ponta ×10, entrada de 1 MΩ,
acoplamento DC, massa curta ou mola de terra e, se disponível, limite de banda
de 20 MHz. A força de saída permanece em 8 mA durante essa repetição. Somente
se duas capturas corretas ainda mostrarem excursões fora de `−0,3 V` a `3,6 V`
será criada uma variante experimental com 4 mA e slew rate lento; essa variante
deverá ser aplicada de forma idêntica ao baseline e ao secure antes de qualquer
comparação.

### P05 — Secure na placa

1. Programar `uart_secure.sof`.
2. Resetar com KEY0 e aguardar a configuração automática.
3. Confirmar atividade/configuração e manter apagados os LEDs persistentes de
   overflow e framing.
4. Enviar a mesma sequência usada no baseline.
5. Observar a saída cifrada em `W10` na DE10-Lite ou J3 `PIN_100` na Cyclone IV.
6. Capturar exatamente cinco bytes, decifrar no PC com o contexto registrado e
   comparar com `55 A5 00 FF 3C`.

**Situação: pendente.**

### P06 — Secure no osciloscópio

Repetir a medição nos pinos específicos da plataforma. Na DE10-Lite, usar CH1
em `V10` e CH2 em `W10`; na Cyclone IV, CH1 em J3 `PIN_103` e CH2 em J3
`PIN_100`. A forma de onda deve continuar sendo 9600/8N1; o conteúdo cifrado
será verificado no PC, não visualmente no osciloscópio. Timestamps do ESP32 ou
de um adaptador USB–UART não substituem essa medição de latência.

**Situação: pendente.**

### P07 — Entrada do GPS

Quando o NEO-M8N estiver disponível:

1. Confirmar alimentação e terra comuns.
2. Medir o TX do GPS antes de conectá-lo ao RX da FPGA.
3. Confirmar atividade serial, nível lógico e 9600/8N1.
4. Conectar GPS TX ao `V10`.
5. Confirmar que o LED de recepção alterna sem framing error.

**Situação: pendente — módulo disponível; alimentação, referência serial e
conexão física ainda não foram registrados.**

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

## Testes obrigatórios da Cyclone IV

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

Última atualização: 22/09/2026. P01/P02 da Cyclone IV e P03 do baseline externo
foram registrados; a instrumentação que antecede o P04 foi implementada e
compilada. O próximo registro esperado é a repetição do P04 com ponta ×10,
massa curta e medição do bit time; depois serão executados os projetos `secure`
nas duas plataformas. A captura GPS deverá passar pelo S20 antes da comparação.

## Execuções registradas em 18–22/09/2026

| Comando | Resultado | Observação |
| --- | --- | --- |
| `make lint` | **Passou** | Lint UART, AES, CTR, bridge e tops DE10-Lite; acesso ao Docker local foi necessário |
| `make gps-replay` | **Passou em 20/09** | 5 sentenças NMEA, 309 bytes CRLF, checksums válidos |
| `make integration` | **Passou novamente em 22/09** | Baseline e secure em clock acelerado e 50 MHz/9600; 2.681 bytes por modo sem divergência; 31 testes PC aprovados |
| `make integration-gps` | **Passou em 20/09** | Replay completo de 309 bytes em 50 MHz/9600; FIFO máxima 2 bytes; baseline/secure recuperados no PC |
| `make baseline-fpga` | **Passou** | SOF, fit e auditoria temporal concluídos |
| `make secure-fpga` | **Passou** | SOF, fit e auditoria temporal concluídos |
| `make context` | **Passou** | 7 testes de criação, permissões, limites, renderização e reutilização de nonce |
| `make pc` | **Passou em 20/09** | 31 testes, incluindo captura, comparação, contexto, replay, métricas e validação NMEA bruta |
| `make gps-capture-check` | **Pronto em 20/09** | Requer `GPS_CAPTURE=...`; valida um arquivo real quando a captura estiver disponível |
| `make check` | **Passou novamente em 22/09** | Código 0; 27 simulações, nove configurações de lint, estrutura e 31 testes Python |
| `make cyclone4-uart-fpga` | **Passou em 21/09** | SOF `build/cyclone4/uart_scope/uart_scope.sof`; programação física e P01/P02 registrados |
| `make cyclone4-baseline-fpga` / `make cyclone4-secure-fpga` | **Passou em 22/09** | SOFs e auditoria de três cantos `PASS`; alvo `EP4CE6E22C8`, 48 MHz |
| `make cyclone4-metrics` | **Passou em 22/09** | Baseline 299 LE/104,08 MHz; secure 5.580 LE/83,56 MHz; métricas pós-fit, não bancada |
| `idf.py build` | **Passou em 22/09** | Host ESP32 por eventos, prazo de 30 ms, guarda de 10 ms e logs estruturados; ainda não gravado nesta revisão |
| `make uart` | **Parcial** | O primeiro teste `uart_rx` passou; a gravação seguinte parou com `No space left on device` no ambiente de execução |

O erro de espaço registrado na execução histórica de `make uart` ocorreu ao
gravar artefatos locais de teste, não em uma simulação com falha funcional. A
regressão global posterior passou sem esse erro.
