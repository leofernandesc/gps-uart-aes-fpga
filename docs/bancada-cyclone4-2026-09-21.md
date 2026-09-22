# Bancada Cyclone IV — roteiro de identificação e testes

## Identificação atual

| Item | Registro atual | Confirmação restante |
| --- | --- | --- |
| Placa | ZRTECH V2.00 / DESIGNED BY WXEDA | Identificada na bancada |
| FPGA | EP4CE6E22C8N | Confirmado pela marcação do encapsulamento |
| SDRAM | Winbond W9864G6KH-6, 64 Mbit | Não é usada neste experimento |
| Clock | 48 MHz, PIN_24 | Confirmado pelo bit time físico de 104 µs |
| Reset | PIN_89, ativo baixo | Usado nos tops integrados |
| UART RX da referência pública | PIN_87 | Não acessível no header usado; bancada usa PIN_103 |
| UART TX da referência pública | PIN_86 | Não acessível no header usado; bancada usa PIN_100 |
| LEDs | PIN_1, PIN_2, PIN_3, PIN_144 | Ativos em zero; funções integradas abaixo |

As pinagens candidatas vêm de referências públicas que correspondem ao perfil
ZRTech/WXEDA, não de uma leitura elétrica desta unidade. O `YXC 12.0...` deve
ser tratado como um componente nominal de 12 MHz, provavelmente ligado ao
conversor USB–UART. Não alterar o clock da FPGA para 12 MHz sem confirmar o
rastreamento da trilha.

## Dados que devem ser enviados antes da programação

1. Foto geral da placa, frente e verso.
2. Foto aproximada do componente marcado `YXC 12.0...` e de qualquer outro
   oscilador próximo à FPGA.
3. Foto dos headers com a serigrafia legível, principalmente `RX`, `TX`, `GND`,
   `3V3`, `JTAG` e o botão de reset.
4. Saída de:

   ```bash
   jtagconfig
   ```

5. Se o conversor serial onboard aparecer no Linux:

   ```bash
   dmesg | tail -n 30
   ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
   ```

6. Marcações do módulo GPS: `VCC`, `GND`, `TX`, `RX`; tensão da placa do
   breakout; e uma foto do módulo. O teste usará inicialmente somente o `TX`
   do GPS para a entrada da FPGA.

## Ligações previstas

Para o teste UART com o conversor serial onboard ou CP2102:

| Origem | Destino | Observação |
| --- | --- | --- |
| TX da fonte/USB–UART | `UART_RX` da Cyclone IV | Cruzar TX com RX |
| `UART_TX` da Cyclone IV | RX da fonte/USB–UART | Saída para captura no PC |
| GND da fonte | GND da placa | Obrigatório |
| VCC lógico | Não ligar sem confirmar | Usar somente I/O de 3,3 V |

Para o GPS:

| GPS | Cyclone IV |
| --- | --- |
| `TX` | `UART_RX` |
| `GND` | `GND` |
| `VCC` | Alimentação especificada no breakout |

O `RX` do GPS não é necessário para a primeira aquisição. Não aplicar 5 V nos
I/Os da FPGA ou do módulo GPS.

## Sequência de testes físicos

### C0 — segurança e identificação elétrica

- Alimentar a placa pela fonte prevista.
- Confirmar que o USB-Blaster detecta um dispositivo Cyclone IV.
- Confirmar GND e a tensão lógica do header com multímetro.
- Não conectar o GPS até confirmar VCC, GND e nível do UART.

Aceite: placa sem aquecimento anormal, JTAG detectado e sinais identificados.

### P01 — UART autônoma (`uart_scope`)

Com `make cyclone4-uart-fpga` e o SOF programado:

- resetar a placa;
- medir `UART_TX` no osciloscópio;
- conferir o byte periódico `0x55`;
- verificar 9600 baud, 8N1 e aproximadamente `104,17 µs` por bit se o clock
  for 48 MHz;
- verificar quadro de aproximadamente `1,042 ms` e período de repetição de
  aproximadamente `100 ms`.

Se a marcação `YXC 12.0...` fosse erroneamente o clock usado pelo FPGA, um
bitstream parametrizado a 48 MHz apresentaria aproximadamente `416,7 µs` por
bit. Esse resultado indica clock efetivo de 12 MHz ou pinagem incorreta e deve
interromper a sequência até a causa ser resolvida.

### P02 — loopback da UART autônoma

Conectar `UART_TX` a `UART_RX` com jumper e resetar. O LED de recepção deve
indicar o `0x55` recebido e o indicador de erro deve permanecer inativo.

Aceite: TX observado, RX observado, sem erro de framing e três repetições após
reset.

### Registro adicional do P01 — Ensaio físico com os pinos acessíveis do J3

