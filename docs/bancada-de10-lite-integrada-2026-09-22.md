# Roteiro integrado da DE10-Lite — 22/09/2026

Status: preparação concluída; P03–P06 na DE10-Lite ainda precisam ser
executados fisicamente. O uart_scope e o loopback isolado já passaram em
18/09. Este roteiro começa no sistema integrado UART RX → FIFO → UART TX e
repete o mesmo ensaio com AES-128-CTR.

## 1. Objetivo

1. P03 — baseline: quatro retornos exatos de 55 A5 00 FF 3C.
2. P04 — baseline no osciloscópio: níveis, bit time, quadro e RX→TX.
3. P05 — secure: quatro ciphertexts recuperados no PC sem divergência.
4. P06 — secure no osciloscópio: mesmo formato 9600/8N1 e RX→TX medido.

Quatro tentativas são usadas porque a quarta atravessa a fronteira de 16 bytes
da máscara CTR. Programar um SOF, acender LEDs ou observar pulsos não encerra
sozinho nenhum teste.

## 2. Arquivos preparados

~~~text
build/de10_lite/baseline/uart_baseline.sof
build/de10_lite/secure/uart_secure.sof
scripts/serial_bench.py
docs/cp2102-serial-bench.md
~~~

Antes da bancada, a partir da raiz do repositório:

~~~bash
make baseline-fpga
make secure-fpga
make metrics
sha256sum build/de10_lite/baseline/uart_baseline.sof build/de10_lite/secure/uart_secure.sof
~~~

Esses comandos compilam e auditam; não programam a placa.

## 3. Ligações com um único CP2102

Desligue a placa antes de alterar jumpers.

| Origem | Destino | Função |
| --- | --- | --- |
| CP2102 TXD | DE10-Lite JP1 pino físico 1 / FPGA V10 | entrada da FPGA |
| CP2102 RXD | DE10-Lite JP1 pino físico 2 / FPGA W10 | saída da FPGA |
| CP2102 GND | DE10-Lite JP1 pino físico 12 ou 30 | referência comum |

Use o adaptador em nível lógico de 3,3 V. Não conecte 5 V ou 3,3 V do módulo
à FPGA; cada placa usa sua própria alimentação. Não deixe jumper direto entre
JP1 pinos 1 e 2. Mantenha o GPS desconectado durante P03–P06. O CP2102 é
full-duplex e serve para transmitir o estímulo e receber a resposta.

Para medir com osciloscópio:

| Canal | Ponto | Papel |
| --- | --- | --- |
| CH1 | JP1 pino 1 / V10 | UART recebida pela FPGA |
| CH2 | JP1 pino 2 / W10 | UART transmitida pela FPGA |

Use pontas ×10, entrada de 1 MΩ, acoplamento DC e massas curtas. O Analog
Discovery 2 pode substituir o osciloscópio; salve o CSV bruto e a imagem.

## 4. Identificação e programação

Liste os cabos JTAG e confira a cadeia antes de programar:

~~~bash
export PATH=/home/leofernandesc/intelFPGA_lite/25.1/quartus/bin:$PATH
quartus_pgm -l
quartus_pgm -c 'NOME_EXATO_DO_CABO' -a
~~~

O cabo desta seção deve mostrar um MAX 10 10M50DA. Se mostrar EP4CE6, é a
Cyclone IV; não usar o SOF da DE10-Lite nesse cabo.

## 5. P03 — baseline

Programe o SOF baseline:

~~~bash
quartus_pgm -c 'NOME_EXATO_DO_CABO' -m jtag -o 'p;build/de10_lite/baseline/uart_baseline.sof'
~~~

Confirme heartbeat, configuração concluída, overflow e framing apagados, e TX
em repouso alto. Crie um contexto baseline com 20 bytes:

~~~bash
mkdir -p data/private/de10-2026-09-22
python3 scripts/context.py new --mode baseline --bytes 20 --output data/private/de10-2026-09-22/baseline-context.json
~~~

Execute o host PC, usando a porta real do adaptador:

