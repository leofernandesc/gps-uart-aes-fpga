# Roteiro integrado da DE10-Lite — 22/09/2026

Arquivo histórico de ensaios e procedimentos. As medições registradas abaixo
foram feitas a 9600 baud; a configuração vigente desde 29/09 é 38400/8N1 com
NEO-M8N. Repetir os testes dependentes da UART antes de usar seus valores
como resultados atuais.

Status: P03 baseline aprovado na DE10-Lite em 26/09/2026; P04–P06 continuam
pendentes. O uart_scope e o loopback isolado também já passaram. Este roteiro
começa no sistema integrado UART RX → FIFO → UART TX e repete o mesmo ensaio
com AES-128-CTR.

## 1. Objetivo

1. P03 — baseline: quatro retornos exatos de 55 A5 00 FF 3C.
2. P04 — baseline no osciloscópio: níveis, bit time, quadro e RX→TX.
3. P05 — secure: quatro ciphertexts recuperados no PC sem divergência.
4. P06 — secure no osciloscópio: formato atual 38400/8N1 e RX→TX medido.

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

### Resultado físico P03 — DE10-Lite — 26/09/2026

O `uart_baseline.sof` foi programado pelo USB-Blaster `[1-3]`; o Quartus
confirmou configuração bem-sucedida no `10M50DAF484@1`, sem erros ou avisos.
O JTAG ID foi `0x031050DD` e o checksum reportado pelo Programmer foi
`0x002A0029`.
O bitstream tem SHA-256
`f878f884b264c2f02a4d720c6ef3120f85ed88c3b52c3f87da7421c90437161c`, foi
gerado no build registrado pelo manifest como commit `746b085` e usa
50 MHz/9600 baud/8N1. O host reconheceu o CP2102 em `/dev/ttyUSB0`.

O ensaio retornou **PASS**: quatro transações de `55 A5 00 FF 3C`, 20 bytes
enviados e 20 recebidos, sem divergência, perda, byte extra ou timeout. O hash
SHA-256 dos dados de referência e recebidos coincide:
`1ec8f144575a9c265334dfa2c385532741170ab730f39f5e38a9fae7f8517e5d`.
Após o ensaio, a observação visual foi: LEDR0 piscando; LEDR1 e LEDR5 acesos;
LEDR2–4 e LEDR6–9 apagados. Isso confirma heartbeat/configuração concluída,
ausência de overflow e framing e FIFO vazia ao fim do ensaio.
O tempo total informado pelo host foi 272,649 ms. Os tempos por transação
foram 16,939; 16,749; 16,759; e 16,745 ms. Essas medidas incluem o PC, driver
USB e adaptador serial e **não** representam latência isolada da FPGA.
Não foram feitas medições elétricas neste passo; bit time, níveis e RX→TX ficam
para P04. O relatório e o binário recebidos foram preservados localmente em
`data/private/de10-2026-09-26/`; o SHA-256 do relatório JSON é
`d046b73ee1875e4c5b748d289a60d43b1c707d5bde186bf74dd3a8ef0ae6401f`.

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

### Tentativa de estímulo P04 — 26/09/2026, 01:18 (Manaus)

