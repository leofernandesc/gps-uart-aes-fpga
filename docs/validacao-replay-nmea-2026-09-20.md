# Validação do replay NMEA — 20/09/2026

## Objetivo

Preparar, sem a placa e sem o NEO-M8N disponível, uma entrada de aplicação que
seja compatível com o formato serial esperado do GPS e possa ser reutilizada
pela simulação RTL e pelo verificador independente no PC.

## Fixture e contrato

O arquivo público
`reference/gps/neo-m8n-nmea-sample.txt` contém cinco sentenças ASCII:
RMC, GGA, GSA, GSV e TXT. Cada sentença tem checksum NMEA válido e fica em uma
linha LF no arquivo de referência. `scripts/gps_fixture.py` valida o checksum,
o limite de 82 caracteres e a codificação ASCII; na transmissão, cada linha é
convertida para `CRLF`, como esperado no fluxo serial do GPS.

O replay resultante tem:

| Item | Resultado |
| --- | ---: |
| Sentenças | 5 |
| Bytes transmitidos | 309 |
| Final de linha | `CRLF` |
| SHA-256 do replay | `a96557374ebe971dd88329d8d40452c06f33c624ba99cd6c5e9b972594aa4f89` |

Esse arquivo é um estímulo público/sintético. Ele não é uma captura do
NEO-M8N e não comprova a integração elétrica ou a recepção de GPS na placa.

## Execução

```bash
make gps-replay
make integration
make pc
```

Resultados observados:

- `make gps-replay`: cinco sentenças, 309 bytes, checksum e CRLF aprovados.
- Simulação acelerada: baseline e secure processaram 9 streams e 2.681 bytes
  cada, sem divergência.
- Simulação em 50 MHz/9600 baud: baseline e secure processaram 4 streams e 49
  bytes cada, sem divergência.
- Simulação dedicada `make integration-gps`: baseline e secure processaram o
  replay completo de 309 bytes em 50 MHz/9600, sem divergência ou overflow.
- No replay nominal, sem pausas artificiais de TX, a ocupação máxima da FIFO foi
  de 1 byte nos dois modos. A latência `rx_valid → tx_start` foi de 80 ns, a
  latência `rx_valid → tx_done` foi de 1.041.680 ns e a distância entre o início
  do quadro de entrada e o início do quadro de saída foi de 989.643 ns. Os
  valores foram medidos para os 309 bytes, com média, mínimo e máximo iguais.
- Verificação independente no PC: os bytes do baseline foram preservados e o
  ciphertext do secure foi recuperado byte a byte com AES-CTR.
- Suíte Python: 31 testes aprovados, incluindo o contrato do replay NMEA,
  captura/contexto e auditoria fail-closed de métricas.

## Limite e próximo uso

O caso de 309 bytes agora é o estímulo comum do fluxo de integração e foi
validado também no timing de produção em RTL. Quando o GPS estiver disponível,
a mesma referência deve ser substituída por uma captura real registrada no PC;
o teste físico deverá comparar a captura de entrada com a saída recuperada e
registrar perdas, framing, overflow e duração. A validação atual não altera a
situação pendente dos ensaios P07–P11.

O testbench foi corrigido em 20/09 para separar o replay nominal do estímulo
com pausas. Os valores nominais acima são de simulação RTL em clock de produção;
continuam não sendo uma medição elétrica do GPS ou da placa.
