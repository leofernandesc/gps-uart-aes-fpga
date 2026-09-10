# Plano de execução e colaboração

Este documento é o guia de trabalho do projeto do artigo. Ele serve para que
qualquer colaborador saiba o que precisa fazer, qual resultado deve entregar e
como verificar se a tarefa está concluída.

## Objetivo

Implementar e avaliar, em FPGA, uma arquitetura para receber dados de um
receptor **NEO-M8N-010** via UART, aplicar AES-128-CTR em hardware e enviar o
fluxo cifrado ao PC:

```text
GPS NEO-M8N-010
       │ TX / UART 9600 8N1
       ▼
UART RX → FIFO 1024 bytes → controle de sessão → AES-128-CTR → UART TX → PC
                                                        │
                                                        ▼
                                           decifragem e análise no PC
```

Parâmetros fixos do protótipo:

| Item | Definição |
| --- | --- |
| FPGA | DE10-Lite, MAX 10, clock de 50 MHz |
| GPS | NEO-M8N-010; VCC marcado como 3,3 V |
| UART | 9600 baud, 8N1 |
| Cifra | AES-128-CTR, núcleo iterativo próprio |
| Entrada | Bytes opacos do GPS; não há parser NMEA no FPGA |
| Saída | Fluxo cifrado capturado pelo PC |
| Avaliação | Comparação do mesmo sistema com e sem AES-CTR |
| Escopo excluído | ASIC, rede neural, segunda FPGA e comparação de arquiteturas AES |

AES-CTR será tratado como mecanismo de **confidencialidade**. O protótipo não
fornece autenticação, integridade, proteção contra replay, anti-spoofing GNSS
ou resistência a canais laterais.

## Estado atual — 09/09/2026

Concluído:

- UART v2 revisado, com clock de 50 MHz, 9600 baud e 8N1;
- FIFO síncrona de 1.024 bytes com ocupação, high-water mark e overflow;
- ponte UART RX → FIFO → UART TX, ainda sem criptografia;
- projeto Quartus da ponte para a DE10-Lite e `.sof` gerado;
- núcleo AES-128 iterativo isolado, com onze chaves de rodada armazenadas;
- 866 vetores AES conferidos por uma biblioteca independente, incluindo 284
  casos públicos do NIST;
- lint, checagem estrutural e análise isolada de recursos/timing do AES.

Pendente:

- CTR por byte e controle de nonce/contador;
- controle de sessões e software de configuração/captura do PC;
- integração final com a FIFO e a UART;
- build integrado com e sem criptografia;
- validação física na DE10-Lite e no GPS, caso a placa esteja disponível;
- experimentos, gráficos, redação, submissão e registro do comprovante.

## Cronograma obrigatório

A execução, a escrita, a submissão e a contingência devem terminar em **25/09**.
A versão principal deve ser enviada em 24/09; o dia 25/09 é reservado apenas
para correção pequena, problema do portal, reenvio e confirmação final.

| Período | Frente | Entrega verificável |
| --- | --- | --- |
| 09–10/09 | CTR isolado | RTL do CTR, nonce/contador definidos e vetores oficiais passando |
| 11–12/09 | Adaptador por byte | Máscaras de 16 bytes, backpressure, pausas, reset e blocos parciais testados |
| 13/09 | Integração simulada | Replay NMEA atravessa UART, FIFO, CTR e decifragem no PC |
| 14–15/09 | Sessões e PC | Armamento, nonce por sessão, limite de bytes, captura e comparação byte a byte |
| 16/09 | Quartus integrado | Baseline sem AES e sistema com CTR compilados com restrições equivalentes |
| 17–18/09 | Bancada ou replay | GPS real validado se houver placa; caso contrário, replay controlado documentado |
| 19–20/09 | Experimentos | Três repetições por build e métricas armazenadas em arquivos rastreáveis |
| 21–22/09 | Resultados | Tabelas, gráficos e análise de desempenho concluídos |
| 23/09 | Revisão | Manuscrito completo revisado pelo orientador e comentários incorporados |
| 24/09 | Submissão | Arquivo final enviado e comprovante salvo |
| 25/09 | Contingência | Reenvio/correção final e encerramento do projeto |

A introdução, os trabalhos relacionados e a metodologia devem ser escritos
progressivamente desde o início. Não deixar toda a redação para os dias 23–25.

## Etapas técnicas e critérios de aceite

### 1. CTR isolado — 09–10/09

Usar o AES já validado para gerar a máscara:

```text
mask = AES-128(key, nonce[95:0] || counter[31:0])
ciphertext_byte = plaintext_byte XOR mask_byte
```

Critérios:

- ordem dos bytes documentada no RTL e no software;
- comparação com uma biblioteca independente para comprimentos de 1 a vários
  blocos;
- teste de contador inicial, incremento e último contador permitido;
- bloqueio explícito quando o contador não puder mais ser incrementado;
- nenhum nonce ou chave privada gravado no repositório.

### 2. Adaptador por byte — 11–12/09

O AES opera em blocos de 128 bits, mas a UART entrega um byte por vez. O
adaptador deve manter uma reserva de máscara e consumir cada byte somente quando
o estágio seguinte aceitar a transferência.

Critérios:

- entradas e saídas com `valid/ready` ou contrato equivalente claramente
  documentado;
- pausas do TX não causam perda nem avanço indevido da máscara;
- comprimentos de 1, 15, 16, 17 e sequências longas são decifrados corretamente;
- reset, troca de chave e rearmamento invalidam o estado antigo;
- o baseline sem AES usa a mesma fronteira de medição e o mesmo controle.

### 3. Sessões e software do PC — 13–15/09

