# Roteiro integrado da DE10-Lite — 22/09/2026

**Status:** preparação concluída; P03–P06 na DE10-Lite ainda precisam ser
executados fisicamente. O `uart_scope` e o loopback isolado já passaram em
18/09. Este roteiro começa no sistema integrado `UART RX → FIFO → UART TX` e
depois repete o mesmo ensaio com AES-128-CTR.

## 1. Objetivo e critérios

Hoje devem ser produzidas evidências separadas para:

1. **P03 — baseline:** quatro retornos exatos de `55 A5 00 FF 3C`;
2. **P04 — baseline no osciloscópio:** níveis, bit time, quadro e RX→TX;
3. **P05 — secure:** quatro ciphertexts recuperados no PC sem divergência;
4. **P06 — secure no osciloscópio:** mesmo formato 9600/8N1 e RX→TX medido.

Quatro tentativas são usadas porque as três primeiras atendem à repetição do
plano e a quarta atravessa a fronteira de 16 bytes da máscara CTR. Programar um
SOF, acender LEDs ou observar pulsos não encerra sozinho nenhum teste.

## 2. Arquivos preparados

```text
build/de10_lite/baseline/uart_baseline.sof
  SHA-256 f878f884b264c2f02a4d720c6ef3120f85ed88c3b52c3f87da7421c90437161c
build/de10_lite/secure/uart_secure.sof
  SHA-256 320357adffc3f530f7908fd0abcc2016d41d5cd123b3aa22dc25b4af9db0a91a
bench/esp32_uart_host_idf/
scripts/esp32_log_verify.py
```

Antes da bancada, a partir da raiz do repositório:

```bash
make baseline-fpga
make secure-fpga
make metrics
sha256sum build/de10_lite/baseline/uart_baseline.sof \
  build/de10_lite/secure/uart_secure.sof
```

Os hashes precisam coincidir com os valores acima antes da programação. Esses
comandos compilam e auditam; não programam a placa.

## 3. Ligações

Desligue as placas antes de alterar jumpers.

| Origem | Destino | Função |
| --- | --- | --- |
| ESP32 GPIO17 / TX2 | DE10-Lite JP1 pino físico 1 / FPGA `V10` | entrada da FPGA; conectar na janela de armamento |
| ESP32 GPIO16 / RX2 | DE10-Lite JP1 pino físico 2 / FPGA `W10` | saída da FPGA |
| ESP32 GND | DE10-Lite JP1 pino físico 12 ou 30 | referência comum |

Regras da montagem:

- não deixar jumper direto entre JP1 pinos 1 e 2;
- não unir `5V` nem `3V3` das placas; cada placa usa sua própria alimentação;
- manter o NEO-M8N desconectado durante P03–P06;
- confirmar a orientação do pino 1 no conector JP1 antes de energizar;
- o osciloscópio compartilha o mesmo GND da bancada.

Para medir com dois canais:

| Canal | Ponto | Papel |
| --- | --- | --- |
| CH1 | JP1 pino 1 / `V10` | UART recebida pela FPGA |
| CH2 | JP1 pino 2 / `W10` | UART transmitida pela FPGA |

Usar pontas ×10, entrada de 1 MΩ, acoplamento DC, massas curtas e, se
disponível, limite de banda de 20 MHz. Não usar o jacaré de massa em um pino de
sinal.

O osciloscópio de bancada pode ser substituído pelo Analog Discovery 2 para
P04/P06. Nesse caso, usar as entradas diferenciais `1+`/`1−` no RX e
`2+`/`2−` no TX, com os terminais negativos no GND comum, e salvar o CSV bruto
além da imagem. A instalação, enumeração, configuração e limites do AD2 estão
no [guia de WaveForms](analog-discovery-2-waveforms.md). O ESP32 continua
responsável pelo estímulo e pela verificação dos bytes.

## 4. Identificação JTAG segura

