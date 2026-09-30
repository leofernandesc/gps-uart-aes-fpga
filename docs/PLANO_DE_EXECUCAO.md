# Plano de execução e colaboração

Atualizado em **30/09/2026**. O andamento e as evidências ficam em
[`cronograma.md`](cronograma.md); este plano define o experimento vigente e as
tarefas restantes para a submissão BTSym’26 até 30/09.

## Escopo e pergunta experimental

Avaliar o custo de acrescentar AES-128-CTR em hardware à aquisição e transmissão
serial de dados GPS, comparando duas elaborações do mesmo RTL na DE10-Lite:

```text
NEO-M8N → UART RX → FIFO → [baseline | AES-128-CTR] → UART TX → PC
```

Baseline e secure usam o MAX 10 `10M50DAF484C7G`, clock de 50 MHz, UART
38400/8N1, FIFO e interfaces idênticas. A presença do AES é a única diferença
arquitetural do par. A FPGA é o objeto experimental; o PC recebe bytes via
CP2102 e verifica eco ou decifragem. O teste de sistema pode usar primeiro uma
captura NMEA real reproduzida pelo CP2102 para tornar a comparação byte a byte
repetível, e depois uma conexão GPS direta para demonstrar a aquisição real.

O sensor adotado é o **u-blox NEO-M8N**, com UART a 38400/8N1. Esse é o perfil
fixo do experimento. Os testes físicos P01–P06 na DE10-Lite foram aprovados
nessa configuração; P07/P12 validaram a aquisição direta no baseline, e P13
validou GPS ao vivo com AES-CTR e recuperação NMEA no PC. Manter GND comum
e verificar os níveis elétricos antes da conexão.
A Cyclone IV está fora do escopo atual; seus registros permanecem como histórico.

AES-CTR fornece confidencialidade, mas não autenticação/integridade nem proteção
contra replay ou spoofing GNSS. Não fazer alegações mais amplas.

## O que deve ser refeito e o que continua válido

Os ensaios físicos anteriores da UART e dos tops integrados foram realizados a
9600 baud. Como a duração do bit muda de aproximadamente 104,17 µs para
26,04 µs, repetir na DE10-Lite:

| Ensaio | Repetir? | Razão / evidência exigida |
| --- | --- | --- |
| P01 UART autônoma | Concluído em 29/09 | Dez quadros `0x55` capturados em modo Repeated; intervalo médio ~99,33 ms |
| P02 loopback UART | Concluído em 29/09 | Dez quadros `0x55` e LEDs RX válido/erro confirmados |
| P03/P04 baseline | Concluído em 29/09 | CP2102 20/20; AD2 decodifica os cinco bytes em RX e TX |
| P05/P06 secure | Concluído em 29/09 | P05 20/20 e P06 5/5 cifrados; PC recuperou a referência e AD2 confirmou os dois canais |
| AES-128/CAVP e CTR oracle | Concluído em `make check` | Independentes da UART; regressão AES/CTR aprovada |
| Replay NMEA RTL, métricas e Quartus | Concluído em 29/09 | Regressão, replay, recursos e timing atualizados para 50 MHz/38400 |
| Perfil UART do NEO-M8N | **38400/8N1 confirmado** | Perfil adotado nos novos ensaios |
| Captura física NEO-M8N na FPGA | **Concluída em 29–30/09** | P07/P12 baseline e P13 secure; 8.192 bytes e 127 sentenças NMEA em P13, LEDR6/LEDR7 apagados |

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
4. **P01–P06 concluídos na DE10-Lite a 38400 em 29/09:** P01/P02 têm
   capturas AD2 e validação do loopback; P03/P04 baseline passou por CP2102 e
   captura dos pinos; P05 secure passou com 20/20 bytes cifrados e recuperação
   exata no PC; P06 passou com 5/5 bytes, recuperação exata e decodificação
   simultânea de V10/W10 no AD2. Configuração, hashes, limites e evidências
   estão em `cronograma.md` e `plano-de-testes.md`. P07 validou fisicamente
   GPS→FPGA→PC com NMEA; P08/P09 passaram em replay de 4.096 bytes. P10
   baseline e secure passaram em 32.768 bytes, com decifragem independente exata.
   A referência foi pré-capturada e o GPS não estava conectado durante os
   replays.
5. **Concluído em 29/09:** capturar a saída UART do NEO-M8N a 38400/8N1 e
   validar sentenças NMEA, CRLF, checksums e SHA-256; manter os dados de
   localização em armazenamento privado.
6. **P08–P10 concluídos quanto aos replays:** replay determinístico da captura
   NMEA pelo CP2102→FPGA; P08/P09 em 4.096 bytes e P10 baseline/secure em
   32.768 bytes. A decifragem independente do P10 secure recuperou toda a
   referência. Não confundir replay gravado com aquisição ao vivo nem tempos de
   host com latência da FPGA.