~~~bash
python3 scripts/serial_bench.py run --port /dev/ttyUSB0 --context data/private/de10-2026-09-22/baseline-context.json --received data/private/de10-2026-09-22/baseline-received.bin --report data/private/de10-2026-09-22/baseline-report.json --trials 4
~~~

Critério P03: status PASS, 20 bytes recebidos, quatro respostas iguais a
55 A5 00 FF 3C e zero timeout, divergência ou bytes extras.

## 6. P04 — baseline no instrumento

Use trigger na borda de descida de CH1 e capture pelo menos 55 e A5:

| Medida | Valor nominal |
| --- | ---: |
| Nível baixo/alto | próximo de 0 V / 3,3 V |
| Tempo de um bit | aproximadamente 104,17 µs |
| Quadro 8N1 de um byte | aproximadamente 1,0417 ms |
| Cinco bytes sem pausas | aproximadamente 5,208 ms |
| Ordem do quadro | start baixo, 8 bits LSB-first, stop alto |

Com CH1 e CH2, medir do início do start bit de entrada ao início do start bit
correspondente na saída. Registrar o valor observado; o tempo do host no JSON
não é latência isolada da FPGA. Salvar a forma de onda com escalas visíveis.

## 7. P05 — secure e recuperação independente

Crie um contexto seguro novo para cada tentativa definitiva:

~~~bash
python3 scripts/context.py new --mode aes-128-ctr --bytes 20 --key-hex 000102030405060708090a0b0c0d0e0f --registry data/private/nonce-registry.json --output data/private/de10-2026-09-22/secure-context.json
CONTEXT_FILE=data/private/de10-2026-09-22/secure-context.json make secure-fpga
quartus_pgm -c 'NOME_EXATO_DO_CABO' -m jtag -o 'p;build/de10_lite/secure/uart_secure.sof'
python3 scripts/serial_bench.py run --port /dev/ttyUSB0 --context data/private/de10-2026-09-22/secure-context.json --registry data/private/nonce-registry.json --received data/private/de10-2026-09-22/secure-received.bin --report data/private/de10-2026-09-22/secure-report.json --trials 4
~~~

O ciphertext deve ser diferente do vetor enviado, mas o relatório deve indicar
PASS porque a decifragem independente recupera os 20 bytes de referência. Um
contexto secure é consumido antes de READY; depois de uma falha, não reutilizar
o contexto nem o SOF.

## 8. P06 — secure no instrumento

Mantenha os mesmos canais e escalas de P04. Registrar bit time, níveis, RX→TX,
ausência de quadro truncado e LEDs de overflow/framing apagados. A diferença
entre as latências de P04 e P06 é uma observação experimental da sobrecarga
do caminho AES-CTR; não usar timestamps do PC para estimar essa latência.

## 9. GPS com o mesmo adaptador

Para obter uma referência real, conectar GPS TX → CP2102 RXD e GND e capturar
o arquivo com scripts/capture.py record. Validar o arquivo com
scripts/gps_capture.py. Depois desconectar o TX do GPS, conectar CP2102 TXD →
FPGA RX e FPGA TX → CP2102 RXD, e executar scripts/serial_bench.py replay com
o mesmo arquivo. Assim baseline e secure processam exatamente os bytes que
foram adquiridos do NEO-M8N. Um único CP2102 não captura referência e saída
simultaneamente; essa é uma decisão do protocolo e deve ser registrada.

## 10. Registro a preencher

| Item | Baseline | Secure |
| --- | --- | --- |
| Data/hora | — | — |
| Commit | — | — |
| Cabo JTAG | — | — |
| SHA-256 do SOF | — | — |
| Programação Quartus | pendente | pendente |
| Quatro tentativas verificadas | pendente | pendente |
| Bit time | pendente | pendente |
| Níveis baixo/alto | pendente | pendente |
| RX→TX | pendente | pendente |
| Overflow/framing | pendente | pendente |
| Arquivos de evidência | — | — |

Somente depois de preencher esta tabela com logs e capturas reais P03–P06 os
ensaios podem ser alterados para concluídos no plano de testes.
