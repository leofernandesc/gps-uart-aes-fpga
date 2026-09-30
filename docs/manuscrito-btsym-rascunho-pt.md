# Aquisição e Transmissão Segura de Dados GPS em FPGA usando UART e AES-128-CTR

**Leonardo Fernandes Cavalcante**, **Edgard Luciano Oliveira Silva**<br>
Rascunho de trabalho para o BTSym’26. Escopo: u-blox NEO-M8N, DE10-Lite/MAX
10, 50 MHz e UART 38400/8N1. A aquisição física do GPS e o encaminhamento
baseline foram validados. Os fluxos GPS cifrados foram validados por replay de
capturas armazenadas, com o GPS desconectado; não foi testada aquisição GPS ao
vivo simultânea à cifragem.

## Resumo

Receptores GPS frequentemente disponibilizam dados de navegação por uma
interface serial assíncrona, que não fornece confidencialidade. Este trabalho
implementa e avalia dois caminhos UART–FIFO em uma FPGA DE10-Lite/MAX 10: uma
baseline transparente e uma variante secure com AES-128-CTR. Ambas usam clock
de 50 MHz, UART 38400/8N1 e FIFO de 1.024 bytes. Ensaios físicos capturaram
dados do NEO-M8N e validaram sentenças NMEA no caminho baseline. Os ensaios
secure reproduziram capturas GPS armazenadas pela FPGA e recuperaram os bytes
originais independentemente no PC; o GPS permaneceu desconectado durante esses
replays. Um fluxo de 32.768 bytes passou nas duas variantes, sem bytes perdidos
ou extras. A análise pós-fit do Quartus registrou 331 elementos lógicos e 212
registradores na baseline, contra 5.603 elementos lógicos e 913 registradores
na variante secure. As Fmax mínimas são 117,56 e 103,38 MHz, respectivamente,
ambas acima do clock de operação de 50 MHz. O replay RTL sintético de 309 bytes
não apresentou divergência ou overflow e atingiu ocupação máxima de um byte na
FIFO. Os resultados de simulação, implementação e bancada são distinguidos.

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
   temporais são coletados dos relatórios pós-fit; e
4. **Validação física:** a forma de onda UART é observada com um Analog
   Discovery 2, o tráfego serial é conferido por adaptador CP2102 USB–UART e as
   capturas do NEO-M8N são validadas quanto a ASCII, CRLF, tamanho e checksum.

`make check` passou na configuração UART atualizada, incluindo vetores
independentes de AES/CTR, integração baseline/secure, checagens estruturais e
36 testes Python. Ensaios físicos também confirmaram o enquadramento UART e o
caminho NEO-M8N→DE10-Lite baseline. Os ensaios secure em hardware usaram vetores
conhecidos e replay de dados GPS previamente capturados; não cifraram um fluxo
GPS ao vivo.

### 3.2 Cargas e condições de teste

O fixture público de aplicação contém cinco sentenças NMEA (RMC, GGA, GSA, GSV
e TXT), checksums válidos e final de linha CRLF na transmissão. Seu tamanho
total é de 309 bytes. Trata-se de um replay NMEA público e sintético do formato
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
| Replay NMEA sintético | RTL a 50 MHz/38400 | 309 bytes | caminho da aplicação no clock de produção |
| GPS físico baseline | NEO-M8N e DE10-Lite a 38400/8N1 | capturas de 4.096 bytes | aquisição, encaminhamento e validade NMEA |
| Replay GPS armazenado | baseline/secure na DE10-Lite a 38400/8N1 | 4.096 e 32.768 bytes | preservação byte a byte e recuperação CTR independente |
| Quartus pós-fit | restrição de 50 MHz | UART + FIFO, com/sem AES-CTR | custo de recursos e timing |

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

### 4.2 Resultados físicos na FPGA

A forma de onda UART da DE10-Lite foi observada com o Analog Discovery 2. No
teste de encaminhamento baseline, o estímulo de cinco bytes foi
decodificado corretamente em RX e TX; a separação medida entre as bordas de
início de RX e TX foi de aproximadamente 247,5 µs, incluindo a recepção UART e
a validação do byte. Esta é uma observação da interface física, não uma medida
isolada da latência AES.

Os testes com GPS e fluxos longos estão resumidos abaixo. Os bytes derivados do
GPS foram mantidos no diretório privado dos ensaios e não são reproduzidos
neste artigo.

| Teste | Procedimento físico | Resultado |
| --- | --- | --- |
| P07 | Captura direta do NEO-M8N; depois GPS ao vivo → DE10-Lite baseline → PC, em outra janela de captura | 4.096 bytes em cada captura; validador NMEA passou em 66 sentenças de referência e 67 encaminhadas |
| P08 | Replay baseline da referência GPS de 4.096 bytes | 3/3 repetições exatas; zero bytes faltantes/extras |
| P09 | Replay secure da referência GPS de 4.096 bytes | Ciphertext diferente da entrada; recuperação no PC coincidiu nos 4.096 bytes |
| P10 | Replay baseline e secure da referência GPS de 32.768 bytes | Baseline coincidiu em todos os bytes; ciphertext secure foi recuperado exatamente; zero faltantes/extras |
| P11 | Reset secure, bloqueio de contexto consumido e recuperação com contexto novo | Duas transmissões secure de 5 bytes aprovadas; a sondagem após consumo não recebeu resposta, como esperado |

