# Validação da captura NMEA — 20/09/2026

## Objetivo

Preparar a etapa de bancada para que uma referência obtida do NEO-M8N seja
validada antes de entrar nos ensaios baseline e secure. O validador trabalha
com o arquivo binário produzido pelo gravador serial e não depende da FPGA.

## Implementação

- `scripts/gps_fixture.py` passou a aceitar um fluxo bruto CRLF e verificar
  sentença completa, ASCII, checksum NMEA e limite de 82 caracteres.
- `scripts/gps_capture.py` gera um relatório privado com quantidade e tipos de
  sentença, bytes, line ending e SHA-256; não sobrescreve relatório existente.
- `make gps-capture-check GPS_CAPTURE=...` fornece a forma curta para a bancada.
- O relatório deixa explícito que a validação formal não prova a origem física
  dos bytes; essa origem deve ser registrada no caderno/relatório de bancada.

## Comandos executados

```bash
make gps-replay
make pc
python3 -m py_compile scripts/gps_fixture.py scripts/gps_capture.py tb/test_gps_fixture.py
```

## Resultado

- `make gps-replay`: **PASS** — 5 sentenças, 309 bytes CRLF.
- SHA-256 do replay público usado no teste:
  `a96557374ebe971dd88329d8d40452c06f33c624ba99cd6c5e9b972594aa4f89`.
- `make pc`: **PASS** — 19 testes em `1,017 s`.
- O teste da CLI confirmou geração de relatório com permissão `0600`.
- Casos de checksum alterado, captura truncada e conversão para LF foram
  rejeitados.

## Uso com o GPS real

Depois de capturar a referência, sem editar o arquivo:

```bash
python3 scripts/gps_capture.py \
  --input data/private/ensaio01/gps-reference.bin \
  --report data/private/ensaio01/gps-reference.json
```

Somente depois de um `PASS` devem ser registrados o hash, a quantidade de
sentenças e a montagem física. O teste atual usa o replay público/sintético;
portanto, **não representa aquisição do NEO-M8N**, não valida nível elétrico,
antena, alimentação ou perda de bytes na bancada.

## Próximo passo

Programar os tops integrados baseline e secure na DE10-Lite, capturar uma
referência do GPS e aplicar este validador antes da comparação byte a byte.
