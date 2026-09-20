# Plano de execução e colaboração

Atualizado em 19/09/2026. O [cronograma](cronograma.md) registra o andamento e
as evidências; este plano detalha as entregas e como aceitá-las.
A [apresentação](proposta_btsym_gps_fpga.html) reúne proposta, arquitetura,
materiais e datas em quatro telas.

## Objetivo e desenho experimental

Receber dados reais do GPS **NEO-M8N-010**, aplicar AES-128-CTR em hardware e
comparar o custo da cifra em **MAX 10 e Cyclone IV**, com o mesmo RTL.

| Plataforma | Sem cifra | Com cifra | Clock |
| --- | --- | --- | --- |
| DE10-Lite / MAX 10 | UART + FIFO | Mesmo sistema + AES-CTR | 50 MHz |
| Cyclone IV | UART + FIFO | Mesmo sistema + AES-CTR | Oscilador da placa a confirmar |

UART fixa em 9600/8N1, FIFO de 1.024 bytes, AES iterativo próprio e decifragem
independente no PC. AES-CTR oferece confidencialidade, sem autenticação.
A [arquitetura detalhada](arquitetura.md) especifica o fluxo e as fronteiras.

As duas placas permanecem na `main`. O código de UART/FIFO/AES/CTR é único;
cada alvo tem wrapper, QSF/SDC e saídas próprias. Usar branches temporárias para
suporte e integração. Os dois builds da DE10-Lite já possuem projetos próprios
e foram compilados; os dois builds da Cyclone IV dependem da identificação da
placa.

## Estado atual

- UART v2, FIFO e ponte sem cifra implementados; ponte compilada para MAX 10.
- AES conferido em 866 vetores e analisado isoladamente no Quartus.
- CTR por byte conferido em 60 fluxos / 19.009 bytes por biblioteca independente.
- UART autônoma para osciloscópio implementada, simulada e compilada.
- Integração baseline/secure validada: 4.982 bytes de TX conferidos no PC.
- Gravador/comparador PC testado com porta virtual; ainda sem adaptador físico.
- Regressão completa: 26 simulações, sete configurações de lint, estrutura e 13 testes PC.
- DE10-Lite detectada, `uart_scope` programada, TX medido e loopback TX→RX aprovado.
- Tops baseline/secure da DE10-Lite compilados com recursos e timing registrados.
- Sem GPS físico; geração/registro persistente de contexto no PC concluídos.
- Provisionamento desses parâmetros no wrapper/FPGA e Cyclone IV permanecem pendentes.
- Cyclone IV aguarda fabricante/modelo, part number, oscilador e pinagem.

Relatórios: [AES](validacao-aes-2026-09-09.md),
[CTR](validacao-ctr-2026-09-10.md), [revisão de 14/09](revisao-2026-09-14.md)
e [integração de 16/09](validacao-integracao-2026-09-16.md),
[bancada DE10-Lite de 18/09](bancada-de10-lite-2026-09-18.md).

## Datas e entregas

**Submissão em 24/09. Contingência e encerramento em 25/09.**

| Data | Frente | Entrega verificável |
| --- | --- | --- |
| 16–18/09 | Bancada UART | SOF programado; TX medido e RX por jumper registrados |
| 16–17/09 | Identificação Cyclone IV | Modelo, clock e pinagem confirmados antes de criar o alvo |
| 16/09 | Integração / PC | Concluído em simulação/PTY: fluxo serial e comparação independente |
| 17/09 | Contexto / preparação FPGA | Estrutura do wrapper e contexto de bring-up |
| 18/09 | FPGA / Quartus | Dois builds DE10-Lite, relatórios de recursos e auditoria temporal; Cyclone pendente |
| 19/09 | Contexto / registro no PC | Gerador privado e registro persistente de nonces, com testes de limites; `make check` aprovado |
| 19–20/09 | Experimentos | Três replays por configuração e ensaio GPS contínuo |
| 21–22/09 | Resultados / manuscrito | Tabelas, gráficos e texto completo |
| 23/09 | Revisão com orientador | Comentários incorporados e versão congelada |
| 24/09 | Submissão | Arquivos enviados e comprovante salvo |
| 25/09 | Contingência | Correções de envio/reenvio e confirmação final |

Introdução, trabalhos relacionados e metodologia avançam junto da implementação.
A integração prevista inicialmente para 13/09 foi validada em RTL em 16/09.
A bancada prevista para 15/09 foi reagendada para 18/09; a placa foi
identificada, programada e validada no TX/loopback. Os novos tops integrados
foram então compilados para iniciar a etapa de comparação.
Definir colaboradores para RTL, PC e bancada em paralelo. Registrar atrasos e
ajustar as dependências no cronograma sem deslocar entregas necessárias após 25/09.