O CP2102 foi aberto em `/dev/ttyUSB0` e o host enviou o primeiro burst
`55 A5 00 FF 3C` em 9600/8N1. Não houve resposta recebida em 1,000 s
(`received_bytes=0`, cinco bytes ausentes, timeout). O script interrompeu a
sequência após essa falha; os outros três bursts não foram enviados. Não foi
salva captura CSV/imagem do AD2, portanto não há dado de forma de onda para
analisar e P04 permanece pendente/inconclusivo. A causa do timeout ainda não
está determinada; o P03 anterior continua aprovado. O relatório local está em
`data/private/de10-2026-09-26/p04-baseline-report.json` (SHA-256
`dfe2157e6be9eb33241b141f807eb15466d13dfc7308cd02016ec17d1c48b315`); o arquivo
recebido está vazio (SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`).

No diagnóstico seguinte, foram relatados LEDR0 piscando e apenas LEDR9 aceso,
com LEDR2/3/6/7 apagados. No wrapper integrado, LEDR9 indica FIFO com pico de
512 bytes, contexto esgotado ou contexto bloqueado. No baseline, esgotamento
AES não se aplica e cinco bytes não deveriam atingir o limiar da FIFO; o
bloqueio do contexto era uma hipótese, não uma causa confirmada. Às 01:28 de
26/09, `uart_baseline.sof` foi reprogramado por JTAG com sucesso no
`10M50DAF484@1` (checksum `0x002A0029`, sem erros/avisos), reinicializando o
estado volátil. Em seguida, foram observados LEDR1 e LEDR5 acesos e LEDR0
piscando, indicando atividade/configuração após a regravação. Ainda não houve
novo envio de bytes; a captura P04 será retomada após armar o AD2.

### Retentativa P04 — 26/09/2026, 01:35 (Manaus)

Com o AD2 armado em captura única, a primeira chamada do ensaio foi barrada
antes de abrir a porta serial porque o contexto existente era de 20 bytes e a
tentativa solicitava 5; portanto, nenhum byte saiu nessa chamada. Foi criado
um contexto baseline de 5 bytes (`context_id=45e10d45e540464cbe3bc94a0ab7ca8b`)
e executado um único burst em `/dev/ttyUSB0`, 9600/8N1. O CP2102 transmitiu
`55 A5 00 FF 3C` e recebeu exatamente `55 A5 00 FF 3C`: **5/5**, zero bytes
ausentes/extras e sem timeout. O tempo da transação observado pelo host foi
16,929 ms (não é latência isolada da FPGA); o tempo total do processo foi
71,824 ms. Os hashes SHA-256 da referência e da recepção coincidem:
`086a1a8a2575a3f80eb8a942552cfaf94825e511f1ec0df2448b4bfc97b68b01`.
Relatório e bytes recebidos estão em
`data/private/de10-2026-09-26/p04-baseline-single-report.json` e
`p04-baseline-single-received.bin`. Essa transação retornou 5/5 uma vez; uma
retentativa posterior falhou, então a resposta ainda não é reproduzível. P04
segue pendente até diagnosticar a falha e salvar/analisar a captura AD2 para
bit time, níveis elétricos e atraso RX→TX.
O usuário informou que nenhuma forma de onda apareceu no WaveForms após o
burst, apesar da tentativa em captura única. Nenhum CSV ou workspace P04 foi
salvo; a medição instrumental continua pendente e o resultado 5/5 permanece
limitado à transferência observada pelo CP2102.

### Segunda retentativa P04 — 26/09/2026, 01:53 (Manaus)

Por solicitação do usuário, foi enviado novamente um único burst
`55 A5 00 FF 3C` pelo CP2102 em `/dev/ttyUSB0`, 9600/8N1. O host transmitiu os
cinco bytes, mas recebeu zero em 1,002 s: **0/5**, cinco ausentes, zero extras,
timeout. O processo durou 1,058 s no host; isso não mede latência da FPGA.
Relatório: `data/private/de10-2026-09-26/p04-baseline-retry2-report.json`
(SHA-256 `12ee622b440483c3d6b3e7dabc7134f8765b19e689f4fc2eaac2429bab5bc34d`);
recepção vazia: `p04-baseline-retry2-received.bin` (SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`). A causa
permanece indeterminada. Próximo diagnóstico: registrar LEDR1/2/3/5/6/7/9 e
confirmar se houve reset/KEY0 desde a transação anterior; não repetir ainda.

O usuário informou depois que somente LEDR9 permanecia aceso. Esse padrão é
compatível com `context_locked` (LEDR1/5 apagados, sem indicação persistente de
overflow/framing), mas não prova qual evento desativou a ponte. Às 01:58 de
26/09, o mesmo `uart_baseline.sof` foi reprogramado por JTAG no
`10M50DAF484@1`, com sucesso e sem erros/avisos (checksum `0x002A0029`). Nenhum
byte foi enviado após essa regravação. O usuário confirmou que os LEDs de
atividade/configuração voltaram a acender; o estado atual do LEDR9 ainda não
foi informado. Essa recuperação é compatível com bloqueio volátil do contexto,
mas o evento que o acionou não foi identificado.

### Tentativa de transmissão repetida — 26/09/2026, 02:11 (Manaus)

Foi solicitado transmitir dez bursts `55 A5 00 FF 3C`, com intervalo de
250 ms. O ensaio transmitiu somente o primeiro burst e abortou quando não
recebeu retorno em 1,001 s: 0/5 recebidos, cinco ausentes, zero extras. Assim,
não houve repetição contínua. Relatório:
`data/private/de10-2026-09-26/p04-baseline-repeat10-report.json` (SHA-256
`87376aa02fc00e4a38bd126f3d4045ade0a4c412c1a2786e91d764214af218b6`). Não
houve dado novo de forma de onda; estado dos LEDs e eventual acionamento de
KEY0 após a última regravação foram solicitados para diagnóstico.

### Estímulo repetitivo para diagnóstico do AD2 — 26/09/2026, 02:18 (Manaus)

Com os dois canais aparentando níveis constantes, foi enviado o padrão
`55 A5 00 FF 3C` repetidamente por `/dev/ttyUSB0` durante 10,103 s, a 9600/8N1,
com pausa de 50 ms entre bursts. Foram transmitidos 200 bursts (1.000 bytes).
Este foi um estímulo visual, não uma validação de eco: a recepção não foi
avaliada e o buffer de entrada do host foi descartado ao final. Não foi salva
captura CSV/workspace nem confirmado ainda se apareceram transições no AD2.

### Segundo estímulo repetitivo — 26/09/2026, aproximadamente 02:30 (Manaus)

