# Validação dos manuscritos — 20/09/2026

## Objetivo

Evitar que uma revisão futura dos rascunhos perca as métricas atuais ou trate
simulação, análise pós-fit e captura sintética como validação física.

## Alterações

- Os rascunhos em inglês e português passaram a documentar o validador de
  captura NMEA e o procedimento para preservar seu relatório/hash.
- A seção de método registra as evidências atuais: 27 simulações HDL, nove
  configurações de lint e 31 testes Python.
- O plano de validação final foi atualizado para validar a referência bruta
  antes da comparação baseline/secure.
- `scripts/manuscript_check.py` verifica métricas, formato do replay e a
  declaração explícita de que a validação física ainda está pendente.

## Resultado

```text
make manuscript-check
PASS manuscript check: English draft
PASS manuscript check: Portuguese draft
PASS manuscript check: current metrics and physical-validation limits are disclosed
```

O verificador não avalia qualidade editorial, referências ou adequação ao
template do evento. Ele é uma proteção factual mínima para as duas versões do
rascunho.

## Próximo passo

Revisar o texto com o orientador e, quando houver bancada, substituir ou
complementar a seção de resultados com registros físicos, sem apagar as
evidências RTL/Quartus já documentadas.