Os arquivos P07/P10, de tamanho fixo, terminam em limites arbitrários de
bytes. O validador NMEA preservou os fragmentos parciais finais (18 e 21 bytes
no P07; 15 bytes na referência P10) e validou separadamente as sentenças
completas.

As duas capturas P07 foram obtidas em momentos diferentes enquanto a saída do
GPS variava; por isso, os fluxos não foram comparados diretamente. P07
comprova recepção física do GPS, encaminhamento baseline e validade sintática
NMEA; a preservação byte a byte foi comprovada pelos replays determinísticos
P08/P10. Durante os replays P08–P11, o GPS permaneceu desconectado. Em
particular, os resultados secure demonstram cifragem em hardware e recuperação
exata de dados derivados do GPS, mas não aquisição GPS ao vivo simultânea ao
processamento AES.

O CP2102 observou tempos de transação de aproximadamente 1,078 s para 4.096
bytes e 8,545–8,546 s para 32.768 bytes. Esses valores incluem PC, driver serial
Linux e ponte USB; são tempos ponta a ponta da bancada, não latência isolada da
FPGA ou do AES. A primeira tentativa baseline de 32 KiB terminou em 5.732
bytes; o resultado aprovado é o replay subsequente com a coleta RX ativa
durante a transmissão. Ambos os registros foram preservados, mas somente a
execução completa foi contabilizada como aprovada.

### 4.3 Comparação pós-fit na FPGA

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

Os resultados mostram um compromisso claro de implementação: AES-128-CTR
aumenta lógica e registradores e reduz a Fmax pós-fit, enquanto as duas
variantes atendem à restrição de operação de 50 MHz. O replay RTL sintético de
309 bytes atingiu ocupação máxima de um byte na FIFO. Replays físicos de 4.096
e 32.768 bytes passaram nas variantes baseline e secure, com recuperação
independente exata do payload secure. Tempos semelhantes observados pelo host
para baseline e secure são consistentes com o caminho serial/host fixo
dominando esses ensaios, mas não isolam a latência criptográfica da FPGA.

A aquisição física do GPS e o encaminhamento baseline foram demonstrados no
ponto de operação selecionado. O fluxo GPS secure foi reproduzido de uma
captura armazenada, com o receptor desconectado; portanto, uma execução ao
vivo GPS→AES simultânea ainda não faz parte da evidência. Além disso, AES-CTR
sozinho não autentica os dados; um modo autenticado ou mecanismo de integridade
separado seria necessário para telemetria segura completa.

## 6. Limites da evidência

A campanha física utilizou uma placa DE10-Lite/MAX 10 e um módulo GPS. As
capturas de referência GPS e da saída encaminhada P07 foram obtidas em janelas
distintas, sem comparação byte a byte simultânea. Os testes secure com GPS usam
capturas armazenadas, não um GPS conectado ao bitstream secure. Os indicadores
LEDR de framing, overflow da FIFO e ocupação não foram registrados
independentemente após a transferência P11. Os tempos seriais informados pelo
host incluem efeitos de Linux e USB–UART, e o Quartus Power Analyzer não foi
utilizado; portanto, não se reivindica latência exclusiva da FPGA nem potência
medida. Chave e nonce são parâmetros de build, não segredos provisionados em
tempo de execução. Por fim, AES-CTR oferece confidencialidade, mas não
autenticação nem integridade.

## 7. Conclusão

Este trabalho apresenta uma arquitetura na DE10-Lite para encaminhamento de
dados GPS por UART com confidencialidade AES-128-CTR opcional. Testes RTL e
análise pós-fit quantificam o comportamento funcional e o custo de
implementação; ensaios físicos validam o caminho baseline com NEO-M8N e a
recuperação exata, na FPGA, de dados derivados do GPS reproduzidos. O fluxo
secure não foi testado com o GPS conectado ao vivo, e os tempos do host não são
interpretados como latência do AES. As duas implementações atendem à restrição
de 50 MHz, enquanto a variante secure usa substancialmente mais lógica e
registradores. Os resultados estabelecem uma base reproduzível para trabalhos
futuros sobre aquisição segura ao vivo e telemetria autenticada.

## Referências para reprodução

- [`docs/metricas-fpga-2026-09-29.md`](metricas-fpga-2026-09-29.md)
- [`docs/validacao-replay-nmea-2026-09-20.md`](validacao-replay-nmea-2026-09-20.md)
- [`docs/validacao-captura-nmea-2026-09-20.md`](validacao-captura-nmea-2026-09-20.md)
- [`docs/plano-de-testes.md`](plano-de-testes.md)
- [`docs/integracao-uart-ctr.md`](integracao-uart-ctr.md)
- [`scripts/fpga_metrics.py`](../scripts/fpga_metrics.py)
- [`scripts/gps_capture.py`](../scripts/gps_capture.py)