Foi repetido o estímulo visual: padrão `55 A5 00 FF 3C`, 200 bursts (1.000
bytes) em 10,100 s, 9600/8N1, com intervalo de 50 ms. Como antes, os bytes
recebidos não foram avaliados nem preservados. O usuário ainda não confirmou o
que apareceu nos canais; não há captura instrumental associada.

### Tentativa de eco após regravação — 26/09/2026, 02:32 (Manaus)

Para iniciar o ensaio em estado conhecido após os estímulos anteriores, o
baseline foi reprogramado. A guarda do wrapper impede rearmar a configuração
por KEY0 depois do primeiro byte recebido; a ponte não se desativa
automaticamente ao fim de cada burst. JTAG configurou o dispositivo
`10M50DAF484@1` sem erros/avisos, checksum `0x002A0029`; SOF SHA-256
`f878f884b264c2f02a4d720c6ef3120f85ed88c3b52c3f87da7421c90437161c`.
Em seguida, o CP2102 transmitiu um burst `55 A5 00 FF 3C` a 9600/8N1. O host
recebeu **0/5 bytes** em 1,501 s (timeout, sem bytes extras), portanto o eco
falhou nesta tentativa. Relatório local:
`data/private/de10-2026-09-26/p04-echo-report.json` (SHA-256
`3415efa60c674dd1aa77256774af18021c0afc4c5ce511c4322d6878ffac43a7`); arquivo
recebido vazio: `p04-echo-received.bin` (SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`). Isso
não identifica sozinho se a falha está na recepção da FPGA, no caminho TX, na
ligação CP2102 ou no cabeamento. Aguardar estado dos LEDs antes/depois e
captura de RX/TX no AD2; P04 segue pendente.

### Diagnóstico com continuidade de pinos e AD2 — 26/09/2026, 02:41–02:54

O gerador `uart_scope` foi lido pelo CP2102 (15 bytes `0x55` em 1,5 s),
confirmando a saída W10 até o PC. A ponte histórica sem guarda de contexto
retornou 0/5. Um SOF independente, que copia diretamente V10 para W10,
também retornou 0/5 e depois 0/500 bytes em envios repetidos. Durante esse
último envio, o AD2 amostrou o pino TXD do CP2102 e W10 a 250 kS/s por 6 s:
as 1.500.000 amostras de cada canal permaneceram acima de 3,26 V. CH1 já
estava no TXD, não diretamente no metal de V10. Na captura com o
gerador interno, W10 apresentou os quadros `0x55`, enquanto TXD permaneceu
alto. Reinicializar apenas o USB do CP2102 não restaurou o eco. O
[registro detalhado](diagnostico-p04-de10-2026-09-26.md) contém horários,
hashes, limites das medições e o próximo ensaio com DIO0 do AD2 como fonte UART.
Não há base para alterar o RTL baseline/secure; P04 continua pendente.

### Retomada da montagem P04 — 29/09/2026, 07:40 (Manaus)

O usuário refez a ligação conforme o mapa desta seção: CP2102 TXD→V10,
W10→CP2102 RXD, GND comum; CH1 em V10, CH2 em W10, ambos referenciados ao
GND. GPS e fonte DIO0 do AD2 ficaram desconectados. O baseline foi
reprogramado pelo USB-Blaster `[1-3]`; Quartus confirmou `10M50DAF484@1`, JTAG
ID `0x031050DD`, checksum `0x002A0029`, sem erros ou avisos.

O AD2 aparece no `dwfcmd enum` como `SN:210321A7FDB4`, livre. O CP2102 está
conectado e identificado no kernel como `10c4:ea60` pelo driver `cp210x`, e
`ttyUSB0` consta no sysfs; o nó `/dev/ttyUSB0`, contudo, não está exposto à
sessão isolada usada pelo teste (`pyserial` informa `no ports found`). Nenhum
estímulo foi enviado nesta retomada e P04 segue pendente. A abertura de
WaveForms pela sessão de ferramentas falhou por indisponibilidade do display;
o aplicativo e o script serial precisam ser usados na sessão gráfica do Ubuntu.

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
| Data/hora | 26/09/2026 00:22 (Manaus) | — |
| Commit do build | `746b085` | — |
| Cabo JTAG | USB-Blaster `[1-3]`; MAX 10 `10M50DAF484@1` | — |
| SHA-256 do SOF | `f878f884…37161c` | — |
| Programação Quartus | PASS, sem erros/avisos | pendente |
| Quatro tentativas verificadas | PASS, 20/20 bytes, sem timeout/extras/divergência | pendente |
| Bit time | pendente | pendente |
| Níveis baixo/alto | pendente | pendente |
| RX→TX | Retorno serial byte a byte PASS; atraso elétrico não medido | pendente |
| Overflow/framing | LEDR6/LEDR7 apagados; FIFO vazia ao final | pendente |
| Arquivos de evidência | Relatório/binário em `data/private/de10-2026-09-26/` | — |

P03 está concluído pelo critério de transferência e comparação serial. P04–P06
continuam abertos até seus próprios ensaios e registros físicos.
