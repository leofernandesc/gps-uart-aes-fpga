# Sprints finais do artigo BTSym'26

Atualizado em **30/09/2026**. A fonte de verdade do progresso é
[`cronograma.md`](cronograma.md). Os artefatos de bancada, chaves, contextos e
capturas ficam em `data/private/` e não devem ser versionados.

## Sprint 0 — Integridade das alegações e regressão de software

**Feito nesta rodada:** a auditoria dos contextos experimentais mostrou que as
capturas secure anteriores foram feitas com a chave pública do vetor de
conformidade FIPS. O artigo PT/EN e a fonte LNCS foram corrigidos: essas
capturas demonstram o datapath AES-CTR e a recuperação independente, mas não
sigilo operacional. Um novo contexto de laboratório com chave aleatória foi
gerado em arquivo privado; o bitstream correspondente foi compilado e auditado
em diretório isolado, mas não programado. O gerador de contexto agora oferece
`--random-key`, mantendo a chave no arquivo privado e fora da saída de terminal.
Não imprimir, copiar para Git ou reutilizar essa chave/contexto.

**Gate:** `make pc`, `make manuscript-check`, `make paper-check`, `make metrics`
e `git diff --check` aprovados; executar novamente antes do commit.

## Sprint 1 — P14: comparação simultânea GPS bruto/ciphertext

### Objetivo e critérios de aprovação

Capturar em paralelo o mesmo fluxo: AD2 DIO0 observa GPS-TX/FPGA-V10; DIO1
observa FPGA-W10; CP2102 RX também observa W10. Para cada variante, exigir
bytes de entrada = bytes da saída baseline ou bytes recuperados do ciphertext,
sem realinhamento, além de bytes CP2102 idênticos aos amostrados em DIO1.
Captura inválida se houver amostras perdidas/corrompidas, erro UART, falso
start, reset, LEDR6/LEDR7 aceso ou incompletude. O piloto inicial é 1 KiB; se
passar, repetir com 32 KiB para a evidência do artigo.

### Bancada

- GPS breakout TX → DE10-Lite V10 (JP1, pino físico 1) → AD2 DIO0.
- DE10-Lite W10 (JP1, pino físico 2) → AD2 DIO1 e CP2102 RXD.
- GND comum entre GPS, FPGA, AD2 e CP2102.
- GPS alimentado a 3,3 V pela breakout; deixe VCC do GPS desligado até aparecer
  `READY` no terminal.
- CP2102 TXD, VCC e pinos de alimentação ficam desconectados. GPS RX fica sem
  conexão. Não faça jumper V10–W10. Não pressione KEY0 durante a captura.
- AD2 conectado ao PC; feche WaveForms para liberar `libdwf`. DIO0/DIO1 são
  entradas de captura; o script desabilita saídas digitais do AD2.
- Configure/programa-se a FPGA antes de alimentar o GPS. Com GPS desligado,
  deixe os sinais conectados e confirme GND comum.

### Ordem de execução

1. **Baseline, piloto 1 KiB:** grave o SOF isolado abaixo. No terminal da raiz
   do repositório, inicie `record`; só ligue VCC do GPS após `READY`. Ao final,
   desligue o GPS e rode `analyze`, confirmando LEDs 6/7 apagados e nenhum reset.

```bash
/home/leofernandesc/intelFPGA_lite/25.1/quartus/bin/quartus_pgm -c 'USB-Blaster [1-3]' -m jtag -o 'p;/home/leofernandesc/gps-uart-aes-fpga/build/experiments/p14-baseline-pilot-01/uart_baseline.sof'

python3 scripts/ad2_live_capture.py record --port /dev/ttyUSB0 --context data/private/de10-2026-09-30/p14-baseline-pilot-context-01.json --build build/experiments/p14-baseline-pilot-01 --output data/private/de10-2026-09-30/p14-baseline-pilot-capture-01 --rate 1000000 --timeout 90 --confirm-source-inactive --confirm-txd-disconnected

python3 scripts/ad2_live_capture.py analyze --input data/private/de10-2026-09-30/p14-baseline-pilot-capture-01 --context data/private/de10-2026-09-30/p14-baseline-pilot-context-01.json --confirm-led6-off --confirm-led7-off --confirm-no-reset
```