Como duas placas serão usadas no mesmo dia, não assumir que o número do
USB-Blaster permaneceu igual. Adicione o Quartus ao terminal e liste os cabos:

```bash
export PATH="/home/leofernandesc/intelFPGA_lite/25.1/quartus/bin:$PATH"
quartus_pgm -l
```

Para cada nome listado, confira a cadeia antes de programar:

```bash
quartus_pgm -c 'NOME_EXATO_DO_CABO' -a
```

O cabo escolhido para este roteiro deve mostrar um MAX 10 `10M50DA...`. Se
mostrar `EP4CE6...`, é a Cyclone IV: não use nela o SOF da DE10-Lite. Nos
comandos abaixo, substitua `NOME_EXATO_DO_CABO` sem remover as aspas.

## 5. Host ESP32 e gravação do log

Antes de gravar ou reiniciar o ESP32, deixe GPIO17/TX2 desconectado de V10. O
modo padrão do firmware é baseline. Compile e grave:

```bash
cd bench/esp32_uart_host_idf
source /home/leofernandesc/.espressif/v6.0.2/esp-idf/export.sh
idf.py set-target esp32
idf.py build
idf.py -p /dev/ttyUSB0 flash
cd ../..
```

Troque `/dev/ttyUSB0` pela porta real do ESP32. Crie o diretório privado para
os logs. Se repetir um ensaio, use um nome novo em vez de sobrescrever a
captura anterior:

```bash
mkdir -p data/private/de10-2026-09-22
```

Durante a programação do FPGA, mantenha pelo menos GPIO17/TX2 desconectado de
V10; GND e o caminho W10→GPIO16 podem permanecer ligados. Depois de programar
o SOF, abra o monitor e pressione `EN` uma vez. O firmware imprime
`ARM_DELAY_MS=10000` e aguarda 10 s antes do primeiro byte. Conecte
GPIO17→V10 nessa janela, sem pressionar KEY0. Capture o terminal com:

```bash
cd bench/esp32_uart_host_idf
script -q -f ../../data/private/de10-2026-09-22/baseline-monitor.log \
  -c 'idf.py -p /dev/ttyUSB0 monitor -b 115200'
```

Se o monitor já tiver reiniciado o ESP32 e mostrado a nova linha
`ESP-IDF UART host ready`, não pressione `EN` outra vez. Espere `ARMED`, quatro
linhas `RESULT` e encerre com `Ctrl+]`. O verificador considera somente a
sessão mais recente iniciada por essa linha. Não pressione KEY0 depois do
primeiro byte: o wrapper bloqueia a reutilização do contexto e exigirá nova
programação do SOF.

## 6. P03 — baseline

Com GPIO17 ainda desconectado de V10, programe:

```bash
quartus_pgm -c 'NOME_EXATO_DO_CABO' -m jtag \
  -o 'p;build/de10_lite/baseline/uart_baseline.sof'
```

Antes do primeiro byte, conferir:

- LEDR0 alternando como heartbeat;
- LEDR1 e LEDR5 acesos após a configuração;
- LEDR6 (overflow) e LEDR7 (framing) apagados;
- UART TX em repouso alto.

Inicie a captura, reinicie o ESP32 uma vez se necessário e conecte GPIO17→V10
durante a janela de 10 s. Cada registro deve conter:

```text
mode=baseline tx=55A500FF3C rx=55A500FF3C rx_len=5 same=1
timeout=0 extra=0 frame_err=0 parity_err=0 fifo_ovf=0
buffer_full=0 break=0 write_err=0 tx_timeout=0
```

Verifique automaticamente:

```bash
make esp32-log-check \
  ESP32_LOG=data/private/de10-2026-09-22/baseline-monitor.log \
  BENCH_MODE=baseline \
  REPORT=data/private/de10-2026-09-22/baseline-report.json
```

Critério P03: relatório `PASS`, quatro tentativas consecutivas, 20 bytes
recebidos e nenhuma flag de erro. Os LEDs 2 e 3 apenas alternam por evento e
podem voltar ao estado inicial após um número par de bytes.

