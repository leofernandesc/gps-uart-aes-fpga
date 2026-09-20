# Aquisição e Transmissão Segura de Dados GPS em FPGA usando UART e AES-128-CTR

**Leonardo Fernandes Cavalcante**, **Edgard Luciano Oliveira Silva**<br>
Rascunho de trabalho para o BTSym’26. Os resultados de GPS físico e da
integração em bancada são identificados explicitamente como pendentes quando
aplicável.

## Resumo

Receptores GPS frequentemente disponibilizam seus dados de navegação por uma
interface serial assíncrona, mas o fluxo de bytes resultante não possui
confidencialidade. Este trabalho apresenta uma arquitetura RTL própria para
adquirir dados no formato NMEA por uma UART de 9600 baud, 8N1, e aplicar
AES-128 no modo contador (CTR) antes da transmissão serial. A arquitetura é
organizada como um caminho comum de UART e FIFO com duas variantes elaboradas:
uma baseline, que encaminha os bytes recebidos, e uma secure, que insere um
fluxo AES-128-CTR entre a recepção e a transmissão. As duas variantes foram
sintetizadas e ajustadas para um alvo DE10-Lite/MAX 10 com clock de 50 MHz.
A verificação independente no PC foi usada para comparar os bytes observados na
saída serial e recuperar o fluxo cifrado. Um replay NMEA público de 309 bytes
também foi executado no clock de produção de 50 MHz/9600 baud, sem divergência
de bytes ou overflow da FIFO. Os relatórios pós-fit do Quartus indicam 342
elementos lógicos e 215 registradores para a baseline, contra 6.984 elementos
lógicos e 2.196 registradores para a secure; a menor Fmax reportada diminui de
132,61 MHz para 82,19 MHz, enquanto as duas variantes permanecem acima do
clock de operação de 50 MHz. A aquisição física de dados do NEO-M8N e o ensaio
integrado na placa permanecem como etapa final de validação.

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
   fixo de operação de 50 MHz, 9600 baud e 8N1;
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

O ponto fixo de operação é clock de 50 MHz na FPGA, 9600 baud e enquadramento
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
   ou máscaras internas do RTL como oráculo.
3. **Análise de implementação no Quartus:** os projetos baseline e secure são
   ajustados separadamente para o dispositivo MAX 10, e recursos, Fmax e slacks
   temporais são coletados dos relatórios pós-fit.

A evidência atual não substitui o ensaio físico final. Os bitstreams integrados
baseline e secure ainda precisam ser programados e testados na DE10-Lite, e a
entrada do NEO-M8N deve ser capturada eletricamente.

### 3.2 Cargas e condições de teste

O fixture público de aplicação contém cinco sentenças NMEA (RMC, GGA, GSA, GSV
e TXT), checksums válidos e final de linha CRLF na transmissão. Seu tamanho
total é de 309 bytes. Trata-se de um replay público/sintético do formato
esperado do GPS, não de uma captura física.

| Teste | Clock/UART | Dados | Objetivo |
| --- | --- | ---: | --- |
| Regressão RTL | acelerado e 50 MHz/9600 | fluxos curtos e de fronteira | cobertura funcional e de falhas |
| Replay NMEA | 50 MHz/9600 | 309 bytes | caminho da aplicação no clock de produção |
| Quartus baseline | restrição de 50 MHz | UART + FIFO | recursos e timing de referência |
| Quartus secure | restrição de 50 MHz | UART + FIFO + AES-CTR | custo criptográfico |

## 4. Resultados

### 4.1 Replay serial e resultados funcionais

O replay NMEA completo foi processado pelas duas elaborações no clock de
produção de 50 MHz/9600 baud. A saída baseline coincidiu com os bytes de
entrada. A saída secure foi recuperada com o contexto AES-CTR independente e
coincidiu com os mesmos 309 bytes de entrada.

| Métrica | Baseline | Secure |
| --- | ---: | ---: |
| Bytes reproduzidos | 309 | 309 |
| Ocupação máxima da FIFO | 2 bytes | 2 bytes |
| Primeiro RX até primeiro TX | 169.269 ciclos / 3,385 ms | 169.269 ciclos / 3,385 ms |
| Primeiro RX até último TX | 16.236.274 ciclos / 324,725 ms | 16.236.274 ciclos / 324,725 ms |
| Divergências de bytes | 0 | 0 após recuperação |
| Overflow da FIFO | 0 | 0 |

