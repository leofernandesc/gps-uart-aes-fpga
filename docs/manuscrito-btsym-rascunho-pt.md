# Aquisição e Transmissão Segura de Dados GPS em FPGA usando UART e AES-128-CTR

**Leonardo Fernandes Cavalcante**, **Edgard Luciano Oliveira Silva**<br>
Rascunho de trabalho para o BTSym’26. Escopo atualizado em 29/09: u-blox
NEO-M9N-00B-00, somente DE10-Lite/MAX 10, 50 MHz e UART 38400/8N1. Medições
anteriores a 9600 baud são históricas, não resultados do ponto de operação
final. Resultados de GPS físico permanecem pendentes até sua captura.

## Resumo

Receptores GPS frequentemente disponibilizam dados de navegação por uma
interface serial assíncrona, que não fornece confidencialidade. Este trabalho
avalia uma arquitetura RTL que recebe dados NMEA do u-blox NEO-M9N e os
transmite por uma FPGA DE10-Lite. Duas variantes elaboradas compartilham UART
50 MHz, 38400 baud, 8N1 e FIFO de 1.024 bytes: a baseline encaminha os bytes,
enquanto a secure insere AES-128-CTR. O estudo combina verificação AES/CTR
independente, replay NMEA público de 309 bytes e análise pós-fit no Quartus. A
baseline usa 331 elementos lógicos e 212 registradores; a secure usa 5.603
elementos lógicos e 913 registradores. As Fmax mínimas são 117,56 e 103,38 MHz,
respectivamente, acima do clock comum de 50 MHz. O replay NMEA simulado não
apresentou divergência nem overflow e atingiu ocupação máxima de uma posição da
FIFO. A aquisição física do M9N continua pendente e não é inferida do replay.

**Palavras-chave:** FPGA, GPS, UART, AES-128-CTR, segurança embarcada,
hardware reconfigurável.

## 1. Introdução

Receptores de navegação são frequentemente integrados a sistemas embarcados
por meio de enlaces seriais assíncronos. Sentenças NMEA são simples de
transportar e inspecionar, mas a interface UART não oferece confidencialidade
nem proteção contra modificações. Em aplicações nas quais informações de
posição são sensíveis, a inclusão de uma camada criptográfica deve ser avaliada
juntamente com as restrições de recursos e temporização do caminho de
comunicação.

Este trabalho investiga uma arquitetura de hardware compacta para transmissão
segura de dados seriais orientados a GPS. A arquitetura recebe bytes por uma
UART conectada a uma fonte GPS, armazena-os em uma FIFO síncrona, aplica
opcionalmente AES-128-CTR e transmite os bytes resultantes por uma segunda
UART. O mesmo RTL é elaborado em duas configurações, permitindo isolar o custo
do bloco criptográfico do custo do sistema de comunicação.

As contribuições são:

1. uma integração UART–FIFO–AES-CTR orientada a bytes, projetada para o ponto
   fixo de operação de 50 MHz, 38400 baud e 8N1;
2. duas elaborações, baseline e secure, para um alvo DE10-Lite/MAX 10;
3. um oráculo independente no PC e um replay NMEA reproduzível para verificar
   os bytes observados na saída serial; e
4. uma comparação quantitativa de recursos pós-fit, Fmax, ocupação da FIFO e
   latência RTL de ponta a ponta.

O AES-CTR é utilizado para fornecer confidencialidade. Ele não fornece
autenticação, proteção contra alteração, proteção contra replay ou proteção
contra spoofing de GNSS; essas limitações fazem parte da definição do sistema e
são discutidas explicitamente.

## 2. Arquitetura proposta

### 2.1 Caminho de dados

O sistema é avaliado em duas formas elaboradas:

```text
Entrada serial orientada a GPS
             |
          UART RX
             |
          FIFO 1024 B
             |
      +------+------+
      |             |
   baseline     AES-128-CTR
      |             |
      +------+------+
             |
          UART TX
             |
        Receptor PC
```

A baseline remove os módulos AES durante a elaboração. Portanto, ela é uma
referência direta de UART mais FIFO, e não um bypass selecionado durante a
execução. A variante secure insere o fluxo CTR depois que um byte é lido da
FIFO. A ponte retém o byte lido da FIFO síncrona até que o próximo estágio o
aceite, evitando a perda de um pulso `valid` durante uma pausa da UART.

### 2.2 UART e armazenamento

O ponto fixo de operação é clock de 50 MHz na FPGA, 38400 baud e enquadramento
8N1. O receptor UART sincroniza a entrada assíncrona e amostra o quadro em seu
centro. Bytes válidos entram em uma FIFO síncrona de 1.024 bytes. Erros de
framing e overflow da FIFO invalidam a captura ativa e permanecem visíveis até
um abort ou reset explícito.