2. **Secure, piloto 1 KiB:** grave somente o SOF compilado a partir do contexto
   `p14-secure-private-pilot-context-01.json`. Rode `record` uma única vez com
   o contexto original e o registry. Uma tentativa secure consome nonce mesmo
   se falhar; em caso de falha, gere contexto/chave/nonce novos, compile novo
   SOF e use nomes de saída novos. Nunca repetir uma sessão CTR com o mesmo
   par chave/nonce.

```bash
/home/leofernandesc/intelFPGA_lite/25.1/quartus/bin/quartus_pgm -c 'USB-Blaster [1-3]' -m jtag -o 'p;/home/leofernandesc/gps-uart-aes-fpga/build/experiments/p14-secure-private-pilot-01/uart_secure.sof'

python3 scripts/ad2_live_capture.py record --port /dev/ttyUSB0 --context data/private/de10-2026-09-30/p14-secure-private-pilot-context-01.json --registry data/private/nonce-registry.json --build build/experiments/p14-secure-private-pilot-01 --output data/private/de10-2026-09-30/p14-secure-private-pilot-capture-01 --rate 1000000 --timeout 90 --confirm-source-inactive --confirm-txd-disconnected

python3 scripts/ad2_live_capture.py analyze --input data/private/de10-2026-09-30/p14-secure-private-pilot-capture-01 --context data/private/de10-2026-09-30/p14-secure-private-pilot-context-01.json --confirm-led6-off --confirm-led7-off --confirm-no-reset
```

3. Se ambos pilotos passarem, criar contextos correspondentes de **32.768
   bytes** e builds isolados baseline/secure; executar a mesma captura simultânea
   nos dois modos. Só esses resultados maiores devem substituir a lacuna P13 no
   artigo. GPS permanece ligado até o gravador informar captura completa.

**Limite da sessão atual:** não há dispositivos USB visíveis para o agente
(CP2102/AD2/USB-Blaster). Assim, compilação e preparação podem ser feitas aqui;
programação, observações de LEDs e aquisição física precisam ser executadas no
computador conectado à bancada. O resultado só conta após análise do
`comparison.json` e inspeção dos artefatos privados.

## Sprint 2 — P15: estresse de replay armazenado, 1 MiB

Não é aquisição GPS ao vivo. O arquivo P07 de 4.096 bytes, validado como NMEA,
foi repetido apenas por sentenças completas para formar uma carga determinística
de 1.048.576 bytes; apenas a fronteira final da carga pode terminar em sentença
parcial. O gerador preserva hash/linhas de origem e cria arquivos privados sem
sobrescrita. A captura P10 bruta de 32 KiB não está disponível localmente.

Fixture criada em `data/private/de10-2026-09-30/p15-gps-workload-1m.bin`:
SHA-256 `a401226fb7d3c43a2e1a96218bf0b3c4804ddca97ef1c0eb1be027fea6eb10d`.
O validador NMEA aceitou 16.970 sentenças completas e registrou 19 bytes de
fragmento final. Relatórios privados: `p15-gps-workload-1m.json` e
`p15-gps-workload-1m-nmea.json` no mesmo diretório.

```bash
python3 scripts/stress_fixture.py --input data/private/de10-2026-09-29/p07-gps-reference-01.bin --output data/private/de10-2026-09-30/p15-gps-workload-1m.bin --report data/private/de10-2026-09-30/p15-gps-workload-1m.json --bytes 1048576
```

O fixture já existe; não repita o comando com esses caminhos porque os scripts
recusam sobrescrita. Para refazê-lo, escolha nomes ainda não usados. Os
contextos privados e builds isolados P15 também já passaram: baseline e secure
têm 1.048.576 bytes; o secure usa chave aleatória (a saída não exibe a chave).
Os SOFs não foram programados.
Se for necessário criar outros contextos/builds, `--random-key` gera a chave
secreta dentro do arquivo privado:

```bash
python3 scripts/context.py new --mode baseline --bytes 1048576 --output data/private/de10-2026-09-30/p15-baseline-1m-context-01.json
python3 scripts/context.py new --mode aes-128-ctr --bytes 1048576 --registry data/private/nonce-registry.json --output data/private/de10-2026-09-30/p15-secure-1m-context-01.json --random-key
python3 scripts/bench_build.py --context data/private/de10-2026-09-30/p15-baseline-1m-context-01.json --output build/experiments/p15-baseline-1m-01
python3 scripts/bench_build.py --context data/private/de10-2026-09-30/p15-secure-1m-context-01.json --output build/experiments/p15-secure-1m-01
```