## 1. UART isolada e identificação da segunda placa — 16–18/09

`make uart-fpga` e a programação JTAG da UART autônoma foram concluídos em
18/09. `jtagconfig` encontrou a placa correta e `quartus_pgm` confirmou o SOF.
O [relatório de bancada](bancada-de10-lite-2026-09-18.md) contém a evidência
do osciloscópio e do loopback. Usar também o
[guia da UART](../fpga/de10_lite/uart_scope/README.md).
A FPGA gera 0x55 a cada 100 ms; observar TX no osciloscópio. Um jumper externo
TX → RX permite verificar recepção nos LEDs.

Critérios de aceite:

- bit de aproximadamente 104,16 µs e quadro 8N1 de 1,0416 ms;
- níveis elétricos e ordem dos bits conferidos; captura com escalas;
- RX mostra 0x55 após reset/jumper, LED 8 aceso e LED 9 apagado;
- registrar versão, SOF, montagem e resultado; completar com fonte independente
  para testar RX assíncrono.

Não é necessário USB–UART para observar o TX desse gerador. Para comparação de
fluxos no PC, prever dois canais de captura serial: saída da FPGA e referência
GPS; podem usar USB–UART ou microcontrolador com ponte validada.

Na Cyclone IV, preencher [dados do alvo](../fpga/cyclone4/README.md), criar
wrapper/QSF/SDC somente com a identificação confirmada e repetir a verificação
UART. A compilação de exemplo usada na instalação do pacote não define essa placa.

## 2. Integração do fluxo por byte — 16–17/09

Concluída em simulação em 16/09 no `uart_ctr_bridge`; ver
[contrato e evidências](integracao-uart-ctr.md). O caminho implementado é
UART RX → FIFO → retenção de byte → estágio selecionado → UART TX.

- Reservar espaço antes de solicitar a leitura síncrona da FIFO.
- Reter `rd_data` e flag válida até o handshake; não perder a resposta de um ciclo.
- Consumir máscara apenas quando o TX/estágio seguinte aceitar o byte.
- Garantir reset/abort sem bytes antigos, incluindo um TX já em andamento.
- Testar comprimentos 1, 15, 16, 17, 255 e superiores à profundidade da FIFO,
  pausas, overflow, stop inválido e cancelamento.
- Usar uma fonte/decodificador serial independente; decifrar a saída efetiva do
  testbench no PC e comparar byte a byte.

Aceite: regressão completa aprovada e replay serial recuperado sem divergências.
O AES isolado, CTR isolado e ponte separados não comprovam essa integração.

## 3. Captura e software de PC — 16–19/09

Gravador binário e comparador implementados; uso em [captura PC](captura-pc.md).
Os testes de software e a comparação da saída serial simulada foram aprovados.
`scripts/context.py` agora cria contextos privados baseline/AES-CTR, gera nonce
quando necessário e mantém um registro que rejeita o mesmo nonce com a mesma
chave. O wrapper de bring-up já carrega um contexto fixo;
isso não substitui o provisionamento para a captura GPS. A validação
do adaptador físico depende de bancada; PTY não representa esse dispositivo.

Definir o procedimento de captura separado do fluxo cifrado. Cada ensaio terá
chave de teste, nonce, contador inicial e quantidade N de bytes registradas no PC.

- Iniciar a captura antes do replay e contar exatamente N bytes no PC.
- Gerar/registrar nonce novo por captura, inclusive após reset; o registro no PC
  já bloqueia a reutilização do par chave/nonce.
- Bloquear ultrapassagem do contador de 32 bits; invalidar a captura em framing,
  overflow, perda ou reset.
- Manter os parâmetros de bancada separados dos dados cifrados.
- Capturar referência, ciphertext e texto recuperado; salvar metadados, hashes,
  contagens, primeira divergência e flags de erro.
- Não versionar chaves privadas, capturas reais ou coordenadas pessoais.

Aceite: nenhuma reutilização acidental de contexto e comparação do PC aprovada
em fluxo vindo da simulação. O primeiro critério foi coberto pelos testes do
gerador; o envio do contexto à FPGA ainda depende do wrapper de bancada.

## 4. Builds comparáveis — DE10-Lite em 18/09; Cyclone IV pendente

Os projetos seguem `fpga/<placa>/baseline/` e `fpga/<placa>/secure/`; saídas em
`build/<placa>/<configuracao>/`. Cada projeto seleciona suas fontes e top,
sem precisar excluir outros módulos do repositório.

- Mesmo RTL, FIFO, interfaces, fronteiras de medida e instrumentação dentro de cada par.
- Remover o AES por elaboração no baseline; não usar apenas um bypass em execução.
- Usar dispositivo, clock e I/O corretos de cada placa.
- Rodar síntese, fit e auditoria de setup/hold/recovery/removal; revisar
  cobertura temporal e exceções de I/O assíncrono.