7. **Concluído em 30/09:** P11 reset, bloqueio e recuperação com contexto novo;
   P12/P13 aquisição GPS ao vivo baseline/secure com 8.192 bytes cada. No P13,
   LEDR6/LEDR7 ficaram apagados; a entrada não foi gravada em paralelo e a
   ocupação física da FIFO não foi registrada. Os ensaios curtos não comprovam
   estabilidade prolongada nem ausência de perda de sentenças inteiras.
8. **Concluído em 30/09:** congelar o par pós-fit e vincular tabelas/resumos PT/EN
   aos hashes das fontes e dos artefatos. Os recursos selecionados são
   331/5.591 LEs e Fmax mínima 117,56/92,61 MHz. A fonte LNCS em `paper/` usa
   macros geradas e verificadas contra esse snapshot.
9. **Concluído em 30/09:** preparar o gravador simultâneo AD2 DigitalIn + CP2102
   para comparar GPS-TX/FPGA-RX com FPGA-TX sem realinhamento posterior, e
   builds isolados baseline/secure para os pilotos P14. A auditoria dos
   contextos revelou que as capturas secure anteriores usaram a chave pública
   do vetor FIPS; o manuscrito agora limita a alegação a datapath/recuperação.
   Um novo contexto de 1 KiB com chave aleatória privada foi criado e seu build
   dedicado passou compilação e auditoria temporal. SOFs ainda não foram
   programados: a sessão do agente não tem acesso aos dispositivos USB.
10. **Fixture P15 de 1 MiB preparada em 30/09:** repetidas as sentenças NMEA
    completas da referência P07 validada de 4 KiB. O validador aceitou 16.970
    sentenças completas; a captura P10 bruta de 32 KiB não está disponível no
    workspace. A fixture é replay armazenado, não GPS ao vivo; P15 ainda exige
    ensaio físico. Contextos e builds isolados baseline/secure estão prontos;
    os SOFs ainda não foram programados. Cada aquisição secure exige nonce
    novo e SOF correspondente.
11. **Pendente até a submissão:** executar P14/P15, incorporar somente resultados
    medidos, completar metadados e declarações dos autores, compilar com o pacote
    oficial Springer, confirmar até 10 páginas e submeter. Roteiro em
    [`sprints-artigo-2026-09-30.md`](sprints-artigo-2026-09-30.md).

**Auditoria temporal complementar concluída em 30/09:** minimum pulse width
passou nos três cantos dos fits selecionados, com pior margem de 9,266 ns.
Dois perfis isolados foram recompilados com identificação explícita dos
sincronizadores e hipóteses de toggle rate; o Quartus reconheceu as duas
cadeias e calculou estimativas MTBF. Esses SOFs não foram programados nem
substituem os resultados físicos ou o par do artigo. Ver
[`auditoria-temporal-2026-09-30.md`](auditoria-temporal-2026-09-30.md).
`make pc` agora passou em 53 testes. Toda aquisição secure exige nonce/contexto
novo e SOF correspondente, inclusive após ciclo de energia.

## Sprint final para a submissão — 30/09

| Data | Prioridade | Critério de saída |
| --- | --- | --- |
| 29/09 | RTL/host 38400, regressão, replay GPS simulado, Quartus baseline/secure e métricas | Logs `PASS`, SOFs atuais, timing sem violações e dados novos no relatório |
| 29/09 | P02–P06 na DE10-Lite | Loopback, eco baseline, CTR secure e capturas correspondentes; P01 já validado no nível de quadro |
| 29–30/09 | Captura NEO-M8N e integração | NMEA validado; conexão direta e/ou replay físico claramente identificados |
| 30/09 | P14 piloto e aquisição simultânea | Comparação bruta/decifrada byte a byte; preservar relatório privado |
| 30/09 | P15 estresse com fixture GPS armazenada de 1 MiB | Baseline e secure recuperados byte a byte; separar replay de aquisição ao vivo |
| 30/09 | PDF LNCS e submissão | Metadados completos, pacote oficial, até 10 páginas, revisão final e comprovante |

O prazo interno anterior de 25/09 foi ultrapassado. Priorizar P14, pois fecha a
principal lacuna da evidência GPS ao vivo, e em seguida executar ao menos um par
P15 de 1 MiB. Não apresentar replay armazenado como GPS ao vivo nem promover
resultados sem artefato de captura e verificação.

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
make timing-review
make serial-bench CP2102_PORT=/dev/ttyUSB0 CONTEXT_FILE=contexto.json RECEIVED=saida.bin REPORT=relatorio.json
make gps-capture-check GPS_CAPTURE=data/private/ensaio/gps-reference.bin
make manuscript-check
```