Uma sessão deve definir chave de teste, nonce, comprimento esperado e estado de
execução. O controle não pode ser confundido com os bytes cifrados.

Critérios:

- sessão armada antes do início da captura;
- nonce novo para cada sessão com a mesma chave;
- erro de stop, overflow ou reset invalida a sessão;
- o PC salva configuração, captura bruta, ciphertext, texto recuperado e
  metadados do ensaio;
- a comparação é byte a byte e registra a primeira divergência, não apenas um
  valor agregado.

### 4. Build integrado — 16/09

Gerar dois builds comparáveis:

1. `baseline`: UART v2 + FIFO + controle, sem AES elaborado;
2. `secure`: UART v2 + FIFO + controle + AES-CTR.

Os dois devem usar o mesmo dispositivo, clock, restrições, condições de fit e
instrumentação mínima. O projeto isolado `fpga/aes_analysis/` é apenas uma
estimativa preliminar; suas exceções de fronteira não devem ser copiadas para o
build integrado.

Critérios:

- ambos os builds compilam sem erro;
- timing de 50 MHz é atendido ou a violação é registrada e discutida;
- recursos são extraídos do relatório pós-fit;
- a versão RTL, seed e versão do Quartus são registradas.

### 5. Bancada ou replay — 17–18/09

Se a DE10-Lite estiver disponível, testar nesta ordem:

1. programar a ponte sem AES e testar uma fonte serial conhecida;
2. ligar o TX do GPS ao RX da FPGA, com terra comum e níveis compatíveis;
3. confirmar a recepção dos bytes no PC;
4. comparar a saída da ponte com uma captura direta do GPS;
5. programar o build com AES-CTR e repetir a captura;
6. decifrar no PC e comparar com a entrada original.

Se a placa não estiver disponível, executar o mesmo protocolo com arquivos de
replay NMEA e declarar explicitamente que não houve aquisição GPS física. Dados
sintéticos validam o fluxo RTL, mas não substituem a evidência de bancada.

### 6. Experimentos e resultados — 19–22/09

Para cada build, executar três repetições do mesmo replay, preservando tamanho,
ordem e pausas. Se houver hardware, acrescentar uma sessão contínua do GPS e
registrar a duração.

Registrar:

- número de bytes recebidos, transmitidos e recuperados;
- erros de UART, overflow e divergências;
- latência do AES e latência do sistema, com a fronteira de medição explícita;
- throughput do núcleo e taxa efetiva do fluxo serial;
- ocupação máxima da FIFO;
- elementos lógicos, registradores, memória e Fmax pós-fit;
- versão do código, configuração do ensaio e hashes dos arquivos de entrada.

Latência causada por USB, terminal ou sistema operacional deve ser identificada
separadamente da latência interna da FPGA. Potência é opcional e, se estimada,
deve ser apresentada como estimativa do Quartus, não como medição física.

## Organização das contribuições

As tarefas podem ser distribuídas por frentes:

| Frente | Responsabilidade |
| --- | --- |
| Coordenação/integração | manter escopo, resolver conflitos e aceitar entregas |
| RTL criptográfico | CTR, adaptador por byte, sessões e handshakes |
| Verificação | testbenches, oráculo independente, vetores e casos-limite |
| FPGA/Quartus | tops, QSF/SDC, builds baseline/secure e extração de métricas |
| GPS/bancada | conferir carrier, níveis, ligações, captura e logs físicos |
| PC/análise/artigo | protocolo de captura, decifragem, gráficos e manuscrito |

Uma pessoa pode assumir mais de uma frente. O importante é que cada tarefa
tenha um responsável definido no issue ou no pull request.

### Fluxo de Git

- `main` deve permanecer reproduzível e conter apenas entregas revisadas.
- Criar branches curtas: `feature/ctr`, `feature/session`, `test/ctr-vectors`,
  `fpga/integrated-build` ou `docs/results`.
- Um commit deve representar uma mudança coerente e compilável sempre que
  possível. Usar mensagens objetivas, por exemplo:
  `Implement AES-CTR byte adapter`.
- Antes de abrir pull request, executar `git diff --check` e os testes afetados.
- Pull requests devem informar: arquivos alterados, comando executado,
  resultado, limitações e eventual dependência de hardware.
- Não fazer force-push em `main`, não apagar trabalho de outra pessoa e não
  versionar chaves, capturas privadas, coordenadas pessoais ou arquivos em
  `build/`.

## Comandos de verificação

Executar na raiz do repositório:

```bash
make aes       # AES isolado
make check     # regressão completa disponível
make fpga      # ponte para DE10-Lite, sem exigir a placa
make aes-fpga  # análise isolada do AES, sem gerar SOF
git diff --check
```

Uma tarefa RTL só pode ser marcada como concluída quando o testbench relevante
passar e o resultado estiver descrito no pull request ou no relatório em `docs/`.
Uma tarefa de Quartus deve anexar a versão do dispositivo, seed, clock e
relatório utilizado. Uma tarefa de bancada deve registrar ligações, alimentação,
baud rate, duração e qualquer erro observado.

## Definição de concluído em 25/09

O projeto estará encerrado quando:

- o build secure estiver integrado e testado contra o baseline;
- o caminho CTR estiver conferido por software independente;
- todas as métricas e arquivos de entrada estiverem identificados por versão;
- a condição de hardware estiver declarada corretamente — GPS real ou replay;
- o manuscrito estiver revisado e com figuras/tabelas rastreáveis;
- a submissão tiver sido realizada até 24/09;
- qualquer correção ou reenvio tiver sido concluído em 25/09;
- o comprovante e a versão submetida estiverem preservados.

O prazo externo de 30/09 não deve ser usado como justificativa para deixar uma
etapa necessária para depois de 25/09.
