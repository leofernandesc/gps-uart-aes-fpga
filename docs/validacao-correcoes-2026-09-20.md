# Validação das correções sem hardware — 20/09/2026

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
python -m unittest tb.test_gps_fixture tb.test_fpga_metrics -v
Ran 8 tests ... OK
python -m py_compile scripts/fpga_metrics.py scripts/gps_fixture.py \
  scripts/gps_capture.py scripts/capture.py tb/test_fpga_metrics.py \
  tb/test_gps_fixture.py
git diff --check
```

Os testes negativos cobrem slack negativo, ausência do status de build, captura
NMEA corrompida/incompleta, identificador inválido, NUL e limite de comprimento.
O PTY de captura serial e a simulação HDL não foram executados neste Windows,
pois `termios` e as ferramentas `iverilog`/`verilator` não estão disponíveis.

## Limites e próximo passo

Esta entrega não gera SOF, não valida clock/pinagem da Cyclone IV e não prova o
comportamento elétrico do reset. Reexecutar `make check`, `make pc` e
`make integration-gps` em ambiente Linux com as ferramentas HDL; então registrar
a nova latência nominal e atualizar os dois manuscritos. A bancada continua
dependente da confirmação da placa Cyclone IV e da disponibilidade do GPS.
