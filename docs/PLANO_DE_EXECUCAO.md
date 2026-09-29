# Plano de execução e colaboração

Atualizado em **29/09/2026**. O andamento e as evidências ficam em
[`cronograma.md`](cronograma.md); este plano define o experimento vigente e as
tarefas restantes para a submissão BTSym’26 até 30/09.

## Escopo e pergunta experimental

Avaliar o custo de acrescentar AES-128-CTR em hardware à aquisição e transmissão
serial de dados GPS, comparando duas elaborações do mesmo RTL na DE10-Lite:

```text
NEO-M9N-00B-00 → UART RX → FIFO → [baseline | AES-128-CTR] → UART TX → PC
```

Baseline e secure usam o MAX 10 `10M50DAF484C7G`, clock de 50 MHz, UART
38400/8N1, FIFO e interfaces idênticas. A presença do AES é a única diferença
arquitetural do par. A FPGA é o objeto experimental; o PC recebe bytes via
CP2102 e verifica eco ou decifragem. O teste de sistema pode usar primeiro uma
captura NMEA real reproduzida pelo CP2102 para tornar a comparação byte a byte
repetível, e depois uma conexão GPS direta para demonstrar a aquisição real.

O sensor é exclusivamente o **u-blox NEO-M9N-00B-00**. A UART ativa é
38400/8N1, taxa padrão do M9N; não se fará comparação de baud rates. O módulo
receptor tem VCC de 2,7–3,6 V e I/O referido a VCC. Isso não define a entrada
de alimentação do breakout: confirmar carrier, pinagem, VCC e níveis antes de
conectar. A Cyclone IV e o NEO-M8 foram retirados do escopo e não participam
da metodologia nem da comparação do artigo; os registros datados permanecem
preservados como histórico.

AES-CTR fornece confidencialidade, mas não autenticação/integridade nem proteção
contra replay ou spoofing GNSS. Não fazer alegações mais amplas.

## O que deve ser refeito e o que continua válido

Os ensaios físicos anteriores da UART e dos tops integrados foram realizados a
9600 baud. Como a duração do bit muda de aproximadamente 104,17 µs para
26,04 µs, repetir na DE10-Lite:

| Ensaio | Repetir? | Razão / evidência exigida |
| --- | --- | --- |
| P01/P02 UART autônoma e loopback | Sim | Nova temporização; quadro 0x55, 26,04 µs/bit, LEDs e captura |
| P03/P04 baseline | Sim | Rebuild 38400, eco do vetor conhecido e captura RX/TX |
| P05/P06 secure | Sim | Rebuild 38400, ciphertext e recuperação PC; novo nonce por captura |
| AES-128/CAVP e CTR oracle | Não isoladamente | Independentes da UART; reexecutados como parte de `make check` |
| Replay NMEA RTL, métricas e Quartus | Sim | Regenerar resultados no ponto real 50 MHz/38400 |
| Captura física NEO-M9N | Primeira execução | Validar taxa, níveis, NMEA e aquisição serial real |

Os resultados antigos em 9600 permanecem no diário, identificados como
históricos; não devem ser apresentados como resultados da configuração final.
Tempos de host incluem Linux/USB/CP2102 e não medem latência isolada da FPGA.

## Tarefas de implementação e validação

1. **Concluído em 29/09:** atualizar defaults e tops da UART, host e captura
   para 38400/8N1, mantendo o clock da DE10-Lite em 50 MHz.
2. **Concluído em 29/09:** `make check`, `make integration-gps` e
   `make manuscript-check` passaram; fixture NMEA e integração foram
   conferidas nos modos baseline/secure.
3. **Concluído em 29/09:** `make baseline-fpga`, `make secure-fpga` e
   `make metrics` passaram; ambos os SOFs e relatórios pós-fit foram gerados,
   sem programação física da placa.
4. **Pendente:** na bancada, repetir P01–P06 em 38400 com DE10-Lite, CP2102 e AD2. Registrar
   vetor, byte time/frame, canal/pino, escala, trigger, arquivo bruto, versão do
   SOF e resultado dos LEDs. Reprogramar entre baseline e secure.
5. **Pendente:** conferir o breakout do M9N e capturar sua UART diretamente pelo CP2102. Validar
   bytes NMEA completos, CRLF, checksums e SHA-256; proteger coordenadas pessoais.
6. **Pendente:** demonstrar GPS→FPGA→PC diretamente, observando entrada e saída. Para uma
   comparação determinística baseline/secure, reapresentar a mesma captura real
   validada como estímulo CP2102→FPGA e conferir eco/decifragem byte a byte.
7. **Pendente:** fazer teste contínuo com duração e total de bytes registrados; relatar erros,
   perdas/overflow e limites da medição. Se a etapa GPS física não couber antes
   da submissão, descrevê-la explicitamente como pendente e não inventar dados.
8. **Pendente até 30/09:** atualizar manuscritos PT/EN com apenas resultados reproduzidos, revisar template,
   referências, figuras e limitações e submeter até 30/09. Preservar comprovante.

## Cronograma final

| Data | Prioridade | Critério de saída |
| --- | --- | --- |
| 29/09 | RTL/host 38400, regressão, replay GPS simulado, Quartus baseline/secure e métricas | Logs `PASS`, SOFs atuais, timing sem violações e dados novos no relatório |
| 29/09 | P01–P06 na DE10-Lite | UART/loopback, eco baseline, CTR secure e capturas correspondentes; estados separados |
| 29–30/09 | Captura M9N e integração | NMEA validado; conexão direta e/ou replay físico claramente identificados |
| 30/09 | Artigo e submissão | Revisão PT/EN, números rastreáveis, limitações explícitas e comprovante BTSym |

O prazo interno de bancada de 25/09 foi ultrapassado e não é mais o marco
vigente. Se o tempo restante obrigar priorização, manter como mínimo: regressão
e builds a 38400, baseline/secure físicos com vetor conhecido, métricas
reproduzidas e manuscrito sem alegações de GPS físico que não tenham evidência.

## Colaboração e controle de mudanças

- `docs/cronograma.md` é a fonte de verdade do andamento. Atualizá-lo após cada
  implementação, build, teste, decisão ou revisão do artigo.
- Cada registro inclui data efetiva, commit/configuração, comando, resultado e
  caminho/hash da evidência; simulação, Quartus e bancada nunca se substituem.
- Alterações em arquitetura, materiais ou datas devem ser refletidas no README e
  em `docs/proposta_btsym_gps_fpga.html`; manter a cópia em Documents sincronizada
  quando existir.
- Antes de commit/pull, revisar diffs completos, preservar trabalho local/alheio
  e rodar `git diff --check`. Para RTL, rodar `make check`.
- Não versionar chave privada, contexto real, captura GPS com coordenadas ou
  relatórios sensíveis. Guardar bitstreams/logs locais salvo decisão explícita.

## Comandos ativos

```bash
make check
make integration-gps
make baseline-fpga
make secure-fpga
make metrics
make serial-bench CP2102_PORT=/dev/ttyUSB0 CONTEXT_FILE=contexto.json RECEIVED=saida.bin REPORT=relatorio.json
make gps-capture-check GPS_CAPTURE=data/private/ensaio/gps-reference.bin
make manuscript-check
```
