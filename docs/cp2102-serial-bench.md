# Bancada serial com um CP2102

O único host serial externo é um módulo USB–TTL CP2102 configurado em nível
lógico de 3,3 V. Ele é conectado ao PC e
executa scripts/serial_bench.py, que transmite bytes, recebe a resposta da
FPGA e compara o resultado no próprio PC.

## Ligações elétricas

Para os testes baseline/secure com vetor conhecido, use uma conexão
full-duplex:

~~~text
CP2102 TXD  ─────────>  UART_RX da FPGA
CP2102 RXD  <─────────  UART_TX da FPGA
CP2102 GND  ──────────  GND da placa
~~~

Na DE10-Lite, UART_RX=V10 e UART_TX=W10 nos pinos de bancada já preparados.
Na Cyclone IV, use UART_RX=J3 PIN_103 e UART_TX=J3 PIN_100. O CP2102 não
alimenta nenhuma FPGA. Não conecte o pino de 5 V ao GPIO e não una fontes de
alimentação; confirme que TXD/RXD estão em 3,3 V antes de ligar.

O mesmo módulo serve para as duas placas, uma por vez. A porta Linux pode ser
/dev/ttyUSB0, /dev/ttyUSB1 ou outro nome atribuído pelo sistema; confirmar
com dmesg e ls -l /dev/ttyUSB*.

## Teste de vetor conhecido

1. Crie um contexto baseline com 20 bytes:

   ~~~bash
   mkdir -p data/private/ensaio-baseline
   python3 scripts/context.py new \
     --mode baseline --bytes 20 \
     --output data/private/ensaio-baseline/context.json
   ~~~

2. Compile e programe o SOF baseline da placa escolhida. Não pressione KEY0
   depois que a primeira captura começar.
3. Conecte TXD, RXD e GND, sem conectar 5 V/3,3 V do CP2102 à placa.
4. Execute o host:

   ~~~bash
   python3 scripts/serial_bench.py run \
     --port /dev/ttyUSB0 \
     --context data/private/ensaio-baseline/context.json \
     --received data/private/ensaio-baseline/received.bin \
     --report data/private/ensaio-baseline/report.json \
     --trials 4
   ~~~

   O vetor padrão é 55 A5 00 FF 3C, repetido quatro vezes. O programa
   imprime READY, envia cada quadro, lê exatamente cinco bytes e mantém uma
   guarda de 10 ms para detectar bytes extras.
5. O resultado esperado é status: PASS, 20 bytes recebidos e zero timeout,
   divergência ou byte extra. Guardar o relatório, o binário recebido, o SOF,
   a identificação da placa e a forma de onda correspondente.

Para o secure, gere um contexto novo com a mesma quantidade de bytes e registre
o nonce:

~~~bash
mkdir -p data/private/ensaio-secure
python3 scripts/context.py new \
  --mode aes-128-ctr --bytes 20 \
  --key-hex 000102030405060708090a0b0c0d0e0f \
  --registry data/private/nonce-registry.json \
  --output data/private/ensaio-secure/context.json
CONTEXT_FILE=data/private/ensaio-secure/context.json make secure-fpga
python3 scripts/serial_bench.py run \
  --port /dev/ttyUSB0 \
  --context data/private/ensaio-secure/context.json \
  --registry data/private/nonce-registry.json \
  --received data/private/ensaio-secure/received.bin \
  --report data/private/ensaio-secure/report.json \
  --trials 4
~~~

O secure deve retornar ciphertext diferente do vetor enviado, mas o relatório
precisa indicar PASS: a decifragem independente recupera exatamente os 20
bytes de referência. Um contexto secure é consumido antes de READY; depois de
uma tentativa, inclusive uma falha, criar outro contexto e programar o SOF
correspondente.

## Captura e replay do GPS

Com um único CP2102, a referência e o caminho FPGA são medidos em duas etapas
controladas:

1. Para capturar o GPS diretamente no PC, conecte GPS TX → CP2102 RXD e GND.
   Use scripts/capture.py record ou o comando abaixo. O RX do GPS não é
   necessário para mensagens periódicas NMEA.

   ~~~bash
   python3 scripts/capture.py record \
     --port /dev/ttyUSB0 --bytes 309 --timeout 10 \
     --output data/private/gps-reference.bin \
     --report data/private/gps-reference-capture.json
   python3 scripts/gps_capture.py \
     --input data/private/gps-reference.bin \
     --report data/private/gps-reference.json
   ~~~

2. Depois de validar a captura, desconecte o TX do GPS do CP2102 e conecte
   CP2102 TXD → FPGA UART_RX e FPGA UART_TX → CP2102 RXD. O comando replay
   transmite os mesmos bytes capturados e recebe a saída no mesmo adaptador:

   ~~~bash
   python3 scripts/serial_bench.py replay \
     --port /dev/ttyUSB0 \
     --input data/private/gps-reference.bin \
     --context data/private/ensaio-baseline/context.json \
     --received data/private/ensaio-baseline/gps-output.bin \
     --report data/private/ensaio-baseline/gps-output.json
   ~~~

   Para o secure, use um contexto novo com bytes igual ao tamanho da captura,
   compile o SOF secure com esse contexto e informe também --registry.

Esse procedimento usa dados realmente adquiridos do NEO-M8N e os reapresenta
em uma segunda execução, evitando comparar duas sequências GPS diferentes.
Com um único CP2102 não se capturam referência e saída simultaneamente; para
isso seriam necessários dois canais independentes ou o Analog Discovery 2
como canal adicional. A limitação deve ser registrada no artigo.

## O que o relatório mede

O relatório JSON registra modo, porta, bytes transmitidos/recebidos, timeout,
bytes faltantes/extras, divergência, hashes, contexto consumido e tempo
observado pelo host. Esse tempo inclui Linux, USB e CP2102; não é latência
isolada da FPGA. O CP2102 também não expõe as flags internas de framing e
overflow: elas continuam sendo verificadas pelos LEDs/diagnósticos da FPGA e
pela forma de onda do osciloscópio ou do Analog Discovery 2.

Os arquivos de contexto, registro de nonce, capturas GPS, respostas e relatórios
são privados, criados sem sobrescrever arquivos existentes e não devem ser
versionados.
