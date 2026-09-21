# Validação física — ESP32 e Cyclone IV — 21/09/2026

Este registro documenta o primeiro ensaio do caminho serial entre a placa
Cyclone IV e um ESP32 usado como fonte e capturador UART. O objetivo foi
substituir temporariamente um adaptador USB–UART externo e verificar o top
`baseline` antes dos ensaios com AES e GPS.

O ensaio do caminho externo do baseline foi aceito: o vetor foi transmitido pelo
ESP32 e retornou pelos pinos TX/RX da FPGA sem alteração. O teste de forma de
onda no osciloscópio e o teste secure continuam sendo etapas separadas.

## 1. Configuração registrada

### Placa Cyclone IV

| Item | Dado observado ou utilizado |
| --- | --- |
| Placa | ZRTECH/WXEDA V2.00 |
| Dispositivo informado na placa | `EP4CE6E22C8N` |
| Dispositivo reconhecido pelo Quartus Programmer | `EP4CE6E22@1` |
| Família do projeto Quartus | Cyclone IV E |
| Clock usado no projeto | 48 MHz, `PIN_24` |
| Reset usado no projeto | `PIN_89`, ativo baixo |
| UART RX da variante de bancada | J3 `PIN_103` |
| UART TX da variante de bancada | J3 `PIN_100` |
| UART | 9600 baud, 8N1 |
| Referência lógica | GND comum; sinais de 3,3 V |
| SOF programado | `build/cyclone4/baseline/uart_baseline.sof` |

O mapeamento `PIN_103`/`PIN_100` é o mapeamento efetivamente usado nos projetos
`baseline` e `secure` para a bancada. Ele é diferente dos pinos UART
`PIN_87`/`PIN_86` encontrados na referência pública da placa, que não estavam
acessíveis no header utilizado.

### ESP32 e computador

| Item | Dado observado ou utilizado |
| --- | --- |
| Microcontrolador | ESP32 clássico, `ESP32-D0WD-V3`, revisão 3.1 |
| Frequência informada pelo chip | 240 MHz |
| Interface USB da placa ESP32 | Silicon Labs CP2102 |
| Dispositivo Linux usado | `/dev/ttyUSB1` |
| Outro conversor detectado, não usado | `/dev/ttyUSB0`, Prolific PL2303 |
| Framework | ESP-IDF `v6.0.2` |
| Canal testado | UART2 |
| GPIO17 / TX2 | FPGA J3 `PIN_103` / UART_RX |
| GPIO16 / RX2 | FPGA J3 `PIN_100` / UART_TX |
| Console USB do ESP32 | 115200 baud |
| Canal FPGA–ESP32 | 9600 baud, 8N1 |

O MAC do ESP32 foi lido durante a identificação do chip, mas não é necessário
para reproduzir o experimento nem para o artigo e, por isso, não foi incluído
neste documento versionado.

### Ligações físicas

| Origem | Destino | Estado do ensaio |
| --- | --- | --- |
| ESP32 GPIO17 / TX2 | Cyclone IV J3 `PIN_103` | conectado |
| Cyclone IV J3 `PIN_100` / TX | ESP32 GPIO16 / RX2 | conectado |
| GND do ESP32 | GND da Cyclone IV | conectado antes da leitura considerada válida |
| 5 V ou 3,3 V entre as placas | — | não conectado; placas alimentadas separadamente |
| Jumper local `PIN_100` ↔ `PIN_103` | — | não instalado; ausência confirmada pelo operador |

O GND comum é obrigatório. A leitura feita antes de o GND ser conectado foi
classificada como observação inválida para aceitação elétrica; as leituras
posteriores foram feitas com o GND conectado.

## 2. Firmware do ESP32

O firmware versionado em
[`bench/esp32_uart_host_idf`](../bench/esp32_uart_host_idf/) configura a UART2
em 9600/8N1, transmite periodicamente o vetor de cinco bytes abaixo e imprime
no monitor USB os bytes recebidos:

```text
55 A5 00 FF 3C
```

Parâmetros relevantes do firmware:

```text
UART testada: UART2
baud: 9600
formato: 8N1
TX: GPIO17
RX: GPIO16
período entre envios: 1000 ms
timeout de TX/RX: 250 ms
buffer RX/TX do ESP32: 256 bytes
```

O top `baseline` deve devolver o mesmo vetor. O top `secure` deve devolver um
ciphertext, que será conferido posteriormente com o contexto AES-CTR da
captura; a aparência hexadecimal no monitor não é um critério de decifragem.

## 3. Sequência de execução

### 3.1 Compilação do host

Foi executado:

```bash
source /home/leofernandesc/.espressif/v6.0.2/esp-idf/export.sh
cd bench/esp32_uart_host_idf
idf.py set-target esp32
idf.py build
```

Resultado: compilação concluída com sucesso usando ESP-IDF `v6.0.2`. O binário
da aplicação foi reportado com tamanho `0x28820`, deixando aproximadamente
84% de espaço livre no particionamento usado pelo projeto.

### 3.2 Identificação e gravação do ESP32