A pequena ocupação da FIFO no replay em clock de produção indica que a fonte
serial, e não o estágio AES, domina a taxa de transferência nessa carga. Essa
conclusão é limitada ao modelo RTL na taxa fixa testada e deve ser novamente
verificada com um fluxo GPS físico.

### 4.2 Comparação pós-fit na FPGA

| Métrica | Baseline | Secure | Secure − baseline |
| --- | ---: | ---: | ---: |
| Elementos lógicos | 342 | 6.984 | +6.642 (+1.942,11%) |
| Registradores | 215 | 2.196 | +1.981 (+921,40%) |
| Bits de memória | 8.192 | 8.192 | 0 |
| Pinos | 14 | 14 | 0 |
| Fmax mínima | 132,61 MHz | 82,19 MHz | −50,42 MHz (−38,02%) |
| Pior slack de setup | 12,459 ns | 7,833 ns | positivo |
| Pior slack de hold | 0,102 ns | 0,111 ns | positivo |
| Pior slack de recovery | 15,341 ns | 12,724 ns | positivo |
| Pior slack de removal | 0,424 ns | 2,332 ns | positivo |

As duas configurações atendem à restrição de clock de 50 MHz nos três cantos
auditados. A variante secure apresenta um custo significativo de lógica e
registradores porque a implementação atual do AES armazena o estado das chaves
de rodada e usa um datapath iterativo. Sua menor Fmax continua acima da
frequência de operação selecionada.

## 5. Discussão e limitações

Os resultados mostram um compromisso claro. A inclusão do AES-128-CTR aumenta a
quantidade de lógica e registradores e reduz a Fmax pós-fit, enquanto a carga da
UART permanece muito abaixo da margem temporal disponível na FPGA. A taxa de
9600 baud também torna o intervalo de comunicação muito maior que as operações
internas do AES para o fluxo testado, o que explica a baixa ocupação da FIFO.

A avaliação atual possui quatro limitações importantes. Primeiro, a entrada
NMEA usada no RTL é um replay público/sintético, e não uma captura ao vivo do
NEO-M8N. Segundo, os designs integrados baseline e secure foram compilados, mas
ainda precisam ser programados e testados fisicamente na DE10-Lite. Terceiro, a
comparação com a Cyclone IV não faz parte da tabela quantitativa atual porque o
dispositivo, clock e pinagem exatos ainda não foram confirmados. Por fim,
AES-CTR sozinho não autentica os dados; um modo autenticado ou mecanismo de
integridade separado seria necessário para um protocolo completo de telemetria
segura.

## 6. Plano de validação final

O ensaio físico restante é:

1. programar o bitstream baseline e verificar uma sequência serial conhecida;
2. conectar o TX do NEO-M8N ao RX configurado da FPGA, com terra comum e níveis
   lógicos confirmados;
3. registrar uma referência GPS independente e comparar a saída baseline;
4. programar o bitstream secure, registrar o ciphertext e recuperá-lo no PC com
   um nonce novo devidamente registrado; e
5. repetir o teste durante um intervalo contínuo, registrando perdas, erros de
   framing, overflow da FIFO, latência e recuperação após reset.

Os resultados físicos devem substituir ou complementar a Seção 4 sem alterar a
metodologia RTL/PC. Simulação, síntese e análise pós-fit devem continuar
identificadas separadamente dessas medições.

## 7. Conclusão

Este trabalho define e avalia uma arquitetura reutilizável em FPGA para
aquisição de dados seriais orientados a GPS com confidencialidade AES-128-CTR.
O caminho RTL comum torna as variantes baseline e secure diretamente
comparáveis, enquanto o verificador independente no PC e o replay NMEA público
tornam o experimento reproduzível antes do acesso completo ao hardware. Os
resultados atuais da DE10-Lite quantificam o custo do estágio criptográfico e
indicam atendimento ao requisito de 50 MHz na análise pós-fit. A aquisição
física do GPS e a validação integrada na placa são os passos restantes antes de
o manuscrito poder afirmar operação de hardware de ponta a ponta.

## Referências para reprodução

- [`docs/metricas-fpga-2026-09-20.md`](metricas-fpga-2026-09-20.md)
- [`docs/validacao-replay-nmea-2026-09-20.md`](validacao-replay-nmea-2026-09-20.md)
- [`docs/plano-de-testes.md`](plano-de-testes.md)
- [`docs/integracao-uart-ctr.md`](integracao-uart-ctr.md)
- [`scripts/fpga_metrics.py`](../scripts/fpga_metrics.py)
