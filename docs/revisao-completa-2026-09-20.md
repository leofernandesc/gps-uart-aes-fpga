# Revisão técnica — 20/09/2026

## Conclusão

O caminho UART → FIFO → AES-CTR → UART está funcional nos testes disponíveis.
A separação entre RTL compartilhado, wrappers de placa, ensaios e ferramentas
do PC é adequada. Ainda há trabalho de implementação e metodologia sem placa:
o secure atual não coube no EP4CE6E22C8 em uma compilação exploratória, a medição
publicada de latência inclui pausas artificiais e o procedimento de captura
precisa controlar alinhamento e reutilização de contexto após reset.

As quatro configurações continuam obrigatórias: baseline e secure em MAX 10
e Cyclone IV. A comparação não pode ser encerrada apenas com a DE10-Lite.
Submissão em 24/09 e contingência até 25/09 permanecem as metas, agora em risco.

Esta entrega é uma revisão, não uma correção do RTL. Os ensaios adicionais
ficaram em `build/review-2026-09-20/`, sem programação de placa. Os documentos
de andamento foram atualizados; as correções funcionais abaixo estão pendentes.

## Verificações executadas

- Fontes avaliadas: `bed7218bca9bc9bbc83c92abd4ee047f74da44b6`. Remoto consultado
  por `git fetch origin`; não foi necessário fazer pull.
- `make check`: código 0, 27 simulações, nove configurações de lint, verificações
  estruturais e 19 testes PC aprovados. A documentação anterior contava sete
  configurações de lint e omitia o teste do wrapper na decomposição das simulações.
- AES: 866 vetores independentes; CTR: 60 fluxos / 19.009 bytes recuperados.
- Integração: por variante, 2.681 bytes no ensaio acelerado e 49 no ensaio
  regular a 50 MHz/9600; nenhuma divergência. O replay dedicado de 309 bytes
  não foi reexecutado nesta revisão; seu testbench e as evidências anteriores
  foram examinados.
- Relatórios reais MAX 10 conferidos: baseline 342 LE / 215 registradores,
  secure 6.984 LE / 2.196 registradores; timing positivo nos três cantos.
- Diagnósticos adicionais reproduziram a aceitação de timing inválido pelo
  extrator, limitações do validador NMEA, a reutilização de máscara após reset
  e a diferença entre latência nominal e latência com pausa.

## Achados prioritários

### 1. Bloqueante para o artigo: secure não cabe atualmente no EP4CE6E22C8