O comando específico `idf.py chip-id` não está disponível como alvo do `idf.py`
nessa versão do ESP-IDF. A identificação foi feita pelo esptool:

```bash
python -m esptool --chip esp32 -p /dev/ttyUSB1 chip-id
```

O chip respondeu como `ESP32-D0WD-V3`, revisão `3.1`, com Wi-Fi, Bluetooth,
dois núcleos e frequência de 240 MHz. A primeira tentativa de inicialização do
stub do esptool não permaneceu estável; a gravação foi repetida em modo
`--no-stub`, a 115200 baud, e foi concluída com verificação SHA:

```bash
python -m esptool --chip esp32 --port /dev/ttyUSB1 --baud 115200 --no-stub \
  write-flash --flash-mode dio --flash-size 2MB --flash-freq 40m \
  0x1000 build/bootloader/bootloader.bin \
  0x8000 build/partition_table/partition-table.bin \
  0x10000 build/esp32_uart_host.bin
```

O chip de flash foi detectado fisicamente como 4 MB, enquanto a imagem gravada
usa cabeçalho/particionamento de 2 MB. A gravação foi aceita e verificada; essa
diferença fica registrada para eventual revisão do particionamento, mas não
impediu o ensaio UART.

### 3.3 Programação do baseline na Cyclone IV

O SOF foi gravado pelo USB-Blaster encontrado como `USB-Blaster [1-3]`:

```bash
/home/leofernandesc/intelFPGA_lite/25.1/quartus/bin/quartus_pgm \
  -c 'USB-Blaster [1-3]' -m jtag \
  -o 'p;build/cyclone4/baseline/uart_baseline.sof'
```

Dados retornados pelo Programmer:

```text
dispositivo: EP4CE6E22@1
JTAG ID: 0x020F10DD
checksum do SOF: 0x000BC41F
configuração: succeeded — 1 device(s) configured
erros: 0
avisos: 0
```

### 3.4 Abertura do monitor

Foi usado o console USB da placa ESP32, separado da UART2 sob teste:

```bash
source /home/leofernandesc/.espressif/v6.0.2/esp-idf/export.sh
idf.py -p /dev/ttyUSB1 monitor -b 115200
```

Uma primeira abertura encontrou a porta ocupada por uma instância anterior do
monitor. Somente os processos antigos que mantinham `/dev/ttyUSB1` aberto foram
encerrados; o monitor foi reaberto e permaneceu ativo durante a observação.

## 4. Leituras observadas

Após a conexão do GND comum, o monitor exibiu a inicialização e o primeiro
retorno:

```text
I (271) esp32_uart_host: ESP-IDF UART host ready
I (271) esp32_uart_host: FPGA channel: 9600 8N1; TX GPIO17; RX GPIO16
I (281) esp32_uart_host: TX: 55 A5 00 FF 3C
I (551) esp32_uart_host: RX: 55 A5 00 FF 3C
I (551) esp32_uart_host: RX bytes: 5
```

Uma amostra posterior, já com o ensaio repetido por mais de dois minutos, foi:

```text
I (121251) esp32_uart_host: TX: 55 A5 00 FF 3C
I (121511) esp32_uart_host: RX: 55 A5 00 FF 3C
I (121511) esp32_uart_host: RX bytes: 5

I (122511) esp32_uart_host: TX: 55 A5 00 FF 3C
I (122771) esp32_uart_host: RX: 55 A5 00 FF 3C
I (122771) esp32_uart_host: RX bytes: 5

I (243471) esp32_uart_host: TX: 55 A5 00 FF 3C
```

Na saída contínua observada entre aproximadamente `I (271)` e pelo menos
`I (243471)`, cada retorno visível continha exatamente cinco bytes e o vetor
era idêntico ao transmitido. Não foram observadas mensagens de erro de escrita,
timeout de transmissão, framing error ou divergência de bytes nesse trecho.

### Interpretação do intervalo TX–RX

O intervalo entre o registro `TX` e o registro `RX` foi aproximadamente
260–270 ms nas amostras visíveis. Esse número **não é a latência física da
UART**. O firmware imprime `TX` antes de chamar `uart_write_bytes()` e depois
faz uma leitura bloqueante com `FPGA_UART_TIMEOUT_MS = 250`; portanto, o tempo
inclui a política de espera e o agendamento do firmware.

Para medir latência end-to-end no artigo, será necessário uma captura dedicada
com timestamps ou uma versão do host que leia exatamente os cinco bytes
esperados e registre o instante de transmissão e de recepção com uma referência
adequada. O resultado atual é usado somente como verificação de integridade do
vetor e de estabilidade do caminho serial.

### Adaptador USB–UART versus ESP32

Um adaptador USB–UART não elimina o tempo físico da transmissão. Em 9600 baud,
um byte em 8N1 ocupa dez bits, portanto os cinco bytes do vetor ocupam
aproximadamente `5 × 10 / 9600 = 5,21 ms` em um sentido. O adaptador pode,
contudo, deixar a captura mais direta: o PC pode abrir a porta serial e mostrar
os bytes assim que chegarem, sem o `uart_read_bytes()` do firmware do ESP32
esperar até 250 ms por um buffer maior que o vetor.