A FIFO é posicionada antes do estágio criptográfico. Isso mantém a interface de
comunicação independente da latência do AES e permite observar se o estágio
criptográfico se torna um gargalo.

### 2.3 AES-128-CTR

O AES-128 opera sobre blocos de 128 bits usando uma chave de 128 bits. No modo
CTR, o AES cifra a concatenação de um nonce de 96 bits com um contador de 32
bits; a máscara resultante é aplicada por XOR ao fluxo de dados. O adaptador
implementado disponibiliza a máscara um byte por vez e avança somente quando o
byte de saída correspondente é aceito. O contador é bloqueado antes de sofrer
wraparound, e um novo nonce é exigido para uma nova captura com a mesma chave.

A chave, o nonce e o contador inicial são parâmetros do experimento. O wrapper
atual da DE10-Lite aplica esses valores estaticamente durante a elaboração e o
build; não é reivindicado um protocolo de provisionamento de chave em tempo de
execução.

## 3. Método experimental

### 3.1 Níveis de verificação

A avaliação separa três tipos de evidência:

1. **Verificação funcional RTL:** os testbenches de UART, FIFO, AES, CTR e da
   ponte exercitam transferências normais, pausas, erros de framing, overflow,
   cancelamento, reset e esgotamento do contador.
2. **Verificação independente no PC:** o testbench decodifica o fio serial TX,
   enquanto Python e `cryptography` recuperam o fluxo secure sem usar payloads
   ou máscaras internas do RTL como oráculo. Um validador separado confere
   sentenças NMEA completas com CRLF, ASCII, checksum e tamanho antes que um
   arquivo de GPS físico possa se tornar referência do experimento.
3. **Análise de implementação no Quartus:** os projetos baseline e secure são
   ajustados separadamente para o dispositivo MAX 10, e recursos, Fmax e slacks
   temporais são coletados dos relatórios pós-fit.

`make check` passou na configuração UART atualizada, incluindo vetores
independentes de AES/CTR, integração baseline/secure, checagens estruturais e
36 testes Python. Esses resultados não constituem um ensaio físico de GPS.

A evidência atual não substitui o ensaio físico final. Os bitstreams integrados
baseline e secure precisam ser gerados a 38400 e testados na DE10-Lite. A
entrada do NEO-M9N ainda não foi capturada eletricamente nessa configuração.

### 3.2 Cargas e condições de teste

O fixture público de aplicação contém cinco sentenças NMEA (RMC, GGA, GSA, GSV
e TXT), checksums válidos e final de linha CRLF na transmissão. Seu tamanho
total é de 309 bytes. Trata-se de um replay público/sintético do formato
esperado do GPS, não de uma captura física.

O fixture versionado é convertido para o mesmo fluxo de bytes CRLF esperado da
fonte serial. Para uma captura ao vivo, `scripts/gps_capture.py` registra a
quantidade e os tipos de sentença, o número de bytes e o SHA-256 somente depois
de o arquivo bruto passar pelas verificações formais. Isso protege o fluxo de
comparação contra truncamento ou conversão de final de linha, mas não comprova
a origem elétrica do arquivo.

| Teste | Clock/UART | Dados | Objetivo |
| --- | --- | ---: | --- |
| Regressão RTL | acelerado e 50 MHz/38400 | fluxos curtos e de fronteira | cobertura funcional e de falhas |
| Replay NMEA | 50 MHz/38400 | 309 bytes | caminho da aplicação no clock de produção |
| Quartus baseline | restrição de 50 MHz | UART + FIFO | recursos e timing de referência |
| Quartus secure | restrição de 50 MHz | UART + FIFO + AES-CTR | custo criptográfico |

## 4. Resultados

### 4.1 Replay serial e resultados funcionais

O replay NMEA completo foi processado pelas duas elaborações no clock de
produção de 50 MHz/38400 baud. A saída baseline coincidiu com os bytes de
entrada. A saída secure foi recuperada com o contexto AES-CTR independente e
coincidiu com os mesmos 309 bytes de entrada.

| Métrica | Baseline | Secure |
| --- | ---: | ---: |
| Bytes reproduzidos | 309 | 309 |
| Ocupação máxima da FIFO | 1 byte | 1 byte |
| RX válido até início do TX | 80 ns | 80 ns |
| RX válido até fim do TX | 260.480 ns | 260.480 ns |
| Início do quadro de entrada até início do TX | 247.503 ns | 247.503 ns |
| Divergências de bytes | 0 | 0 após recuperação |
| Overflow da FIFO | 0 | 0 |

Os valores nominais vêm do replay RTL em clock de produção, sem pausas
artificiais no TX. Eles não são medições elétricas do GPS ou da placa.