- Registrar versão Quartus, SHA do RTL, seed, clock e condições dos modelos.
- Extrair LEs, registradores, bits/blocos de memória, Fmax e slacks do pós-fit.
- Não copiar as exceções de portas virtuais do AES isolado para o sistema completo.

Resultado DE10-Lite: baseline e secure compilados, com timing positivo. O
baseline usou 342 LE/215 registradores/8.192 bits de memória e Fmax mínima de
132,61 MHz; o secure usou 6.984 LE/2.196 registradores/8.192 bits e Fmax mínima
de 82,19 MHz. Os dois operam a 50 MHz sem violação. A matriz completa continua
pendente até confirmar a Cyclone IV; não apresentar esse resultado parcial como
quatro builds concluídos.

## 5. GPS real e experimentos — 19–20/09

Após conferir módulo, alimentação e montagem:

1. Validar GPS diretamente e guardar uma referência.
2. Testar o baseline integrado na primeira placa.
3. Executar a captura com AES e decifrar no PC.
4. Comparar todos os bytes com a referência independente.
5. Repetir o protocolo na Cyclone IV.

Executar três repetições do mesmo replay por configuração, preservando bytes e
intervalos. Acrescentar captura contínua do GPS com duração registrada; almejar
uma hora por configuração quando a bancada permitir. Se houver impedimento
físico, registrá-lo e revisar o experimento com o orientador; replay sintético
não é aquisição GPS real.

Registrar perdas, framing, overflow, latência e ocupação máxima da FIFO. Uma
forma de onda correta é evidência temporal/elétrica; não prova ausência de
perdas em uma aquisição longa. Um eco visual no terminal também não substitui
a comparação automática de todos os bytes.

## 6. Resultados e escrita — 21–23/09

Comparar primeiro o acréscimo `secure − baseline` em cada FPGA; depois,
discutir diferenças entre plataformas.

- Latência em ciclos **e** µs, identificando o clock de cada placa.
- Taxa útil UART separada do throughput AES; 9600/8N1 tem teto nominal de
  960 bytes/s por direção antes de pausas e overhead.
- Recursos absolutos e percentuais; não somar LEs e registradores.
- Fmax estimada separada do clock de operação e de medidas de bancada.
- Potência opcional, estimada com atividade e condições documentadas; não
  usar estimativas genéricas para concluir eficiência energética entre famílias.
- Builds SignalTap separados das medições oficiais de recursos.

Aceite: tabelas/figuras rastreáveis, metodologia reproduzível e texto revisado
pelo orientador em 23/09. Não declarar nova cifra nem garantir segurança além
da confidencialidade implementada.

## Colaboração e Git

| Frente | Entrega |
| --- | --- |
| Coordenação | Manter cronograma, dependências e decisões com o orientador |
| RTL | Integração, retenção de bytes e controle de fluxo |
| Verificação | Oráculo independente, erros, reset e replay |
| FPGA | Wrappers, QSF/SDC, builds e recursos/timing |
| Bancada | UART no osciloscópio, placa Cyclone IV e GPS real |
| PC/artigo | Captura, decifragem, métricas e manuscrito |

Definir responsáveis em issues/PRs. Uma pessoa pode assumir mais de uma frente.

Antes de cada entrega, revisar o diff e executar os testes afetados. Para RTL,
rodar `make check`. Seguir [AGENTS.md](../AGENTS.md) para fetch/pull e revisar
todo o intervalo recebido antes de continuar. Não fazer force-push nem
sobrescrever alterações de outro colaborador.

Atualizar cronograma, plano, README e HTML na mesma entrega quando mudarem
datas ou arquitetura. Preservar relatórios históricos; gerar novos manifestos
para novas fontes/resultados. `build/` permanece local e ignorado pelo Git.

## Comandos

```bash
make uart          # RX/TX e teste de bancada
make uart-waves    # VCD dos sinais públicos
make uart-fpga     # SOF UART autônoma DE10-Lite
make fpga          # ponte UART + FIFO DE10-Lite
make baseline-fpga # build integrado sem AES na DE10-Lite
make secure-fpga   # build integrado com AES-128-CTR na DE10-Lite
make aes
make ctr
make integration
make pc
make context
make aes-fpga
make check
git diff --check
```

## Encerramento em 25/09

Concluir os builds disponíveis e seus resultados, comparar o fluxo recuperado,
revisar o manuscrito, submeter em 24/09 e guardar o comprovante. O dia 25/09
fica para eventual correção/reenvio e confirmação final. Relatar limitações
de hardware explicitamente, sem transformar planos ou simulação em medições.