O alvo foi identificado como Cyclone IV E **EP4CE6E22C8**. O dispositivo tem
6.272 LEs, 270 Kbits de RAM, 15 multiplicadores 18 × 18 e duas PLLs. `E22`
identifica EQFP de 144 pinos; `C8`, faixa comercial e speed grade 8.
[Manual oficial, tabelas 1–1/1–3 e figura 1–3](https://docs.altera.com/api/khub/documents/8ZIWxPYpX_ESk1aWBAaflA/content).

Foi elaborado o top secure existente para esse dispositivo, com o contexto
público, sem editar fontes. `quartus_map` terminou; `quartus_fit` retornou 3:

```text
Total logic elements : 7,735 / 6,272 (123%)
Total combinational functions : 6,520 / 6,272 (104%)
Error (170011): Design contains 6520 blocks of type combinational node.
However, the device contains only 6272 blocks.
Error (171000): Can't fit design in device
```

Evidência local: `build/review-2026-09-20/cyclone4-probe/output_files/`.
Esse ensaio é somente de capacidade: manteve os parâmetros do wrapper MAX 10,
não possui pinagem de bancada nem SDC validado e não gerou SOF. Não fornece
Fmax ou validação a 48 MHz. O erro de capacidade é explícito; uma futura
otimização pode mudar o resultado, portanto não significa impossibilidade de
usar AES nessa FPGA.

Recomendação: reduzir área no AES compartilhado, avaliar o armazenamento das
onze chaves e o paralelismo das S-boxes, preservando a interface e os vetores
de referência. Recompilar ambos os alvos após qualquer mudança. O FIFO já usa
RAM; reduzi-lo não é a primeira hipótese para resolver o custo dominante.
Ver `rtl/aes/aes128_core.sv:26` e `rtl/aes/aes128_core.sv:35`.

### 2. Alta: a latência do manuscrito inclui bloqueio artificial do TX

Em `tb/uart_ctr_bridge_tb.sv:207`, o TX é desabilitado antes dos primeiros
três bytes; há outra pausa no nono byte. Isso também ocorre no modo
`GPS_ONLY`. Os 169.269 ciclos / 3,385 ms e a ocupação máxima de dois bytes
são resultados desse estímulo com pausas, não uma medição limpa do custo
normal de encaminhamento ou da inclusão do AES.

Além disso, `rx_event` indica byte recebido e `tx_event` indica **fim** da
transmissão; não são duas bordas de início de quadro. As fronteiras precisam
ser explícitas no artigo.

Um diagnóstico separado, sem pausas e com máscara já preparada, mediu nos dois
modos: byte válido RX → início TX = 80 ns; byte válido RX → fim TX =
1.041.680 ns. Evidência: `build/review-2026-09-20/latency_reset_probe.log`.
São duas transferências curtas de diagnóstico, não resultados substitutos
para todo o workload GPS. Separar ensaio nominal, inicialização e teste de
backpressure; depois regenerar as tabelas dos dois manuscritos.

### 3. Alta: o reset recarrega o mesmo contexto CTR

`fpga/de10_lite/common/de10_lite_uart_ctr_top.sv:52` recarrega a mesma chave,
nonce e contador a cada KEY0. O registro do PC bloqueia a criação de outro
JSON com o mesmo par, mas não observa resets nem impede reutilização do SOF.

O diagnóstico enviou `55`, recebeu `e2`, resetou e enviou `aa`, recebendo `1d`.
Os dois pares usam a máscara `b7`. É o comportamento esperado do contexto
estático de bring-up, mas não pode ser apresentado como prevenção operacional
de reutilização. Em CTR, o bloco nonce/contador precisa ser único por chave
entre mensagens. [NIST SP 800-38A, apêndice B](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38a.pdf).

Para os experimentos reais, documentar e testar um início controlado, contexto
novo efetivamente aplicado e invalidação de reset. Não voltar a alimentar o
mesmo SOF com dados novos depois de resetar. Provisionamento estático pode
continuar sendo uma limitação explícita do protótipo; o teste não exige trocar
CTR por outro algoritmo, nem redesenhar toda a arquitetura.

### 4. Alta: o extrator pode publicar métricas de um build reprovado

`scripts/fpga_metrics.py:23` reconhece apenas valores positivos de slack. A
rotina também não exige conclusão aprovada do build/auditoria nem cobertura
completa de verificações em cada canto.

Em cópias temporárias dos relatórios reais, foi inserido setup = −0,125 ns,
com status FAIL. `collect()` aceitou os arquivos e informou +8,698 ns como
pior setup. Os relatórios reais continuam positivos; não foram adulterados.

Corrigir parsing de valores com sinal, exigir todos os cantos/checks, rejeitar
falha/relatório incompleto e adicionar testes negativos. Associar métricas ao
commit, configuração, seed e hashes dos artefatos antes da tabela definitiva.
Reprodução local: `python3 build/review-2026-09-20/probe_checks.py`.

### 5. Alta para a bancada: falta fechar a janela de aquisição do GPS real

`scripts/capture.py:89` limpa a porta e cada gravador começa separadamente.
O comparador assume que o primeiro byte recebido usa o contador inicial.
Um GPS já transmitindo continuamente não garante esse alinhamento.

Há também incompatibilidade entre capturar N bytes arbitrários e exigir que
o último byte seja o fim de uma sentença NMEA completa. Isso pode rejeitar
uma aquisição elétrica correta apenas por sua janela terminar no meio da linha.

Fechar e ensaiar a sequência: fonte inicialmente inativa, FPGA com contexto
correto, ambos os gravadores READY, liberação da fonte e N bytes identificados.
Para captura contínua, preservar os bytes brutos e os offsets; validar sentenças
completas internas sem descartar bytes silenciosamente nem deslocar o CTR.
Dois adaptadores facilitam a observação, mas não sincronizam o início por si só.

### 6. Média: o validador NMEA aceita dados formalmente inválidos

`scripts/gps_fixture.py:13` aceita `$*00\r\n` e até uma linha contendo NUL com
checksum correspondente. A checagem ASCII não restringe o corpo a caracteres
imprimíveis nem valida o identificador da sentença. Também aceita 84 bytes
incluindo CRLF apesar de declarar limite de 82.

Definir o subconjunto esperado e testar cabeçalho, caracteres, checksum e
fronteiras de comprimento. O receptor tem opção `Limit82`; o perfil/configuração
real deve ser registrado, sem assumir que toda saída u-blox respeita esse
limite por padrão. [Manual u-blox M8, configuração NMEA](https://content.u-blox.com/sites/default/files/products/documents/u-blox8-M8_ReceiverDescrProtSpec_UBX-13003221.pdf).
Isso é validação no PC, não justificativa para acrescentar parser NMEA no RTL.

### 7. Média: parte da observabilidade e da evidência do artigo ainda falta

- O wrapper expõe no LED 9 somente ocupação >= 512 ou esgotamento do contador,
  não o máximo numérico da FIFO. Se a tabela física exigir esse máximo, definir
  como medi-lo. Instrumentação extra precisa ser equivalente dentro de cada par.
- `scripts/manuscript_check.py:46` procura substrings fixas, não comprova que as
  métricas estejam atuais ou que a validação física esteja pendente. Um texto
  artificial com os marcadores e a afirmação de conclusão física passou no teste.
- Os rascunhos EN/PT ainda precisam de trabalhos relacionados, referências
  científicas externas, resultados das quatro configurações e evidência física.
  Referências internas de reprodução não substituem bibliografia científica.
- Recursos pós-fit, Fmax, ciclos do AES, latência e taxa útil são métricas
  diferentes. Comparar ciclos e tempo real entre clocks distintos; não usar
  tempo de chegada USB como latência da FPGA nem Fmax como clock aplicado.
- O plano HTML estava em 18/09; README/plano ainda não identificavam o EP4CE6.
  O andamento foi atualizado nesta entrega, sem marcar bancada como concluída.

## Decisões técnicas que devem ser preservadas

| Área | Avaliação |
| --- | --- |
| `rtl/uart` | Contadores no clock do sistema, RX sincronizado e amostragem central; não precisa criar outro domínio de clock para 9600 baud. |
| `rtl/common` | FIFO com leitura síncrona e retenção explícita da resposta; reset com liberação sincronizada. |
| `rtl/aes`, `rtl/ctr` | Núcleo forward, máscaras pré-calculadas, avanço por handshake e bloqueio de wrap; boa cobertura funcional, área a reduzir. |
| `rtl/bridge` | `uart_ctr_bridge` é o sistema comparável baseline/secure; `uart_bridge` permanece útil como ensaio intermediário/histórico. |
| `fpga` | Wrappers/QSF/SDC por placa; uma base RTL. DE10-Nano/Cyclone V é auxiliar, não substitui a Cyclone IV. |
| `tb`, `reference` | Oráculos independentes e referências imutáveis são pontos fortes; acrescentar testes dos defeitos encontrados. |
| `scripts` | Captura binária, arquivos privados, não sobrescrita e comparação independente adequados; falta robustez nas métricas e na aquisição real. |
| `docs`, `build` | Separação entre evidência versionada e saídas locais adequada; registrar revisão/hash da fonte junto dos novos resultados. |

## Bancada: CP2102 e clock

O host operacional é um único adaptador USB–UART CP2102 em full-duplex. Ele
transmite o vetor conhecido ou um replay e captura a saída da FPGA. Para GPS,
primeiro registra-se a referência direta e depois reapresenta-se o mesmo arquivo
à FPGA; assim a comparação não mistura duas sequências GPS diferentes. Um único
adaptador não observa duas entradas independentes simultaneamente, mas isso não
é requisito do protocolo atual.

O CP2102 suporta 9600/8N1; a faixa oficial começa em 300 bps, não 300 Kbps.
Os pinos 3,3 V/5 V são alimentação: confirmar o nível lógico de TX/RX do módulo.
Usar GND comum; manter os pinos de alimentação desconectados da FPGA já alimentada.
[Datasheet CP2102](https://www.silabs.com/documents/public/data-sheets/CP2102-9.pdf).

Os 48 MHz são uma hipótese para o oscilador da placa Cyclone IV, não uma
especificação do part number. Confirmar modelo/esquema ou foto legível do
oscilador e pino correspondente. Se confirmado: divisor UART = 5.000 ciclos
por bit e período do clock SDC = 20,833333 ns. DE10-Lite continua em 50 MHz.

## Ordem de execução recomendada

1. Reduzir área do AES comum e repetir o fit exploratório no EP4CE6; confirmar
   oscilador, esquema, bancos e pinagem enquanto isso.
2. Corrigir a metodologia de latência, extrator e validador; fechar o procedimento
   de contexto/reset/início de captura e acrescentar testes de regressão.
3. Criar os alvos reais Cyclone IV e recompilar os quatro builds com a mesma
   revisão do RTL; recursos de antes da otimização não são a comparação final.
4. Validar os adaptadores, executar baseline/secure com replay e GPS real nas
   duas placas, registrando repetições, flags e arquivos privados.
5. Consolidar resultados e bibliografia em paralelo; revisão em 23/09, envio em
   24/09 e contingência em 25/09. Se área ou bancada não fecharem a tempo,
   reavaliar o prazo com o orientador, sem retirar a segunda plataforma por conta própria.