A pequena ocupação da FIFO no replay em clock de produção indica que a fonte
serial, e não o estágio AES, domina a taxa de transferência nessa carga. Essa
conclusão é limitada ao modelo RTL na taxa fixa testada e deve ser novamente
verificada com um fluxo GPS físico.

### 4.2 Comparação pós-fit na FPGA

| Métrica | Baseline | Secure | Secure − baseline |
| --- | ---: | ---: | ---: |
| Elementos lógicos | 331 | 5.603 | +5.272 (+1.592,75%) |
| Registradores | 212 | 913 | +701 (+330,66%) |
| Bits de memória | 8.192 | 8.192 | 0 |
| Pinos | 14 | 14 | 0 |
| Fmax mínima | 117,56 MHz | 103,38 MHz | −14,18 MHz (−12,06%) |
| Pior slack de setup | 11,494 ns | 10,327 ns | positivo |
| Pior slack de hold | 0,103 ns | 0,102 ns | positivo |
| Pior slack de recovery | 13,962 ns | 13,416 ns | positivo |
| Pior slack de removal | 0,440 ns | 2,230 ns | positivo |

As duas configurações atendem à restrição de clock de 50 MHz nos três cantos
auditados. A variante secure apresenta um custo significativo de lógica e
registradores porque a implementação atual do AES calcula as chaves de rodada
sob demanda e usa um datapath iterativo. Sua menor Fmax continua acima da
frequência de operação selecionada.

## 5. Discussão e limitações

Os resultados mostram um compromisso claro. A inclusão do AES-128-CTR aumenta a
lógica e os registradores e reduz a Fmax pós-fit, enquanto as duas variantes
precisam atender ao mesmo clock de operação de 50 MHz. A 38400 baud, um quadro
8N1 de dez bits dura aproximadamente 260,4 µs; o replay RTL de 309 bytes
registrou ocupação máxima de uma posição da FIFO em ambas as variantes. Isso
vale para a carga simulada e não é uma afirmação sobre todo receptor GPS ou
ensaio físico prolongado.

A carga NMEA reproduzível no RTL é um replay público/sintético, não uma captura
ao vivo do NEO-M9N. Resultados físicos da DE10-Lite e do GPS a 38400 permanecem
pendentes e devem ser distinguidos da simulação e da implementação Quartus. Por
fim, AES-CTR sozinho não autentica os dados; um modo autenticado
ou mecanismo de integridade separado seria necessário para um protocolo
completo de telemetria segura.

## 6. Plano de validação final

O ensaio físico restante é:

1. recompilar e programar baseline e secure a 38400/8N1;
2. repetir a forma de onda/loopback UART e os ensaios conhecidos P03–P06 na
   DE10-Lite;
3. confirmar alimentação e níveis do breakout NEO-M9N e capturar sua UART;
4. validar sentenças NMEA completas e preservar o hash da captura privada;
5. executar aquisição GPS direta e replay determinístico pelas variantes
   baseline e secure, recuperando o ciphertext no PC com nonce novo; e
6. executar intervalo contínuo e registrar bytes, framing, overflow e reset.
Qualquer medida não realizada permanece explicitamente pendente.

Os resultados físicos devem substituir ou complementar a Seção 4 sem alterar a
metodologia RTL/PC. Simulação, síntese e análise pós-fit devem continuar
identificadas separadamente dessas medições.

## 7. Conclusão

Este trabalho define e avalia uma arquitetura reutilizável em FPGA para
aquisição de dados seriais orientados a GPS com confidencialidade AES-128-CTR.
O caminho RTL comum torna as variantes baseline e secure diretamente
comparáveis, enquanto o verificador independente no PC e o replay NMEA público
tornam o experimento reproduzível. Os resultados da DE10-Lite a 38400 baud
quantificam o custo do estágio criptográfico e mostram que ambos os builds
atendem ao clock de 50 MHz na análise pós-fit. A aquisição física do M9N e a
validação integrada de ponta a ponta permanecem pendentes; não se afirma
operação GPS física antes de obtê-las.

## Referências para reprodução

- [`docs/metricas-fpga-2026-09-29.md`](metricas-fpga-2026-09-29.md)
- [`docs/validacao-replay-nmea-2026-09-20.md`](validacao-replay-nmea-2026-09-20.md)
- [`docs/validacao-captura-nmea-2026-09-20.md`](validacao-captura-nmea-2026-09-20.md)
- [`docs/plano-de-testes.md`](plano-de-testes.md)
- [`docs/integracao-uart-ctr.md`](integracao-uart-ctr.md)
- [`scripts/fpga_metrics.py`](../scripts/fpga_metrics.py)
- [`scripts/gps_capture.py`](../scripts/gps_capture.py)
