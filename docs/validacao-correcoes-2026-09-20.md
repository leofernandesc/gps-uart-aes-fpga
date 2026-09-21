# Validação das correções e reconciliação — 20/09/2026

## Escopo

Esta etapa trata os achados da revisão de 20/09 que não dependem de placa:
extração de métricas, validação NMEA, latência nominal do replay e proteção do
contexto estático após reset.

## Alterações

- `scripts/fpga_metrics.py` agora exige um log de timing aprovado, todos os
  quatro checks em todos os cantos auditados, um relatório Fmax por canto,
  status PASS do build e rejeita slack negativo com sinal explícito.
- `scripts/gps_fixture.py` rejeita identificador NMEA inválido, corpo vazio,
  caracteres ASCII de controle e sentenças que excedam 82 bytes incluindo CRLF.
  A leitura do fixture tolera a conversão LF→CRLF do checkout Windows.
- O testbench do replay de produção não injeta mais as pausas artificiais de
  backpressure; a latência nominal deve ser regenerada em ambiente com
  simulador HDL antes de atualizar os números do artigo.
- O wrapper DE10-Lite carrega o contexto estático somente no primeiro reset
  após a programação. Um reset posterior deixa o bridge inativo e exige nova
  programação, evitando reutilizar silenciosamente nonce e contador.

## Evidências executadas

```text
python3 -m unittest discover -s tb -p 'test_*.py' -v
Ran 31 tests ... OK
python -m py_compile scripts/fpga_metrics.py scripts/gps_fixture.py \
  scripts/gps_capture.py scripts/capture.py tb/test_fpga_metrics.py \
  tb/test_gps_fixture.py
git diff --check
make check
make integration-gps
make cyclone4-capacity
make baseline-fpga
make secure-fpga
make metrics
```

Os testes negativos cobrem slack negativo, ausência do status de build, captura
NMEA corrompida/incompleta, identificador inválido, NUL e limite de comprimento.
O `make check` passou com a regressão HDL, lint, síntese estrutural e verificação
independente no PC. O replay GPS nominal passou nos dois modos com 309 bytes,
FIFO máxima de 1 byte e sem stalls artificiais. Os builds DE10-Lite terminaram
com manifestos `PASS` e a auditoria de métricas aceitou o par somente depois de
confirmar hashes e cobertura temporal completa.

O estudo Cyclone IV passou somente como análise de capacidade: baseline 351 LE /
216 registradores e secure 5.626 LE / 917 registradores. Ainda não há SOF,
pinagem, clock de bancada ou programação da placa Cyclone IV.

## Limites e próximo passo

Esta etapa não prova o comportamento elétrico do GPS nem da Cyclone IV. Os
ensaios físicos continuam dependentes da confirmação da placa, do oscilador,
da pinagem e da disponibilidade do NEO-M8N. O wrapper integrado, entretanto,
foi verificado em RTL para power-up, reset antes da recepção e bloqueio de
reutilização do contexto depois do primeiro byte.