## 7. P04 — baseline no osciloscópio ou Analog Discovery 2

Use trigger na borda de descida do CH1 e comece com `200 µs/div`. Capture pelo
menos `0x55` e `0xA5`, preservando imagem ou CSV com escalas visíveis.

| Medida | Valor nominal |
| --- | ---: |
| Nível baixo/alto | próximo de 0 V / 3,3 V |
| Tempo de um bit | aproximadamente `104,17 µs` |
| Quadro 8N1 de um byte | aproximadamente `1,0417 ms` |
| Cinco bytes sem pausas | aproximadamente `5,208 ms` |
| Ordem do quadro | start baixo, 8 bits LSB-first, stop alto |

Com CH1 e CH2, medir do início do start bit de entrada ao início do start bit
correspondente na saída. Registrar o valor observado sem usar
`host_window_us`: esse campo inclui o driver e o escalonamento do ESP32. Repetir
duas capturas com massa curta se ainda aparecerem picos fora dos trilhos antes
de considerar alteração de força/slew.

## 8. P05 — secure e recuperação independente

Desconecte GPIO17 de V10. No ESP32, selecione o modo secure e grave novamente:

```bash
cd bench/esp32_uart_host_idf
idf.py menuconfig
# FPGA UART bench host -> Secure: capture ciphertext
idf.py build
idf.py -p /dev/ttyUSB0 flash
cd ../..
```

Com GPIO17 ainda desconectado, programe o SOF secure:

```bash
quartus_pgm -c 'NOME_EXATO_DO_CABO' -m jtag \
  -o 'p;build/de10_lite/secure/uart_secure.sof'
```

Com o contexto público de bring-up, as quatro primeiras respostas esperadas
após uma programação nova são:

| Sequência | Ciphertext esperado |
| ---: | --- |
| 1 | `5B 72 25 65 E1` |
| 2 | `45 B4 E1 A6 EC` |
| 3 | `5B C4 B1 6D 68` |
| 4 | `45 61 2E FC 93` |

Esses valores correspondem a:

```text
key     = 000102030405060708090a0b0c0d0e0f
nonce   = 101112131415161718191a1b
counter = 00000001
```

Abra a captura secure, reinicie o ESP32 uma vez se necessário, reconecte
GPIO17→V10 durante a janela de armamento, aguarde quatro registros e encerre:

```bash
cd bench/esp32_uart_host_idf
script -q -f ../../data/private/de10-2026-09-22/secure-monitor.log \
  -c 'idf.py -p /dev/ttyUSB0 monitor -b 115200'
cd ../..

make esp32-log-check \
  ESP32_LOG=data/private/de10-2026-09-22/secure-monitor.log \
  BENCH_MODE=secure \
  REPORT=data/private/de10-2026-09-22/secure-report.json
```

Critério P05: relatório `PASS`, 20 bytes de ciphertext, recuperação exata das
quatro cópias do vetor e nenhuma flag de transporte. O contexto público serve
somente ao bring-up. Um ensaio definitivo com contexto próprio deve compilar o
SOF com `CONTEXT_FILE=...` e passar o mesmo JSON ao verificador.

## 9. P06 — secure no osciloscópio ou Analog Discovery 2

Mantenha exatamente os canais, pontas e escalas de P04. O conteúdo do CH2 muda,
mas os quadros continuam 9600/8N1. Registrar:

- bit time e níveis do CH2;
- RX→TX do primeiro byte;
- ausência de quadro truncado nos cinco bytes;
- LEDR6 e LEDR7 apagados durante todo o ensaio.

A diferença entre as latências físicas de P04 e P06 é a sobrecarga observada do
AES-CTR na DE10-Lite. Não derivar essa diferença de timestamps do ESP32.

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

Somente depois de preencher esta tabela com os logs e capturas reais P03–P06
podem ser alterados para concluídos no plano de testes.