O ESP32 disponível já possui um CP2102 e cumpre a mesma função de interface
USB–UART. Para eliminar a espera artificial no host atual, a próxima versão de
instrumentação deve ler exatamente os cinco bytes esperados, usar um timeout
menor e registrar timestamps próprios. Comprar um adaptador só é necessário se
for desejável uma segunda captura independente ou uma bancada sem o ESP32.

### O que significou o jumper no teste anterior

No ensaio local anterior, um jumper ligou diretamente:

```text
Cyclone IV TX — J3 PIN_100 ─────┐
                                ├── Cyclone IV RX — J3 PIN_103
```

Isso foi útil para verificar a UART e os pinos da própria FPGA, mas não seria
adequado no ensaio com o ESP32: o TX da FPGA ficaria ligado ao próprio RX e
ainda poderia haver dois transmissores dirigindo o mesmo nó. Isso poderia
produzir eco local, leituras ambíguas e contenção elétrica. No ensaio registrado
neste documento, esse jumper não estava instalado.

Para o teste independente, devem permanecer apenas:

```text
ESP32 GPIO17/TX2 ─────> Cyclone IV J3 PIN_103/RX
Cyclone IV J3 PIN_100/TX ─────> ESP32 GPIO16/RX2
ESP32 GND ──────────────── Cyclone IV GND
```

## 5. Resultado e classificação

| Item | Resultado de 21/09/2026 | Classificação |
| --- | --- | --- |
| ESP32 identificado | D0WD-V3, rev. 3.1 | confirmado |
| Firmware compilado | ESP-IDF 6.0.2, build concluído | confirmado |
| Firmware gravado | três imagens gravadas e verificadas | confirmado |
| GND comum | conectado após a observação inicial sem GND | condição posterior válida |
| FPGA programada | baseline, JTAG sem erro | confirmado |
| Vetor transmitido | `55 A5 00 FF 3C` | confirmado no monitor |
| Vetor recebido | `55 A5 00 FF 3C`, cinco bytes | observado repetidamente |
| Estabilidade | retornos repetidos sem divergência visível | observado |
| Caminho externo independente | jumper ausente; GPIO17→`PIN_103` e `PIN_100`→GPIO16 | aprovado para o baseline |
| P03 — baseline com ESP32 | vetor externo retornado com cinco bytes | aprovado |
| P04 — forma de onda no osciloscópio | ainda não medido nesta configuração | pendente |
| Secure físico | não executado neste registro | pendente |
| GPS físico | não executado neste registro | pendente |

O ensaio demonstra que o host ESP32 está pronto e que o baseline recebeu e
retransmitiu o vetor por um caminho externo independente. O intervalo de
260–270 ms do monitor continua sem valor de latência física; a medição de
desempenho será feita separadamente.

## 6. Observação preliminar no osciloscópio

Durante a primeira tentativa do P04, com o ESP32 e a FPGA conectados, foram
relatados os seguintes valores no sinal TX da FPGA:

| Observação | Valor relatado | Interpretação inicial |
| --- | ---: | --- |
| Distância entre picos na visualização afastada | aproximadamente `30 µs` | ainda não representa o bit time validado |
| Distância entre pico negativo e pico positivo na visualização aproximada | `680 ns` | provável transitório/ringing da borda |
| Forma geral | pico negativo, nível baixo, pico positivo e estabilização | compatível com bordas de um sinal digital medido com sonda/cabo de massa longo |

Para 9600 baud com o clock de 48 MHz, o bit time esperado continua sendo
aproximadamente `104,17 µs`. Os `680 ns` devem ser tratados como duração de
um transitório elétrico, não como duração de um bit. O bit time deve ser medido
entre bordas lógicas equivalentes ou entre os centros dos níveis estáveis,
ignorando os picos de overshoot/undershoot.

Essa observação não fecha o P04. A medição deve ser repetida com a ponta em
×10, acoplamento DC e o menor caminho possível de massa, preferencialmente uma
mola de terra ou um fio curto ligado ao GND mais próximo. Se o osciloscópio
possuir limitador de banda, pode-se habilitar inicialmente 20 MHz para separar
o quadro UART do ringing de alta frequência. Se o intervalo entre transições
lógicas estáveis continuar próximo de `30 µs` depois desse ajuste, o ensaio
deve ser interrompido para revisar pinagem e divisor de baud.

## 7. Próxima execução física

1. Manter o GND comum conectado.
2. Conferir exclusivamente as três ligações: GPIO17→`PIN_103`,
   `PIN_100`→GPIO16 e GND→GND.
3. Executar P04 no osciloscópio, medindo os quadros de entrada e saída do
   baseline.
4. Programar o secure com um contexto AES-CTR privado novo, capturar o
   ciphertext e compará-lo no PC antes de iniciar o teste GPS.

O ESP32 está sendo usado apenas como instrumento de bancada: o PC conversa com
ele pelo USB/CP2102 a 115200 baud, enquanto a UART2 entre ESP32 e FPGA permanece
em 9600/8N1. Não conectar os trilhos de 5 V ou 3,3 V das duas placas.
