# Plano de execução e colaboração

Atualizado em 15/09/2026. O [cronograma](cronograma.md) registra o andamento e
as evidências; este plano detalha as entregas e como aceitá-las.
A [apresentação](proposta_btsym_gps_fpga.html) reúne proposta, arquitetura,
materiais e datas em quatro telas.

## Objetivo e desenho experimental

Receber dados reais do GPS **NEO-M8N-010**, aplicar AES-128-CTR em hardware e
comparar o custo da cifra em **MAX 10 e Cyclone IV**, com o mesmo RTL.

| Plataforma | Sem cifra | Com cifra | Clock |
| --- | --- | --- | --- |
| DE10-Lite / MAX 10 | UART + FIFO + controle | Mesmo sistema + AES-CTR | 50 MHz |
| Cyclone IV | UART + FIFO + controle | Mesmo sistema + AES-CTR | Oscilador da placa a confirmar |

UART fixa em 9600/8N1, FIFO de 1.024 bytes, AES iterativo próprio e decifragem
independente no PC. AES-CTR oferece confidencialidade, sem autenticação.
A [arquitetura detalhada](arquitetura.md) especifica o fluxo e as fronteiras.

As duas placas permanecem na `main`. O código de UART/FIFO/AES/CTR é único;
cada alvo tem wrapper, QSF/SDC e saídas próprias. Usar branches temporárias para
suporte e integração. Os quatro builds finais ainda serão implementados; o
teste UART e a ponte atual são preparatórios.

## Estado atual

- UART v2, FIFO e ponte sem cifra implementados; ponte compilada para MAX 10.
- AES conferido em 866 vetores e analisado isoladamente no Quartus.
- CTR por byte conferido em 60 fluxos / 19.009 bytes por biblioteca independente.
- UART autônoma para osciloscópio implementada, simulada e compilada.
- Regressão completa: 22 simulações, lint, estrutura e comparação CTR aprovados.
- Sem evidência física registrada; integração, sessões/PC e quatro builds pendentes.
- Cyclone IV aguarda fabricante/modelo, part number, oscilador e pinagem.

Relatórios: [AES](validacao-aes-2026-09-09.md),
[CTR](validacao-ctr-2026-09-10.md) e [revisão de 14/09](revisao-2026-09-14.md).

## Datas e entregas

**Submissão em 24/09. Contingência e encerramento em 25/09.**

| Data | Frente | Entrega verificável |
| --- | --- | --- |
| 15/09 | Bancada UART / placa Cyclone IV | TX medido; RX por jumper; placa e clock identificados |
| 16–17/09 | Integração / PC | Fluxo UART–FIFO–CTR–TX e sessões; replay recuperado corretamente |
| 18/09 | FPGA / Quartus | Quatro builds, relatórios de recursos e auditoria temporal |
| 19–20/09 | Experimentos | Três replays por configuração e ensaio GPS contínuo |
| 21–22/09 | Resultados / manuscrito | Tabelas, gráficos e texto completo |
| 23/09 | Revisão com orientador | Comentários incorporados e versão congelada |
| 24/09 | Submissão | Arquivos enviados e comprovante salvo |
| 25/09 | Contingência | Correções de envio/reenvio e confirmação final |

Introdução, trabalhos relacionados e metodologia avançam junto da implementação.
A integração prevista inicialmente para 13/09 foi reagendada; não está concluída.
Definir colaboradores para RTL, PC e bancada em paralelo. Registrar atrasos e
ajustar as dependências no cronograma sem deslocar entregas necessárias após 25/09.

## 1. UART isolada e identificação da segunda placa — 15/09

Usar `make uart-fpga` e o [guia da UART de bancada](../fpga/de10_lite/uart_scope/README.md).
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

Conectar UART RX → FIFO → retenção de byte → controle → AES-CTR → UART TX.

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

## 3. Sessões e software de PC — 16–17/09

Definir protocolo local de configuração separado do fluxo cifrado. Cada sessão
tem chave de teste, nonce, contador inicial e quantidade N de bytes.

- Armar antes da captura e iniciar no próximo `$`; contar exatamente N bytes.
- Gerar/registrar nonce novo por chave e sessão, inclusive após reset.
- Bloquear ultrapassagem do contador de 32 bits; invalidar a sessão em framing,
  overflow, perda ou reset.
- Separar configuração confiável de bancada de distribuição segura de chaves.
- Capturar referência, ciphertext e texto recuperado; salvar metadados, hashes,
  contagens, primeira divergência e flags de erro.
- Não versionar chaves privadas, sessões reais ou coordenadas pessoais.

Aceite: rearmamento testado, nenhuma reutilização acidental de contexto e
comparação do PC aprovada em fluxo vindo da simulação.

## 4. Quatro builds comparáveis — 18/09

Criar `fpga/<placa>/baseline/` e `fpga/<placa>/secure/`; saídas em
`build/<placa>/<configuracao>/`. Cada projeto seleciona suas fontes e top,
sem precisar excluir outros módulos do repositório.

- Mesmo RTL, FIFO, controle, fronteiras de medida e instrumentação dentro de cada par.
- Remover o AES por elaboração no baseline; não usar apenas um bypass em execução.
- Usar dispositivo, clock e I/O corretos de cada placa.
- Rodar síntese, fit e auditoria de setup/hold/recovery/removal; revisar
  cobertura temporal e exceções de I/O assíncrono.
- Registrar versão Quartus, SHA do RTL, seed, clock e condições dos modelos.
- Extrair LEs, registradores, bits/blocos de memória, Fmax e slacks do pós-fit.
- Não copiar as exceções de portas virtuais do AES isolado para o sistema completo.

Aceite: quatro builds rastreáveis e timing no clock de operação de cada placa.
Se algum falhar, registrar a causa e resolver; não informar sucesso parcial como
matriz concluída.

## 5. GPS real e experimentos — 19–20/09

Após conferir módulo, alimentação e montagem:

1. Validar GPS diretamente e guardar uma referência.
2. Testar o baseline integrado na primeira placa.
3. Executar a sessão com AES e decifrar no PC.
4. Comparar todos os bytes com a referência independente.
5. Repetir o protocolo na Cyclone IV.

Executar três repetições do mesmo replay por configuração, preservando bytes e
intervalos. Acrescentar sessão contínua do GPS com duração registrada; almejar
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
| RTL | Integração, retenção de bytes e controle de sessões |
| Verificação | Oráculo independente, erros, reset e replay |
| FPGA | Wrappers, QSF/SDC, quatro builds e recursos/timing |
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
make aes
make ctr
make aes-fpga
make check
git diff --check
```

## Encerramento em 25/09

Concluir os quatro builds e seus resultados, comparar o fluxo recuperado,
revisar o manuscrito, submeter em 24/09 e guardar o comprovante. O dia 25/09
fica para eventual correção/reenvio e confirmação final. Relatar limitações
de hardware explicitamente, sem transformar planos ou simulação em medições.