Como `PIN_86` não está disponível no header utilizado, foi criada a variante
`j3_scope`, mantendo o RTL da UART e roteando temporariamente `UART_TX` para um
pino acessível do J3. O primeiro ponto testado foi `PIN_125`, mas apresentou
nível alto estável de aproximadamente `2,2 V`, apesar do pino `3V3` medir
`3,3 V`. Esse ponto corresponde a uma linha de vídeo na referência da placa e
foi descartado para a validação elétrica da UART.

A variante foi então alterada para:

```text
UART_TX -> PIN_100 do J3
UART_RX -> PIN_103 do J3
```

O SOF foi recompilado, passou na auditoria temporal e foi programado com
sucesso no EP4CE6E22C8.

| Medida | Resultado |
| --- | ---: |
| Bit time | aproximadamente `104 µs` |
| Distância observada entre o início e a última borda visível | `904 µs` |
| Nível alto estável em `PIN_100` | `3,32 V` |
| Alimentação do header `3V3` | `3,3 V` |
| Programação JTAG | sucesso, zero erros |

O intervalo de `904 µs` não inclui o final do bit de parada, que permanece no
mesmo nível lógico do repouso. O ensaio valida a temporização e o nível
elétrico do TX no `PIN_100`. Não conectar monitor ou cabo VGA durante esse
ensaio; usar somente o osciloscópio e GND.

O loopback da variante `j3_scope` foi então executado com um jumper entre
`PIN_100` (TX) e `PIN_103` (RX). O RX deixou de depender do `PIN_87`, que não
está acessível no header utilizado. O `PIN_101` não foi usado
porque o Quartus o reserva como `nCEO` nessa configuração de Active Serial.

### Registro P03 aprovado — ESP32 como fonte e capturador

Em 21/09/2026, o projeto `baseline` foi programado e um ESP32 clássico foi
usado como fonte serial e capturador, por meio do CP2102 da própria placa. O
ESP32 foi identificado como `ESP32-D0WD-V3`, revisão 3.1, e executou o host
ESP-IDF 6.0.2 em UART2, 9600/8N1. A ligação usada foi GPIO17/TX2 → J3
`PIN_103`/RX, J3 `PIN_100`/TX → GPIO16/RX e GND comum.

O host enviou repetidamente `55 A5 00 FF 3C` a cada 1000 ms. No monitor USB a
sequência retornou exatamente com cinco bytes, sem divergência visível, em
amostras desde `I (271)` até pelo menos `I (243471)`. O GND foi conectado antes
da captura considerada válida; a observação anterior sem GND não foi usada
como evidência.

Não havia jumper entre `PIN_100` e `PIN_103` durante este ensaio. Portanto, o
retorno observado veio pelo caminho externo ESP32 TX → FPGA RX → FPGA TX →
ESP32 RX. O registro completo, incluindo a programação do ESP32 e a
interpretação correta do intervalo TX–RX, está em
[`docs/validacao-esp32-cyclone4-2026-09-21.md`](validacao-esp32-cyclone4-2026-09-21.md).

O intervalo de 260–270 ms entre as linhas `TX` e `RX` do monitor não é tratado
como latência da UART: o firmware faz uma leitura bloqueante de até 250 ms e
imprime `TX` antes da escrita. Uma medição de latência será feita somente com
um host/captura específico. O P04, que exige medição da forma de onda no
osciloscópio nessa configuração, continua pendente.

Para a repetição, o host foi atualizado em 22/09: coleta por eventos, cinco
bytes em até 30 ms, guarda de 10 ms para extras e linhas estruturadas
`RESULT`/`SUMMARY`. Nos tops integrados, os LEDs ativos em zero são `LED[0]`
heartbeat, `LED[1]` configuração/atividade, `LED[2]` overflow persistente e
`LED[3]` framing persistente. A força de saída UART continua em 8 mA até o P04
ser repetido com ponta ×10 e massa curta.

Na primeira observação do P04, foram relatados espaçamento aproximado de `30 µs`
entre picos na visão afastada e `680 ns` entre os picos negativo e positivo de
uma borda na visão aproximada. Esses valores ainda não fecham o bit time: para
9600 baud o valor esperado é `104,17 µs`. O registro detalhado classifica os
`680 ns` como possível transitório/ringing. A descida foi observada em cerca de
`−32 ns` e a estabilização em aproximadamente `800 ns`, uma acomodação de
`0,83 µs`. O registro orienta repetir a medida com sonda ×10 e massa curta em
[`docs/validacao-esp32-cyclone4-2026-09-21.md`](validacao-esp32-cyclone4-2026-09-21.md).
Também foram anotados pico negativo de `−1,52 V` e pico positivo de `4,92 V`.
Como esses valores ultrapassam os trilhos nominais de 3,3 V, eles permanecem
preliminares até serem repetidos com ponta ×10 e massa curta; não devem ser
usados como resultado elétrico final do artigo.