Com o GPS desconectado, ligue CP2102 TXD→V10, W10→CP2102 RXD e GND comum;
programe a variante correspondente antes de cada replay. Os comandos JTAG são:

```bash
/home/leofernandesc/intelFPGA_lite/25.1/quartus/bin/quartus_pgm -c 'USB-Blaster [1-3]' -m jtag -o 'p;/home/leofernandesc/gps-uart-aes-fpga/build/experiments/p15-baseline-1m-01/uart_baseline.sof'
/home/leofernandesc/intelFPGA_lite/25.1/quartus/bin/quartus_pgm -c 'USB-Blaster [1-3]' -m jtag -o 'p;/home/leofernandesc/gps-uart-aes-fpga/build/experiments/p15-secure-1m-01/uart_secure.sof'
```

Reproduzir a carga pela CP2102 → FPGA → CP2102. Usar o contexto e SOF correspondentes:

```bash
python3 scripts/serial_bench.py replay --port /dev/ttyUSB0 --baud 38400 --context data/private/de10-2026-09-30/p15-baseline-1m-context-01.json --input data/private/de10-2026-09-30/p15-gps-workload-1m.bin --received data/private/de10-2026-09-30/p15-baseline-1m-received-01.bin --report data/private/de10-2026-09-30/p15-baseline-1m-report-01.json --timeout 360 > /dev/null
python3 scripts/serial_bench.py replay --port /dev/ttyUSB0 --baud 38400 --context data/private/de10-2026-09-30/p15-secure-1m-context-01.json --registry data/private/nonce-registry.json --input data/private/de10-2026-09-30/p15-gps-workload-1m.bin --received data/private/de10-2026-09-30/p15-secure-1m-received-01.bin --report data/private/de10-2026-09-30/p15-secure-1m-report-01.json --timeout 360 > /dev/null
```

Reproduzir a carga pela CP2102 → FPGA → CP2102 com GPS desconectado. Para cada
modo exigir 1.048.576 bytes capturados, zero perdas/extras, comparação exata do
baseline ou recuperação CTR exata, e zero LEDs de overflow/framing. Usar
timeout de pelo menos 360 s (transmissão serial teórica mínima ≈273 s a
38400/8N1, mais margem do host). Secure requer contexto de 1 MiB, registro de
nonce e bitstream do mesmo contexto; usar nonce novo em cada aquisição. Não
interpretar o tempo do host como latência da FPGA.

## Sprint 3 — fechar manuscrito e pacote de submissão

- Inserir os resultados P14/P15 somente se passarem os gates acima; diferenciar
  explicitamente GPS ao vivo de replay armazenado.
- Manter a chave pública dos ensaios antigos declarada como tal. Se P14 com
  chave aleatória passar, reportar essa nova evidência separadamente; não
  reescrever retroativamente os resultados antigos como confidenciais.
- Atualizar tabelas e resumos PT/EN contra os relatórios/hash dos ensaios;
  preservar limitações (CTR não autentica, sem potência medida, sem spoofing,
  sem latência física FPGA-only).
- Completar instituição/departamento e e-mail do autor correspondente; confirmar
  financiamento, conflito de interesses e demais declarações exigidas.
- Compilar com os arquivos oficiais `llncs.cls` e `splncs04.bst`, conferir
  referências/figuras e validar o PDF em no máximo 10 páginas incluindo tudo.
  O ambiente atual não tem compilador TeX nem classe Springer instalados.
- Revisão final por autores/orientador e submissão; arquivar comprovante. Não
  declarar submetido sem comprovante do sistema.

## Próxima ação

Executar primeiro o P14 baseline de 1 KiB seguindo exatamente a ordem acima.
Depois revisar a captura, então avançar para o piloto secure. Não iniciar P15
antes do gate de 32 KiB se a prioridade imediata continuar sendo fechar a
comparação simultânea GPS ao vivo. A chamada oficial lista **30/09/2026** como
deadline e não informa horário/fuso na página; a submissão é urgente, mas exige
aprovação dos autores e os metadados/declarações ainda ausentes.
