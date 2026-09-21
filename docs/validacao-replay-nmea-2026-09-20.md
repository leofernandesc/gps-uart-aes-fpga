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
- Nos dois modos, a ocupação máxima da FIFO foi de 2 bytes. No estímulo
  registrado, que continha pausas artificiais de TX, a distância entre o
  primeiro byte RX e o primeiro quadro TX foi de 169.269 ciclos (3,385 ms); até
  o último quadro TX foram 16.236.274 ciclos (324,725 ms). Esses números são
  históricos e não devem ser usados como latência nominal.
- Verificação independente no PC: os bytes do baseline foram preservados e o
  ciphertext do secure foi recuperado byte a byte com AES-CTR.
- Suíte Python: 16 testes aprovados, incluindo o contrato do replay NMEA.

## Limite e próximo uso

O caso de 309 bytes agora é o estímulo comum do fluxo de integração e foi
validado também no timing de produção em RTL. Quando o GPS estiver disponível,
a mesma referência deve ser substituída por uma captura real registrada no PC;
o teste físico deverá comparar a captura de entrada com a saída recuperada e
registrar perdas, framing, overflow e duração. A validação atual não altera a
situação pendente dos ensaios P07–P11.

O testbench foi corrigido em 20/09 para separar o replay nominal do estímulo
com pausas. A nova medição deve ser executada em Linux com simulador HDL antes
de substituir os valores históricos no artigo.