### P03/P04 — baseline

1. Compilar e programar `build/cyclone4/baseline/uart_baseline.sof`.
2. Enviar `55 A5 00 FF 3C` por uma fonte UART independente a 9600/8N1.
3. Capturar a saída no PC e, se possível, medir simultaneamente RX/TX no
   osciloscópio.
4. Fazer loopback externo e repetir três vezes.

Aceite: os cinco bytes saem na mesma ordem, sem framing error/overflow e com
forma de onda 8N1 correta.

### P05/P06 — secure

1. Criar um contexto privado novo para a captura.
2. Compilar com `CONTEXT_FILE` e programar
   `build/cyclone4/secure/uart_secure.sof`.
3. Enviar exatamente os mesmos bytes do baseline.
4. Capturar o ciphertext, decifrar no PC e comparar com a entrada.
5. Repetir após reset e registrar o bloqueio/recarregamento do contexto.

Aceite: ciphertext capturado, recuperação byte a byte, contexto registrado e
três repetições sem divergência.

### P07 — GPS sem criptografia

- Alimentar o NEO-M8N conforme o breakout.
- Conectar somente `GPS TX → UART_RX` e GND comum.
- Capturar uma referência NMEA pelo canal independente disponível.
- Validar com `scripts/gps_capture.py`.
- Programar baseline e verificar retransmissão das sentenças.

Aceite: sentenças completas, CRLF preservado, checksum válido, zero overflow e
comparação byte a byte com a referência.

### P08/P09 — GPS baseline e secure

Executar três repetições em cada configuração. No secure, usar contexto novo,
capturar o ciphertext e recuperar a mensagem no PC. Registrar o arquivo bruto,
relatório, hashes, quantidade de bytes, primeira divergência e LEDs de erro.

### P10 — estabilidade contínua

Manter o GPS transmitindo durante uma duração registrada. Contabilizar bytes,
sentenças, framing errors, overflow, maior nível da FIFO e primeira divergência.
O ensaio só passa se a saída recuperada coincidir integralmente com a referência.

### P11 — reset e recuperação

Pressionar reset entre duas capturas e confirmar que nenhum byte da captura
anterior é retransmitido. Depois iniciar uma captura nova com contexto novo no
secure.

## Comandos

```bash
make cyclone4-uart-fpga
make cyclone4-baseline-fpga
make cyclone4-secure-fpga

# Exemplo seguro; o contexto deve permanecer em data/private/.
CONTEXT_FILE=data/private/ensaio-cyclone4/contexto.json \
  make cyclone4-secure-fpga
```

Programação JTAG, após conferir o nome exibido pelo `jtagconfig`:

```bash
quartus_pgm -c 'USB-Blaster [cabo]' -m jtag \
  -o 'p;build/cyclone4/uart_scope/uart_scope.sof'
```

## Registro de evidência

| Teste | Data/hora | Commit | SOF/hash | Instrumento/captura | Resultado |
| --- | --- | --- | --- | --- | --- |
| C0 |  |  |  |  |  |
| P01 | 21/09/2026 | `e6ea4ff` | `build/cyclone4/j3_scope/uart_scope_j3.sof` | Osciloscópio, J3 `PIN_100` | **Aprovado** — 104 µs/bit, 3,32 V |
| P02 | 21/09/2026 | `e6ea4ff` | `build/cyclone4/j3_scope/uart_scope_j3.sof` | Jumper J3 `PIN_100` ↔ `PIN_103`, LEDs | **Aprovado** — loopback `0x55`, sem erro |
| P03 | 21/09/2026 | `4d8b40c` | `build/cyclone4/baseline/uart_baseline.sof`, checksum `0x000BC41F` | ESP32 D0WD-V3/CP2102, ESP-IDF 6.0.2, 9600/8N1, sem jumper local | **Aprovado** — `55 A5 00 FF 3C` retornou com 5 bytes pelo caminho externo |
| P04 | 21/09/2026 |  |  | Osciloscópio ainda não usado nesta configuração | **Pendente** — falta medir os quadros do baseline |
| P05/P06 |  |  |  |  |  |
| P07 |  |  |  |  |  |
| P08/P09 |  |  |  |  |  |
| P10 |  |  |  |  |  |
| P11 |  |  |  |  |  |

Uma compilação ou uma forma de onda correta não substitui a captura serial
comparada. Resultados físicos devem ser registrados somente depois de a placa
ser programada e o fluxo elétrico ser observado.
