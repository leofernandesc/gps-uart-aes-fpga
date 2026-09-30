# Cronograma revisto — NEO-M8N e DE10-Lite — setembro de 2026

Objetivo ativo: adquirir dados do u-blox NEO-M8N por UART e avaliar o
custo do AES-128-CTR na DE10-Lite/MAX 10, comparando baseline e secure.
Submissão BTSym’26: até 30/09/2026.

## Decisões e estado em 30/09/2026

- GPS: **u-blox NEO-M8N**; o modelo será referido assim no artigo e no projeto.
- Plataforma do experimento: **somente DE10-Lite**, clock de 50 MHz. Cyclone IV
  foi abandonada; os registros antigos permanecem como histórico, não como
  parte da metodologia ou do artigo.
- UART do projeto e do NEO-M8N: **38400/8N1**. RTL, host e testbenches foram
  atualizados; o perfil do receptor foi confirmado após ciclo de energia.
  `make check` passou e
  `make integration-gps` processou os 309 bytes nas duas variantes a 50 MHz:
  FIFO máxima de 1 byte, 80 ns de RX válido até início do TX e 260.480 ns até
  fim do quadro TX. Baseline e secure também passaram no Quartus e nos três
  cantos temporais. Recursos: 331/5.603 LE, 212/913 registradores e Fmax mínima
  117,56/103,38 MHz. O SOF baseline foi programado às 17:44 e usado no P03;
  o SOF secure foi programado e o P05 repetido com contexto novo: 20/20 bytes
  foram cifrados e recuperados exatamente no PC. O P06 também passou: cinco
  bytes cifrados foram recuperados no PC e decodificados no AD2 em RX/TX. O
  `uart_scope` de bancada foi programado para o P01.
- **P01 físico a 38400: concluído**. Além das duas capturas iniciais, o workspace
  AD2 mais recente guarda dez aquisições em modo Repeated; cada uma decodifica
  `0x55`, com período médio de bit de 26,039 µs (38.402,85 baud). Os horários
  dos buffers dão nove intervalos entre quadros, média de 99,33 ms (93–107 ms),
  consistente com a cadência configurada de 100 ms. O arquivo salvo mostra
  trigger em Channel 1 embora C1 esteja desligado e C2 ligado; manter essa
  ressalva e selecionar CH2 nos próximos ensaios.
- **P02 físico a 38400: concluído**. Dez buffers AD2 decodificam `0x55`, com
  bit time médio de 26,040 µs e intervalo médio de 99,56 ms (94–107 ms). A
  captura usa um canal, suficiente para observar a linha comum TX↔RX conectada
  pelo jumper. Na verificação visual, LEDR8 (RX válido) acendeu e LEDR9 (erro)
  permaneceu apagado, confirmando o loopback. **P03 baseline: eco CP2102
  aprovado, 20/20 bytes em quatro transações. P04: captura completa de cinco
  bytes em RX/TX, bit time ~26,0 µs, aprovada na DE10-Lite. P05 secure: 20/20
  bytes cifrados, sem perdas, e recuperação CTR exata no PC. P06 secure no AD2
  também está concluído; a aquisição GPS direta foi validada em P07.** Os testes independentes do
  algoritmo AES não dependem do baud e não precisam ser repetidos isoladamente;
  `make check` já foi reexecutado após a atualização.
- O breakout do GPS é alimentado a 3,3 V. Antes da conexão com a FPGA, manter
  GND comum e confirmar que TX/RX permanecem em níveis compatíveis com a placa.
- **Integração GPS:** P07 validou sentenças NMEA na captura direta e na saída
  física do baseline da DE10-Lite. P08 concluiu os 3 replays baseline com
  comparação byte a byte; P09 secure também passou com recuperação exata de
  4.096 bytes. Em P10, os replays baseline e secure passaram com 32.768 bytes da
  referência GPS armazenada; no modo secure o plaintext foi recuperado
  exatamente. O GPS ficou desconectado durante os replays. Restam registrar os
  indicadores físicos de erro/overflow e executar reset e recuperação (P11).

| Data | Etapa | Situação / entrega exigida |
| --- | --- | --- |
| 29/09 | RTL/host e regressão a 38400 | **Concluído** — `make check`, 37 testes Python; replay NMEA em 50 MHz aprovado nos dois modos |
| 29/09 | Builds e métricas Quartus baseline/secure | **Concluído** — ambos os fits e auditorias temporais PASS; ver `metricas-fpga-2026-09-29.md` |
| 29/09 | P01, UART autônoma a 38400 | **Concluído** — dez quadros `0x55`; intervalos dos buffers AD2: média 99,33 ms (93–107 ms), trigger a corrigir nos próximos ensaios |
| 29/09 | P02, loopback UART a 38400 | **Concluído** — 10/10 quadros `0x55` e temporização no AD2; LEDR8 RX válido aceso, LEDR9 erro apagado |
| 29/09 | P03/P04 baseline a 38400 | **Concluído na DE10-Lite** — P03 eco 20/20; P04 decodifica os cinco bytes em RX e TX, bit time ~26,0 µs, janela AD2 10,239 ms |
| 29/09 | P05 secure a 38400 | **Concluído** — reteste 4/4 transações, 20/20 bytes cifrados e recuperados; relatório privado `p05-secure-20b-38400-report-02.json` |
| 29/09 | P06 secure no AD2 | **Concluído** — CP2102 5/5 e decifragem exata; captura AD2 decodifica entrada e ciphertext em V10/W10 |
| 29–30/09 | P07–P10 GPS e replays | **P07 aprovado** — aquisição e saída baseline com NMEA válido; **P08 3/3** e **P09 secure** aprovados em 4.096 bytes; **P10 baseline e secure aprovados** em 32.768 bytes, sem perda/divergência e com recuperação CTR exata. Referência GPS pré-capturada; GPS desconectado durante os replays. Faltam indicadores físicos de erro/overflow e reset/recuperação (P11) |
| 30/09 | Atualizar resultados, revisar manuscritos e submeter | Até a deadline; manter evidências e comprovante |

**P05 — reteste secure, 29/09/2026 às 18:32 (Manaus):** após programar
`build/de10_lite/secure/uart_secure.sof`, o CP2102 enviou quatro vezes
`55 A5 00 FF 3C`; a FPGA devolveu 20/20 bytes de ciphertext, sem perdas,
extras ou timeout. A recuperação CTR no PC coincide byte a byte com a
referência (SHA-256 `1ec8f144575a9c265334dfa2c385532741170ab730f39f5e38a9fae7f8517e5d`).
O ciphertext tem SHA-256
`594d430e1a9e09a58cf6ff0e4a7f1f342a3ef1bb1b05a32a7e6823645793ad59`.
Relatório privado: `data/private/de10-2026-09-29/p05-secure-20b-38400-report-02.json`.
O ensaio anterior que retornou texto claro permanece registrado como tentativa
reprovada e foi supersedido por este reteste aprovado. Os 0,260 s de host
incluem Linux/USB e não medem latência isolada da FPGA.

**P06 secure, 29/09/2026 às 19:03 (Manaus): PASS.** Com contexto AES-CTR
privado novo de 5 bytes e SOF compilado/auditado, o CP2102 enviou
`55 A5 00 FF 3C`; a DE10-Lite devolveu `14 D8 F4 3D 63`. O relatório registra
5/5 bytes, sem timeout, perda, extra ou divergência, e recuperação exata do
vetor original. SHA-256 do ciphertext:
`e80f629d07586546353b05aa1d678916257dbc245442fb6f1e0bd554fca9e8e0`.
Relatório e bytes recebidos permanecem em `data/private/de10-2026-09-29/`.

A captura do AD2 foi feita em dois canais, 800 kS/s, 8.192 amostras (10,239 ms),
escala 1 V/div, offset 0 V e trigger de descida CH1 em 1,5 V. Com CH1→V10/RX e
CH2→W10/TX, a decodificação independente encontrou os mesmos cinco bytes de
entrada e os cinco bytes de ciphertext, com stop bits válidos. O período de bit
estimado foi ~26,00 µs no CH1 e ~26,04 µs no CH2; os níveis amostrados ficaram
próximos de 0–3,4 V. A associação física dos canais decorre da montagem, pois o
CSV não grava nomes de pinos FPGA.

Capturas arquivadas no repositório: [CSV do AD2](evidence/de10-lite-m9-p06-secure-ad2-2026-09-29.csv)
e [workspace WaveForms](evidence/de10-lite-m9-p06-secure-ad2-2026-09-29.dwf3work).
SHA-256: CSV `cf33576897ec8a0db90663b26f8672ca95d05b13f33d307ac5b29a3eb2a74300`;
workspace `87192a501969b109b35ec28d4c8bd7c88e1df370c8267d8a7ebb44b1adb0bf21`;
relatório privado `b9e3da3deacb63f67d181e1380cd034212792e96c84cf2d2b4583af2b9f699ef`.
O início do TX ocorreu cerca de 247,5 µs após o início do primeiro quadro RX;
isso inclui a recepção serial do byte e não é latência isolada de AES. O tempo
de 68,98 ms no relatório é do caminho host/Linux/USB e também não mede a
latência interna da FPGA. Próxima etapa: executar P07, validando a captura e a
entrada física direta do NEO-M8N na DE10-Lite.

O plano anterior de duas placas/M8 e o freeze de 25/09 foram supersedidos.
Detalhes datados abaixo são registros históricos, não requisitos atuais.

## Situação em 29/09/2026

**Retomada do P04 em 29/09, 07:40 (Manaus):** a montagem foi refeita no
arranjo padrão CP2102 + AD2, sem GPS nem DIO0; o baseline `uart_baseline.sof`
foi programado no MAX 10 `10M50DAF484@1`, JTAG ID `0x031050DD`, checksum
`0x002A0029`, sem erros/avisos. O SOF tem SHA-256
`f878f884b264c2f02a4d720c6ef3120f85ed88c3b52c3f87da7421c90437161c`. O
USB-Blaster e o AD2 são enumerados. O usuário conectou o CP2102 e o kernel
reconheceu `10c4:ea60`/driver `cp210x`, com `ttyUSB0` em sysfs; porém o nó
`/dev/ttyUSB0` não está exposto à sessão isolada do teste (`pyserial: no ports
found`). Nenhum byte foi enviado nesta retomada e P04 não foi executado. A
tentativa de abrir WaveForms pela sessão de ferramentas falhou por falta de
acesso ao display gráfico; o AD2 está livre. É necessário executar o host
serial e abrir WaveForms na sessão gráfica do Ubuntu para continuar a captura.

**Captura passiva do P04 em 29/09, 11:51 (Manaus):** foram salvos
`~/CapturasWaveForms/TesteP04semocp2102.csv` e o workspace WaveForms
`TesteP04semocp2102.dwf3work`. O CP2102 estava conectado, mas não houve envio
de bytes durante a aquisição. O CSV contém 8.192 amostras/canal a 662.252
amostras/s (12,368 ms; aproximadamente 69 amostras por bit a 9.600 baud).
Canal 1: 3,2903–3,2978 V; canal 2: 3,3234–3,3325 V; nenhum canal cruzou
1,65 V ou caiu abaixo de 1,5 V. Assumindo a montagem P04 usual (CH1 em RX/V10,
CH2 em TX/W10), ambos ficaram em repouso alto, comportamento esperado sem
tráfego serial. Como o CSV identifica apenas “Channel 1/2” e não registra onde
as pontas estavam conectadas, essa associação depende da montagem física. É
uma evidência de repouso, não uma validação do caminho RX→TX: P04 continua
pendente até capturar quadros durante estímulo do CP2102. SHA-256: CSV
`bae3ab4c8f301298a50480bea1418e864a8e02009f1a66174348be292c1c9ef1`; workspace
`6adf28241ede7fa3f2be64cec5e1587b65a1804eff84ec25bb2a3fbb142e6f70`.

**Ensaio ativo do baseline em 29/09, 12:05 (Manaus):** `serial_bench.py`
abriu `/dev/ttyUSB0` e escreveu o vetor `55 A5 00 FF 3C` em 9600/8N1 (5
bytes, uma tentativa). Não houve retorno: 0/5 bytes em 1,0004 s, timeout,
sem bytes extras; o arquivo recebido ficou vazio. Relatório privado:
`data/private/de10-2026-09-29/p04-baseline-5b-report.json`, contexto
`context_id=1b2f05f338ef4758a8180201a9a219cb`; SHA-256 do relatório
`43383bac09d3b1c3a812cff80882969a5b510357cd815e046af46a1323deabd7`.
O `tx_bytes=5` confirma que o programa entregou os bytes à porta serial do
host, mas não comprova transições elétricas no TXD/V10. Sem captura simultânea
do AD2 nem estado dos LEDs deste envio, ainda não se sabe se a FPGA recebeu o
quadro. P04 segue reprovado nesta tentativa e sem causa isolada; não alterar o
RTL com base apenas neste timeout.

**Repetição e captura posterior em 29/09, 12:14 (Manaus):** o segundo
relatório também registra envio do vetor `55 A5 00 FF 3C` e retorno 0/5 após
timeout de 1,001 s (sem extras). Entretanto, o CSV WaveForms tem timestamp
12:14:56.532, enquanto a transação terminou aproximadamente às 12:14:26.723;
portanto, a captura começou cerca de 29,8 s depois do envio e não cobre o burst.
Ela contém 8.192 amostras a 543.478 amostras/s por 15,071 ms: CH1=3,2883–3,2961 V
e CH2=3,3220–3,3310 V, sem níveis abaixo de 1,5 V nem transições no limiar de
1,65 V. Isso mostra as linhas em repouso depois do teste, não que TXD/V10
tenham permanecido altos durante a transmissão. O trigger salvo está em borda
de subida a 0 V; para a próxima tentativa, armar Single antes do envio, com
trigger de descida em torno de 1,65 V e janela de 15–20 ms. Os arquivos
`TesteP04semocp2102.csv` e `.dwf3work` foram atualizados; hashes atuais:
CSV `7ad28b8a616674ddcdde6a4b876d618644959b6c0da1feacb4cdb79292cccc39`, DWF
`ebffb566df252dd0f929604ee4d2b10969a8bc07ff775a0b4b7d5e3527f34a02`.
P04 continua sem captura elétrica simultânea e sem causa isolada.

**Terceira tentativa em 29/09, 12:20 (Manaus):** o relatório
`data/private/de10-2026-09-29/p04-baseline-5b-report-03.json` registra o
mesmo vetor e 0/5 bytes recebidos, com timeout de 1,0005 s; o arquivo recebido
está vazio. SHA-256 do relatório:
`7b1a93309cdc55e1821f63765287d892163cbe4e399f87937acc4aaa3cfeb10f`.
Não há novo CSV de captura associado a essa tentativa; o Single não mostrou
traço ao usuário. O resultado ainda não localiza a falha elétrica.

**Quarta tentativa em 29/09, 12:26 (Manaus):** o relatório
`data/private/de10-2026-09-29/p04-baseline-5b-report-04.json` registra o
mesmo vetor, 0/5 bytes retornados e timeout de 1,0012 s (SHA-256
`5bba81c764e4071ec14a773cae0a724872636d65596b9af563b530e074a4b2e4`).
O CSV atual do AD2 foi adquirido às 12:26:26.517, cerca de 4 s após o relatório
do host (12:26:22.461), com janela de apenas 15,071 ms: não é uma captura do
burst. CH1 ficou entre 3,2876–3,2958 V e CH2 entre 3,3220–3,3307 V, sem
cruzamentos de 1,65 V. O trigger salvo continua em borda de subida a 0 V.
Os arquivos de mesmo nome no diretório `~/CapturasWaveForms` foram novamente
substituídos; hashes atuais: CSV
`c4aa809956ce669e20038e348e7e2f2400013ed31fb386d4df4d85fe236017e4` e
workspace `750aec5289db81db992647eabb5f04d011ae6ba741fb62e916c0b22347f225ed`.
**Loopback local do CP2102 em 29/09:** a tentativa das 12:35 retornou 0/5, mas
a ligação TXD↔RXD ainda não estava confirmada. A tentativa das 12:41 (`-02`)
também retornou 0/5; depois, o usuário esclareceu que TXD e RXD não estavam
conectados. Essa execução foi marcada como inválida e excluída da avaliação
(relatório SHA-256 `a236f9c2dfe5459071eea30d76c84d5a2b5fc2ca1386cd79fc97ed1e5d7e2467`).
Às 12:42, com o jumper TXD↔RXD conectado, o teste `-03` passou: os cinco bytes
`55 A5 00 FF 3C` foram recebidos sem divergências ou extras. O tempo da
transação informado pelo host foi 15,853 ms; ele não mede latência da FPGA. O
relatório `data/private/de10-2026-09-29/cp2102-self-loop-03-report.json` tem
SHA-256 `c947472d4428bd1e04357472bfd9c8bb80c3d16bd589b727d165933de28282b2`, e o
arquivo recebido tem o mesmo hash da referência:
`086a1a8a2575a3f80eb8a942552cfaf94825e511f1ec0df2448b4bfc97b68b01`.
Resultado: CP2102, driver/porta serial e caminhos TX/RX funcionam no loopback
local com essa montagem. P04 integrado ainda está pendente. Próxima ação:
remover o jumper local e conectar CP2102 TXD→V10, W10→CP2102 RXD e GND comum;
programar o baseline e repetir o eco, capturando V10/W10 durante o envio.

**Eco baseline e captura AD2 em 29/09, 12:51 (Manaus):** o relatório do host
registra `PASS`, com `55 A5 00 FF 3C` enviado e recebido byte a byte (5/5, sem
timeout ou extras), contexto `1eb6f17d795349c18d0910e9b03b6738`. O relatório
privado `data/private/de10-2026-09-29/p04-baseline-5b-report-05.json` tem
SHA-256 `69fd7e010c715bed17e0cfaaca552cc4e443f292641b6d42d3b6843e58317e25`; o
arquivo recebido tem SHA-256 `086a1a8a2575a3f80eb8a942552cfaf94825e511f1ec0df2448b4bfc97b68b01`,
igual à referência. O tempo de 16,753 ms da transação e 71,772 ms total são do
host, não latência isolada da FPGA. A captura `~/CapturasWaveForms/TesteP04.csv`
foi salva às 12:51:42.844, 7,96 s após o relatório: 8.192 amostras a 2,85714
MHz, janela de 2,867 ms; CH1 variou de 3,3796 a 3,3934 V e CH2 de 3,3203 a
3,3304 V, sem transições ou amostras abaixo de 1,65 V. O trigger estava em
borda de subida a 0 V, inadequado para capturar o start bit UART, que começa
com borda de descida. Hashes: CSV `8d0eebb2762b6603a747938713e8aa503aef8a377efff4353794e313bd26f64b`,
workspace `c2332475dd3f36a2048328feee68c0175e6c714f887a297891b03c2ecf495566`.
Assim, o eco byte a byte passou se o jumper local TXD↔RXD estava removido e a
placa ligada como planejado; esse detalhe não aparece no relatório. A captura
não comprova a forma de onda. Repetir o Single com trigger de descida em ~1,5 V,
janela de pelo menos 15 ms, armado antes do envio. P04 instrumental segue
pendente.

**P04 com trigger corrigido em 29/09, 13:02 (Manaus):** o relatório `-06`
retornou `PASS`, 5/5 bytes (`55 A5 00 FF 3C`), sem timeout ou extras; contexto
`bde161ccb4be4d36af5db7220436b0e8`. SHA-256 do relatório
`661d187ed18313d3e2f0cceabce755855733492277c4dd359e2e93a909180b14`; o binário
recebido tem SHA-256 `086a1a8a2575a3f80eb8a942552cfaf94825e511f1ec0df2448b4bfc97b68b01`.
O CSV `~/CapturasWaveForms/TesteP04.csv`, marcado às 13:02:52.586, está alinhado
ao relatório das 13:02:52.650. Com 8.192 amostras a 2,85714 MHz, a janela foi
2,867 ms. O trigger agora está em borda de descida a 1,5 V e há transições nos
dois canais. Considerando CH1=V10 e CH2=W10, o bit time preliminar é 104,075 µs
em CH1 (14 intervalos) e 104,212 µs em CH2 (4 intervalos), próximos dos
104,167 µs nominais. A primeira descida em W10 ocorreu aproximadamente 0,989 ms
depois da primeira descida em V10, compatível com o recebimento de um quadro
antes do eco. A janela termina antes de capturar o vetor completo e parte da
resposta. O nível baixo de CH2 ficou em 1,149 V (alto: 3,545 V), enquanto CH1
variou de −0,064 a 3,418 V; esse baixo elevado precisa ser esclarecido antes de
aceitar os níveis elétricos. Verificar que o jumper local CP2102 TXD↔RXD foi
removido e que CH2− está no GND comum: um jumper mantido pode unir dois drivers
de saída. Arquivos e hashes: CSV `fe1f7283737d40a35ae3fa203223428d64b017dc3a5a602f2c9a54aef369a736`,
workspace `72a4fa18b4fac058f33b448e4552d047954510225709f5d853fe86aa314316cf`.
Na captura `-06`, P04 já tinha evidência de transições e bit time preliminar,
mas a janela e o nível baixo de CH2 ainda precisavam ser corrigidos.

**P04 completo em 29/09/2026, 13:21 (Manaus):** o ensaio `-07` retornou
`PASS`: o CP2102 enviou e recebeu `55 A5 00 FF 3C`, 5/5 bytes, sem timeout,
divergência ou extras. O relatório
`data/private/de10-2026-09-29/p04-baseline-5b-report-07.json` tem SHA-256
`e017188ef8a39056da9b2ea3112258ccb4b2d75852a18f26df832e304d51fd43`; o vetor
recebido tem o mesmo SHA-256 da referência,
`086a1a8a2575a3f80eb8a942552cfaf94825e511f1ec0df2448b4bfc97b68b01`. O tempo
de 16,863 ms é do host/USB e não é latência isolada da FPGA.

O CSV `~/CapturasWaveForms/TesteP04.csv`, às 13:21:11.913, está alinhado ao
relatório concluído às 13:21:11.967. Foram capturadas 8.192 amostras a 400 kS/s,
janela nominal de 20,48 ms; trigger CH1 em descida a 1,5 V, escala de 1 V/div e
offsets em 0 V. Assumindo CH1=V10/RX e CH2=W10/TX, a análise dos centros dos bits
em 9600 baud decodifica `55 A5 00 FF 3C` nos dois canais, incluindo start e stop
válidos. Os níveis ficaram em −0,103 a 3,425 V no CH1 e −0,031 a 3,395 V no
CH2; o nível baixo elevado de 1,149 V da captura `-06` não se repetiu. Os
intervalos entre quadros indicam aproximadamente 104,1 µs/bit, próximo dos
104,167 µs nominais. A primeira saída em CH2 começa cerca de 0,990 ms após a
entrada em CH1; isso é observação temporal do enlace, não latência isolada da
computação AES/FPGA. Hashes: CSV
`249f074f682950b91e95e5fd13aa1d5f01da967eb31f6deed4cc4bb2d301ebd0`, workspace
`.dwf3work` `fbf92e6423d2c17ab2100f9b253d821433f14c8423d572af9b2d7aeca7ec7176`.
P04 baseline integrado e instrumental está aprovado na DE10-Lite. Este bloco
descreve os ensaios daquela configuração; a Cyclone IV foi retirada do escopo
ativo e seus resultados não são requisito para o artigo atual.

**Registro histórico P05/P06 secure na DE10-Lite, perfil 9600/8N1,
29/09/2026, 14:02 (Manaus):** o build secure
para MAX 10 `10M50DAF484C7G`, 50 MHz/9600 baud, passou no Quartus e na auditoria
dos três cantos; pior slack de setup 8,621 ns, sem violações. O SOF
`build/de10_lite/secure/uart_secure.sof` (SHA-256
`cf71a3db60d3bcfee699b85bab96c21fe0c8a2ce8ecd641d5759600d92c70d1b`) foi
programado no `10M50DAF484@1`, checksum `0x005990D7`.

O relatório privado `data/private/de10-2026-09-29/p05-secure-5b-report-02.json`
registra **PASS, 5/5** para entrada `55 A5 00 FF 3C` e ciphertext recebido
`09 A3 46 AF 82`, sem timeout, bytes extras ou divergência; o comparador
independente no PC recuperou exatamente a entrada original. Contexto
`5aa86b553a1c43debe50b2a40de4ff10` (chave e nonce continuam privados). SHA-256
do relatório `7b02e93f77fc01bb0d71874ad143e87a9d0196ba8f92c262c6687596d0fb99bb`;
arquivo recebido `ca775cee0ddbb90e31f2da46cb6413950f4a1033e94a5ba606244ca9763546e3`.
Os 16,728 ms registrados para a transação são medição do host/Linux/USB, não
latência isolada da FPGA.

A captura AD2 `~/CapturasWaveForms/TesteP05.csv` foi iniciada às 14:02:47.533,
63 ms antes do relatório do host. Foram adquiridas 8.192 amostras a 400 kS/s
(20,48 ms), com trigger CH1 em descida a 1,5 V, 1 V/div e offset 0 V. Sob a
ligação CH1=V10/RX e CH2=W10/TX, a decodificação nos centros dos bits recupera
os cinco quadros de entrada `55 A5 00 FF 3C` e os cinco quadros cifrados de
saída `09 A3 46 AF 82`, com start/stop válidos em 8N1. Bit time estimado:
104,063 µs (CH1) e 104,188 µs (CH2), compatível com 9600 baud dentro da
resolução de 2,5 µs/amostra. O primeiro start de saída ocorre cerca de
0,990 ms após o primeiro start de entrada; esse intervalo inclui a recepção do
byte e não representa latência isolada do AES. Nos centros dos bits, níveis
baixos médios: −0,052 V (CH1) e 0,014 V (CH2); altos médios: 3,390 V (CH1) e
3,350 V (CH2). Faixas de toda a captura: −0,096–3,433 V e −0,034–3,391 V.
CSV SHA-256 `36a01fbab4b7ec70b6300afaaf4a9ec57d104c675a78661b899b5d45d28039ee`;
workspace SHA-256 `7655dbf33123385b9cdcc6d005eab07bf60fb024af99db171ddcacf92c4aed9a`.
Resultado histórico: cinco bytes cifrados/decifrados e capturados no perfil
9600/8N1. Isso não fecha P05/P06 para o perfil que então estava vigente,
NEO-M8N/38400. A anotação de falha P05 neste registro descreve o estado antes do reteste aprovado às 18:32;
ver o resultado atual acima. AES-CTR não oferece autenticação.

**Preparação P07 na DE10-Lite, 29/09/2026, 14:19 (Manaus):** `make
baseline-fpga` passou e gerou `build/de10_lite/baseline/uart_baseline.sof` para
MAX 10 `10M50DAF484C7G`, 50 MHz e 9600/8N1. A auditoria temporal nos três
cantos passou sem violações. O USB-Blaster `[1-3]` programou o `10M50DAF484@1`
com sucesso (checksum `0x002A0029`, JTAG ID `0x031050DD`); SHA-256 do SOF
`f878f884b264c2f02a4d720c6ef3120f85ed88c3b52c3f87da7421c90437161c`. Isso
prepara o top baseline para observar a recepção GPS via V10/LEDR2 e manter
LEDR6/LEDR7 como indicadores de overflow/framing. Ainda não houve conexão ou
aquisição física do GPS, portanto P07 permanece **em preparação**, não aprovado.
Próximo passo: identificar os pinos do breakout, verificar alimentação e TX,
então capturar 512 bytes com `scripts/capture.py record` e validar NMEA.

**P01 — captura UART autônoma em 29/09, 15:45 (WaveForms):** foi programado
`uart_scope` na DE10-Lite, com clock de 50 MHz e TX emitindo `0x55` em 38400/8N1.
O USB-Blaster programou o dispositivo MAX 10 `10M50DAF484@1`; o SOF programado
tem SHA-256
`34c79d78eb2c37014fe78d9212bace8e2bf740ef83dd80b0c1c2d6f1f3d7e48d`. O CSV
corrigido contém o sinal no **Channel 2** (1 V/div, offset 0 V, modo Average),
amostrado a 10 MS/s por 8.192 pontos (janela de 819,1 µs). A metadata ainda
indica trigger de borda de descida no Channel 1, nível 1,5 V; alinhar a fonte
de trigger ao CH2 na próxima aquisição.

Com limiar de análise de 1,65 V, foram encontrados dez cruzamentos alternados
ao longo do start, dos oito bits de dados e do início do stop. Os nove
intervalos entre bordas têm média **26,038 µs** (taxa inferida **38.405 baud**,
erro aproximado de **+0,014%** ante 38400; resolução temporal de 0,1 µs por
amostra). A leitura nos centros do quadro confirma start `0`, dados LSB-first
`1 0 1 0 1 0 1 0` e stop `1`, isto é, **`0x55`, 8N1 — aprovado**. Os patamares
medianos foram −0,049 V (baixo) e 3,332 V (alto); a faixa extrema observada foi
−0,079 a 3,373 V. O pequeno mínimo negativo deve ser tratado como excursão
medida, não como nível lógico nominal.

A aquisição termina muito antes dos 100 ms entre quadros; portanto, P01 passa
para baud, enquadramento, padrão de dados e níveis observados, mas a
periodicidade/autonomia não foi confirmada. Os 100 ms permanecem a meta do
estímulo de bancada: o RTL usa `PERIOD_CYCLES = CLK_FREQ / 10`, independente de
`BAUD_RATE`; a troca de baud não exige alterar a cadência. Arquivos brutos em
`docs/evidence/`: `de10-lite-m9-p01-2026-09-29.csv` (SHA-256
`99faee86e72e23bc8652dcbb39aa6477e52d05f97090e9b3c18fc3e233ac4e7d`) e
`de10-lite-m9-p01-2026-09-29.dwf3work` (SHA-256
`08493f88224cffa9e925ee9a8585f61e85febc0a3da22fe6423367647d8793b2`).

**Repetição P01 — aquisição WaveForms às 16:39:36.927:** o novo CSV registra
CH2 a 10 MS/s, 8.192 pontos, 1 V/div, offset 0 V e modo Average. A janela é
819,1 µs, com eixo temporal de −211,010 a +608,090 µs. Com limiar de
1,65 V e interpolação linear entre amostras, os dez cruzamentos produzem nove
intervalos com média **26,03881 µs**, equivalente a **38.404,21 baud** (erro
aproximado **+0,011%** ante 38400). A amostragem nos centros confirma start 0,
dados LSB-first `1 0 1 0 1 0 1 0`, stop 1 (`0x55`). As extremidades observadas
foram −0,086045 e 3,372845 V; o mínimo negativo é um extremo transitório, não
o patamar lógico nominal. Esta repetição confirma novamente o quadro e a taxa,
mas, por durar menos de 1 ms, não mede a cadência de 100 ms. Evidência:
`docs/evidence/de10-lite-m9-p01-repeat-2026-09-29-1639.csv`, SHA-256
`f19ebb8ca50fab6f051f1688020b21fb14feaa58be837641188aaa5a714639c0`.

Na captura isolada das 16:39, o arquivo tinha apenas um quadro e por isso não
permitia avaliar a cadência. Não era necessário usar Record: a aquisição
Repeated guarda os buffers no PC em ordem temporal. A captura de 16:57 descrita
abaixo resolveu essa lacuna. Próximo passo: executar P02, loopback TX→RX, com a
fonte de trigger alinhada ao CH2.

#### Aquisição repetida P01 — workspace WaveForms às 16:57

O arquivo `M9-P01.dwf3work` contém dez buffers de 8.192 amostras, capturados a
10 MS/s (janela de 819,2 µs cada) em modo Repeated. A análise do canal de sinal
(CH2) encontrou dez transições por quadro; a amostragem nos centros de bit
decodifica `0x55` em 8N1 nos dez buffers. Sobre 90 intervalos entre transições,
o período médio foi **26,0397 µs** (baud inferido **38.402,85**, erro de
**+0,0074%** contra 38400). As extremidades observadas foram −0,0934 e
3,3802 V.

Os horários associados aos dez buffers avançam de 16:57:06.244 a 16:57:07.138.
Os nove intervalos são **95, 99, 107, 97, 95, 104, 106, 98 e 93 ms**: média
**99,33 ms**, mínimo 93 ms e máximo 107 ms. Isso confirma, com resolução de
1 ms e dez observações, uma repetição compatível com a meta de 100 ms. A
aquisição Repeated grava capturas no buffer do PC em ordem temporal, conforme
o [manual do WaveForms](https://digilent.com/reference/software/waveforms/waveforms-3/reference-manual); Record não é requisito para esse método.

Ressalva de configuração: o workspace salvo indica CH1 desligado, CH2 ligado,
mas a fonte de trigger como Channel 1. Os quadros de CH2 e os horários foram
analisados, porém a próxima configuração deve usar CH2 como fonte de trigger
para deixar o ensaio inequívoco.

- Workspace: `docs/evidence/de10-lite-m9-p01-repeated-2026-09-29-1657.dwf3work`
  (SHA-256 `005c6c286f53bbb735fb466b7fba0e1a0538ba52a60a0809e093a0585b4c10ea`).
- O CSV em `Documents/testerecordad2.csv` não foi usado para medir cadência:
  não contém cabeçalho, taxa de amostragem ou timestamps e registra apenas
  parte do quadro.

#### P03 — eco baseline e captura AD2 às 17:47

O CP2102 transmitiu quatro vezes `55 A5 00 FF 3C`; a FPGA devolveu todos os
20 bytes, sem perda, bytes extras ou timeout. O relatório informa 259,046 ms de
tempo total do host, que inclui Linux/USB e não deve ser apresentado como
latência da FPGA. Relatório privado
`data/private/de10-2026-09-29/p03-baseline-20b-report-01.json` (SHA-256
`e90e47e439c4eb87c3dfa56166fff061842e791e53aa5880e60baeb2e21c24d9`); arquivo
recebido com 20 bytes (SHA-256
`1ec8f144575a9c265334dfa2c385532741170ab730f39f5e38a9fae7f8517e5d`).

A captura Single `M9-P03` foi feita a 11,11111 MS/s, com 8.192 amostras por
canal e duração total de **0,737190 ms**. O trigger estava em CH1, borda de
descida a 1,65 V. CH1 variou de −0,0956 a 3,4254 V; CH2, de −0,0529 a 3,3728 V.
Há atividade serial nos dois canais, mas o quadro de cinco bytes requer
aproximadamente **1,302 ms** em 38400/8N1; logo o recorte não contém a
transferência completa. O resultado P03 de comparação de bytes permanece PASS;
esta aquisição não fecha P04.

Para uma forma de onda integral de um burst, usar Single a 1 MS/s com 8.192
amostras (8,192 ms; cerca de 26 amostras por bit), trigger CH1 na descida a
1,65 V e armar antes de transmitir. Para capturar as quatro transações
espaçadas em 50 ms, usar Record durante pelo menos 300 ms.

Capturas arquivadas em `docs/evidence/`: CSV
`de10-lite-m9-p03-baseline-ad2-2026-09-29-1747.csv` (SHA-256
`2ba21d94c607a4915fe3b60f5903da6f4434b8b4366255854f188ec5fa3bf574`) e
workspace `de10-lite-m9-p03-baseline-ad2-2026-09-29-1747.dwf3work` (SHA-256
`727b5e6a76773d578f6bc15a074dd6ca39ae20130c008b1d9c41e7526a9849e9`).

#### Recaptura P03/P04 — AD2 e CP2102 às 18:00

Uma transação baseline de cinco bytes foi capturada com 8.192 pontos a
800 kS/s (10,23875 ms), trigger CH1 de descida a 1,65 V e dois canais. O
CP2102 recebeu `55 A5 00 FF 3C` integralmente (5/5, sem timeout/extras; status
`PASS`). A decodificação analógica recupera o mesmo vetor tanto em CH1 (RX,
CP2102 TXD→V10) quanto em CH2 (TX, W10→CP2102 RXD), incluindo start e stop.
O bit time estimado é ~26,00 µs no CH1 e ~26,03 µs no CH2, compatível com
38400 baud; a média de espaçamento entre quadros de byte é ~260 µs. O início
do TX aparece cerca de 247,5 µs após o início do RX. Essa medição de pino a pino
inclui o tempo de recepção do quadro UART e não é a latência interna isolada do
AES. Níveis registrados: CH1 −0,0919 a 3,4403 V; CH2 −0,0455 a 3,3876 V,
próximos da lógica de 0–3,3 V.

O teste de bytes e a forma de onda de baseline estão aprovados. Relatório
privado `data/private/de10-2026-09-29/p03-baseline-5b-report-02.json` (SHA-256
`3eb1644bbdf055ac7580be2fdcdafb2ee59eb793703e9fb6571534421e02b16f`).
Capturas: [CSV](evidence/de10-lite-m9-p03-baseline-ad2-2026-09-29-1800.csv)
(SHA-256 `6327bbff8d6feda1c301eaa672d60932cced5e95d69d66173c7d99e7361fb637`)
e [workspace WaveForms](evidence/de10-lite-m9-p03-baseline-ad2-2026-09-29-1800.dwf3work)
(SHA-256 `2652c30c0d41fb2abc2a1391288c4d507ffd5c92558209a1eec5b896046492e2`).

## Situação em 26/09/2026

**Atualização em 26/09:** P02 (loopback da UART autônoma) foi repetido na
DE10-Lite com o `uart_scope`; os arquivos de captura são de 25/09 às 23:56 e a
confirmação dos LEDs foi registrada em 26/09. O AD2 registrou dez quadros
`0x55`, com 104,153 µs/bit e níveis medianos de 3,325 V/−0,026 V; os LEDs
confirmaram recepção válida e ausência de erro. P01/P02 estão agora registrados
nas duas placas.
As capturas originais e a análise estão no
[registro da bancada DE10-Lite + AD2](bancada-de10-lite-ad2-2026-09-25.md).
Também em 26/09, P03 baseline integrado passou na DE10-Lite: quatro quadros
`55 A5 00 FF 3C` retornaram byte a byte pelo CP2102, totalizando 20/20 bytes,
sem timeout, divergência ou extras. LEDR0 piscava, LEDR1/LEDR5 estavam acesos,
e LEDR6/LEDR7 apagados; a FIFO estava vazia ao final. A programação JTAG foi confirmada no
`10M50DAF484@1`; o relatório do host e o binário recebido estão em
`data/private/de10-2026-09-26/`. Os 272,65 ms do host incluem PC/USB/adaptador e
não são latência isolada da FPGA. P04–P11, secure e GPS ainda não foram
concluídos; o freeze físico previsto para 25/09 atrasou.
Na tentativa de estímulo de P04 às 01:18, o CP2102 enviou o primeiro burst,
mas recebeu zero bytes em 1 s; o script abortou os demais e não foi salva forma
de onda do AD2. A causa está em diagnóstico, sem alterar o resultado aprovado
de P03. Depois, LEDR9 ficou aceso e LEDR0 piscando; o baseline foi reprogramado
às 01:28 com sucesso (checksum `0x002A0029`). LEDR1/LEDR5 voltaram a acender e
LEDR0 continuou piscando. Com o AD2 armado, a primeira chamada foi barrada
antes da transmissão por incompatibilidade de tamanho (contexto de 20 bytes
para payload de 5). Após gerar contexto baseline de 5 bytes, `55 A5 00 FF 3C`
retornou integralmente pelo CP2102 (5/5, sem timeout/extras; 16,929 ms medidos
pelo host). Uma retentativa posterior enviou o mesmo burst, mas recebeu 0/5 em
1,002 s. Portanto, o retorno 5/5 observado antes não é reproduzível ainda; a
causa está em diagnóstico. O usuário também informou que nenhum traço apareceu
no WaveForms; não há CSV/workspace P04 e a medição instrumental segue pendente.
O próximo passo é registrar os LEDs de estado e confirmar se houve KEY0/reset
antes de programar ou enviar outros bytes.
O usuário confirmou que os indicadores de atividade/configuração voltaram a
acender após a regravação das 01:58. A hipótese de bloqueio volátil ganhou
suporte, mas o estado de LEDR9 e o evento que acionou o bloqueio ainda precisam
ser confirmados. Uma tentativa de dez bursts a cada 250 ms transmitiu só o
primeiro e parou por timeout (0/5 retornados); portanto, não houve sequência
repetida. Depois, para visualizar o sinal sem depender do eco, foram transmitidos
200 bursts do mesmo padrão durante 10,103 s, com intervalo de 50 ms; o host não
avaliou os retornos e não há captura salva. Aguardando confirmação se houve
transições nos canais do AD2 e o estado atual dos LEDs. Um segundo estímulo
visual, também de 200 bursts/1.000 bytes, foi enviado por volta de 02:30 durante
10,100 s, igualmente sem avaliação de eco. Às 02:31, o baseline foi reprogramado
com sucesso para iniciar em estado conhecido; o wrapper impede rearmar por KEY0
depois do primeiro RX, mas não encerra automaticamente cada burst. Logo depois, a verificação
explícita de eco enviou `55 A5 00 FF 3C` e recebeu 0/5 bytes em 1,501 s pelo
CP2102. O relatório local é `data/private/de10-2026-09-26/p04-echo-report.json`.
P04 continua falhando/intermitente; a causa não foi isolada e depende de conferir
LEDs e capturar RX/TX no AD2. Não houve evidência instrumental salva.

**Diagnóstico em 26/09, 02:41–02:54:** P04 agora tem
[capturas instrumentais e teste de continuidade](diagnostico-p04-de10-2026-09-26.md).
O `uart_scope` produziu 15 bytes `0x55` recebidos pelo CP2102, confirmando
W10→PC. A ponte antiga sem guarda de contexto retornou 0/5; um SOF novo que
espelha V10 diretamente em W10 também retornou 0/5. Durante 500 bytes
escritos no CP2102, o AD2 registrou o próprio TXD do adaptador alto em todas as 1.500.000 amostras
de uma janela de 6 s que incluiu o envio. Com o `uart_scope`, o mesmo AD2
registrou os pulsos em W10 e TXD alto. O CH1 já estava no próprio TXD do
CP2102, não no metal de V10; o reset USB específico do adaptador não mudou
o resultado. O próximo ensaio troca apenas a fonte de estímulo: AD2 DIO0→V10,
com CP2102 TXD desconectado, W10→CP2102 RXD e GND comum. **P04 continua pendente** e o freeze físico
de 25/09 segue atrasado. Nenhuma mudança no RTL baseline/secure foi feita.

**Retentativa com fonte AD2 em 26/09, 03:07–03:10:** com CP2102 TXD
desconectado e DIO0→V10, o SOF de continuidade ainda retornou 0/5. O AD2
mediu V10 em 3,262–3,281 V e W10 em 3,306–3,325 V, sem nível baixo na
janela de 32,768 ms. No teste estático, o próprio AD2 leu DIO0 alternando
1→0→1, mas V10 e W10 ficaram altos. O próximo passo é medir o terminal DIO0
diretamente com CH1 e verificar o contato físico até V10. Os relatórios
brutos e limites constam no [diagnóstico P04](diagnostico-p04-de10-2026-09-26.md).
P04 permanece **pendente**; regressão `make check` aprovada em 26/09.
Às 03:12, a leitura no terminal apontado como DIO0 também ficou em ~3,24 V
enquanto o readback do AD2 indicava 0. A identificação/continuidade física
do fio DIO0 precisa ser conferida antes de qualquer novo ensaio UART;
solicitada foto da ligação para comparar com o pinout Digilent.
Um comando independente pelo `dwfcmd` repetiu a divergência
(`Digital In=0x0000`, CH1=3,229 V, CH2=3,314 V). Pendente medição do terminal
DIO0 com multímetro durante nível baixo sustentado.

**Atualização de bancada em 25/09:** a DE10-Lite foi reprogramada com
`uart_scope` e o Analog Discovery 2 capturou um quadro completo `0x55`, com
aproximadamente 104 µs por bit. A referência diferencial da captura ainda
precisa ser esclarecida: a tensão apareceu entre 0 e −2,77 V, portanto o nível
elétrico do TX não foi validado por esse registro. Na verificação DC seguinte,
o multímetro indicou 3,3 V no ponto de referência, mas o Voltmeter do AD2
mostrou −17,2 mV. O jumper azul do adaptador BNC foi encontrado em AC; após
movê-lo para DC, o usuário obteve 3,3 V no WaveForms. O `uart_scope.sof` foi
reprogramado via JTAG às 23:08 após o desligamento da placa, com sucesso e sem
avisos. O workspace `TesteAD2UART.dwf3work` foi salvo às 23:15 e analisado:
na captura em DC, o canal 1 apresentou níveis de aproximadamente 3,308 V e
−0,072 V, quadro 8N1 `0x55` e período de 104,18 µs/bit. A repetição P01 do
TX autônomo está **concluída no AD2**, complementando o loopback anterior;
naquele momento, isso não concluía P03/P04 dos tops integrados. O workspace bruto, o CSV,
a imagem anterior, os hashes, a configuração do instrumento e os limites da
medição estão em
[bancada DE10-Lite + AD2](bancada-de10-lite-ad2-2026-09-25.md). O WaveForms
foi aberto e reconheceu o AD2; o `dwfcmd` não consegue adquirir enquanto a
interface ocupa o dispositivo. Naquele ponto, essa repetição ainda não encerrava
P03/P04 dos tops integrados nem os ensaios secure/GPS.

**Revisão técnica:** as duas plataformas são obrigatórias. A segunda FPGA é a
Cyclone IV E `EP4CE6E22C8N`, montada na placa ZRTECH/WXEDA V2.00. O perfil de
48 MHz, 9600/8N1 e a pinagem de bancada foram confirmados pelo JTAG, pela
programação e pelo período medido no TX. O secure otimizado agora cabe no fit e
os três projetos Cyclone IV já geram SOF; isso ainda não substitui os testes
físicos integrados.
O prazo continua concentrado na bancada até 25/09, com redação no fim de semana
e submissão/contingência até 30/09. Ver [revisão completa](revisao-completa-2026-09-20.md)
e o [roteiro específico da Cyclone IV](bancada-cyclone4-2026-09-21.md).

Antes de retomar os ensaios físicos, a instrumentação foi definida em torno de
um único adaptador USB–TTL CP2102. O novo host PC envia quatro quadros de cinco
bytes, aguarda 10 ms para detectar bytes extras e compara baseline/secure com
uma biblioteca independente. Na Cyclone IV, os quatro LEDs dos tops integrados
mostram heartbeat, atividade/configuração, overflow persistente e framing
persistente. O datapath, a pinagem e a força de saída UART não foram alterados.
Os builds baseline/secure e a regressão de integração passaram; isso prepara,
mas não conclui, o P04 físico.

Para a DE10-Lite, o roteiro P03–P06 foi fechado com pinagem JP1, ordem segura
de programação, quatro tentativas por variante, valores secure esperados e
verificação automática do relatório do CP2102. O P03 baseline passou fisicamente
em 26/09; P04 e o projeto secure ainda aguardam ensaios nessa placa.
O script arma a porta depois da programação e limpa as filas seriais antes do
primeiro quadro, sem consumir bytes/contexto antes da captura.
O teste em PTY de baseline/secure e o replay GPS passaram; a regressão `make check`
foi repetida com 34 testes Python. Isso valida o host, mas ainda não é evidência
física do CP2102.
Os dois SOFs foram regenerados no commit `746b085`, passaram pela auditoria de
timing nos três cantos e tiveram seus hashes registrados no plano de testes.
Em 22/09, o WaveForms 3.25.1 e o Adept Runtime 2.30.1 foram instalados no
Ubuntu amd64. O Analog Discovery 2 ainda não estava conectado, portanto a
instalação do software foi concluída, mas a enumeração e os ensaios P04/P06 com
esse instrumento continuam pendentes. O procedimento está no
[guia do AD2](analog-discovery-2-waveforms.md).

UART, FIFO, AES e CTR estão integrados em um módulo comum para baseline e
secure. A saída serial foi comparada no PC, incluindo simulação em 50 MHz/9600.
O gravador/comparador binário passou em testes com porta virtual Linux.
Em 18/09, a DE10-Lite foi identificada, o SOF `uart_scope` foi recompilado e
programado, e TX no osciloscópio e loopback TX→RX foram concluídos. Os tops
integrados `baseline` e `secure` estão separados em projetos Quartus e seus
builds foram concluídos, com recursos e timing registrados. O NEO-M8N está
disponível, mas ainda não há registro de aquisição física.

A documentação anterior foi consolidada em 15/09; suas simulações e compilações
UART foram executadas na noite de 14/09, conforme o relatório de revisão.

Decisão arquitetural em 15/09: retirar o bloco de sessão do datapath. O fluxo
principal passa a ser `GPS → UART RX → FIFO → passagem direta ou AES-CTR → UART
TX → PC`; chave, nonce e tamanho da captura ficam registrados como parâmetros
do experimento no PC.

A integração prevista inicialmente para 13/09 foi validada em RTL em 16/09.
A bancada prevista para 15/09 foi reagendada: a DE10-Lite foi disponibilizada
em 18/09, identificada, programada e validada no TX/loopback. Software, os
builds MAX 10 e o artigo seguem em paralelo, mantendo o encerramento em 25/09.

| Data | Entrega | Critério de conclusão | Situação |
| --- | --- | --- | --- |
| 07–10/09 | UART, FIFO, AES e CTR isolados | Testes e evidências dos marcos abaixo | Concluído em RTL; ponte e AES analisados no Quartus |
| 14/09 | Revisão e teste UART autônomo | Simulação, SOF e timing do alvo UART; documentação revisada | Concluído em simulação e Quartus |
| 16–18/09 | UART na DE10-Lite | Captura TX no osciloscópio, 0x55/104,16 µs, RX por jumper e indicadores registrados | Concluído em 18/09 — relatório da bancada |
| 20–21/09 | Identificar Cyclone IV | Modelo da placa, clock, pinos e esquema confirmados | **Concluído inicialmente em 21/09** — placa ZRTECH/WXEDA V2.00, `EP4CE6E22C8N`, JTAG, perfil de 48 MHz e pinos de bancada registrados; revisão elétrica de borda continua no P04 |
| 20–21/09 | Revisão e adequação às duas plataformas | Secure cabe no EP4CE6; métricas, captura e regressão corrigidas | **Concluído em 21/09** — wrappers, QSF/SDC, `uart_scope`, baseline e secure compilados; `make cyclone4-metrics` aprovado |
| 16/09 | Integração RTL e comparador | Replay serial recuperado sem divergências nos dois modos; testes PC | Concluído em simulação/PTY; ver marco abaixo |
| 17–18/09 | Contexto e preparação dos builds | Wrapper carrega contexto de bring-up e projetos baseline/secure separados | Concluído para DE10-Lite — aplicação de contexto privado validada em 20/09 |
| 18–20/09 | Builds DE10-Lite | Baseline/secure com recursos e timing rastreáveis | Concluído — dois SOFs regenerados, manifests `PASS`, recursos e timing registrados |
| 19/09 | Contexto e registro no PC | Contextos privados e registro persistente de nonces testados | Concluído — `make context` e `make pc` |
| 20/09 | Replay NMEA / captura | Fixture integrado ao ensaio RTL/PC e validador de captura bruta implementado | Concluído em simulação/PC; GPS físico pendente |
| 21/09 | Preparação física das duas plataformas | Pinagem/clock/JTAG confirmados; bitstreams de bancada programáveis; UART isolada validada | **Concluído com avanço** — P01/P02 Cyclone IV, baseline programado e P03 histórico aprovado; P04 iniciado |
| 22/09 | Baseline nas duas plataformas | P03/P04 executados na DE10-Lite e Cyclone IV; bytes conhecidos, waveform, loopback e comparação no PC | **Em andamento em 26/09** — P03 passou na Cyclone IV e na DE10-Lite; faltam P04 nas duas plataformas |
| 23/09 | Secure nas duas plataformas | P05/P06 executados; ciphertext capturado, decifrado no PC e contexto/reset registrados | Pendente |
| 24/09 | GPS real e ensaio contínuo | P07–P10 executados nos quatro pares placa/configuração; três repetições e captura contínua | Pendente — depende do NEO-M8N e das interfaces seriais |
| **25/09** | **Falhas, reset e fechamento físico** | **P11, repetição de qualquer caso instável, matriz de evidências completa e freeze** | **Pendente — último dia de bancada** |
| 26–27/09 | Artigo | Tabelas, gráficos, resultados físicos, discussão, referências e versões PT/EN | Pendente — foco exclusivo na escrita |
| 28/09 | Revisão técnica | Conferência do orientador e incorporação de comentários | Pendente |
| 29–30/09 | Submissão e contingência | Template, arquivos finais, envio, comprovante e eventual correção | Pendente |

## Plano fechado de testes físicos — 21 a 25/09

O objetivo desta semana é encerrar toda a bancada na sexta-feira. Cada ensaio
deve gerar uma evidência no mesmo dia: log de programação, captura serial,
foto/arquivo da forma de onda, relatório do comparador e registro da placa,
clock, pinos, contexto e horário. Um teste só entra como concluído quando os
bytes forem comparados automaticamente; LED ou forma de onda isolada não basta.

| Dia | Manhã | Tarde | Fechamento obrigatório |
| --- | --- | --- | --- |
| **Seg 21/09** | Confirmar Cyclone IV: código EP4CE6E22C8, oscilador, pinagem, alimentação, GND e JTAG. Preparar QSF/SDC e identificar os pinos RX/TX. | Programar um bitstream mínimo/`uart_scope` em cada placa. Repetir UART autônoma e loopback na Cyclone IV; preparar o baseline para o CP2102. | P01/P02 registrados; P03 histórico do baseline aprovado; P04 iniciado, com repetição elétrica necessária. |
| **Ter 22/09** | Repetir P04 com ponta ×10 e massa curta; medir bit time e amplitudes da borda no baseline das duas plataformas. | Consolidar captura no PC, waveform e três repetições por placa; corrigir qualquer instabilidade antes do secure. | P03/P04 do baseline classificados, comparação byte a byte e waveform arquivadas. |
| **Qua 23/09** | Programar o secure nas duas placas e carregar o contexto do ensaio. Repetir os bytes conhecidos. | Executar P05/P06: capturar ciphertext no PC, decifrar com o contexto registrado e medir RX→TX no osciloscópio ou AD2 quando possível. Testar reset antes do primeiro byte e bloqueio após o primeiro byte. | Ciphertext recuperado exatamente, contexto/nonce registrados sem chave em claro, três repetições secure por placa e evidência de reset. |
| **Qui 24/09** | Validar o NEO-M8N: VCC, GND, nível elétrico, atividade TX e 9600/8N1. Capturar a referência NMEA independente. | Executar P07–P09 nos quatro casos: DE10-Lite baseline/secure e Cyclone IV baseline/secure. Fazer três repetições, validar NMEA e comparar a entrada com a saída recuperada. | GPS físico comprovado, zero divergência, framing/overflow registrados e arquivos brutos/hash preservados. Se possível, iniciar P10 contínuo. |
| **Sex 25/09** | Completar P10: captura contínua por duração registrada nos quatro casos, com perdas, primeira divergência, FIFO e erros contabilizados. | Completar P11 em cada placa/configuração; repetir qualquer ensaio instável, salvar SOFs/logs/capturas e preencher a matriz final de evidências. | **Freeze físico:** P01–P11 classificados como aprovado, reprovado ou bloqueado com causa objetiva. Nenhuma nova alteração de RTL depois deste ponto. |

### Matriz de cobertura física

- **P01–P02:** UART autônoma, níveis, temporização, TX e loopback nas duas
  plataformas.
- **P03–P04:** baseline, retransmissão de bytes conhecidos, waveform e
  comparação no PC nas duas plataformas.
- **P05–P06:** secure, ciphertext, decifragem independente, latência e reset
  do contexto nas duas plataformas.
- **P07:** alimentação, terra, nível e formato serial do GPS.
- **P08–P09:** GPS real no baseline e no secure, três repetições por plataforma.
- **P10:** estabilidade contínua e contagem de perdas/erros/overflow/FIFO.
- **P11:** reset, descarte da captura anterior e recuperação com contexto novo.

O NEO-M8N, a Cyclone IV com pinagem confirmada, o osciloscópio, USB-Blaster,
cabos/jumpers e um adaptador USB–TTL com sinais de 3,3 V precisam estar disponíveis
antes do início de 21/09. Um CP2102 é suficiente: a referência GPS é capturada
primeiro e depois reapresentada à FPGA pelo mesmo módulo. Sem GPS ou
sem a identificação elétrica da Cyclone IV, o caso correspondente deve ser
marcado como **bloqueado**, nunca como aprovado por replay RTL.

Os testes de contador esgotado, overflow forçado e falhas internas permanecem
na validação RTL; fisicamente serão verificados apenas os efeitos observáveis
de framing, reset, perda de dados e estabilidade da comunicação.

A chamada pública do BTSym consultada em 14/09 informa 30/09/2026 como prazo
externo. Confirmar modalidade e template no portal antes do envio. O planejamento
de bancada termina em 25/09; o fim de semana fica reservado para a redação e a
submissão deve ocorrer até 30/09.
[Chamada de trabalhos](https://lcv.fee.unicamp.br/virtual-btsym26-home/btsym26-call-for-paper/).

## Marco em 22/09: instrumentação preparada para P04–P06

- O host PC `scripts/serial_bench.py` foi implementado para o CP2102
  full-duplex. Cada tentativa transmite cinco bytes, espera até 1 s pela
  resposta e observa 10 ms para detectar bytes tardios ou duplicados.
- O relatório JSON registra sequência, modo, TX/RX, tamanho, timeout, extras,
  divergência e hashes. O tempo registrado é explicitamente do host, não
  latência física da FPGA; framing e overflow continuam vindo dos diagnósticos
  da placa e da instrumentação.
- O modo baseline verifica eco; o modo secure preserva o ciphertext para
  comparação independente no PC. O fluxo funciona tanto na DE10-Lite quanto na
  Cyclone IV, com o mesmo adaptador e pinagem específica de cada placa.
- Os LEDs integrados da Cyclone IV agora priorizam as flags persistentes:
  heartbeat, configuração/atividade, overflow e framing. O mapeamento é igual
  no baseline e no secure.
- `make check`, os dois builds Cyclone IV e `make cyclone4-metrics`
  passaram. Pós-fit: baseline 299 LE/189 registradores/Fmax 104,08 MHz; secure
  5.580 LE/889 registradores/Fmax 83,56 MHz; ambos operam a 48 MHz.
- O P04 continua pendente. A repetição deve usar ponta ×10, entrada de 1 MΩ,
  acoplamento DC e massa curta. Os 8 mA permanecem inalterados até existir uma
  captura correta e repetível que justifique testar 4 mA/slew lento.
- O novo [roteiro integrado da DE10-Lite](bancada-de10-lite-integrada-2026-09-22.md)
  separa P03–P06, impede confusão de cabo quando as duas FPGAs estão presentes
  e fixa quatro tentativas de `55 A5 00 FF 3C` por variante.
- O ambiente WaveForms/Adept foi instalado e verificado; a ausência do AD2 na
  porta USB foi registrada. A captura com AD2 será evidência física somente
  depois de `dwfcmd enumerate` listar o instrumento e os arquivos de captura
  serem preservados.
- Os SOFs baseline/secure foram regenerados a partir de `746b085`, com manifests
  `PASS`, timing aprovado nos três cantos e hashes conferidos. Isso ainda não
  representa programação ou funcionamento físico na DE10-Lite.
- `scripts/serial_bench.py` envia o vetor conhecido ou o replay NMEA, registra
  cada resposta e gera um relatório JSON: baseline exige eco exato; secure
  decifra todo o fluxo CTR e rejeita lacunas, corrupção ou bytes extras. Os
  testes unitários do host passaram; nenhum log físico da DE10-Lite foi
  produzido nesta preparação.

## Marco em 21/09: perfil Cyclone IV preparado para a bancada

- A placa foi identificada como **ZRTECH/WXEDA V2.00**, com FPGA
  `EP4CE6E22C8N`. A memória `W9864G6KH-6` é SDRAM externa e não participa do
  caminho UART/AES.
- O perfil validado usa clock de 48 MHz no `PIN_24`, reset ativo baixo no
  `PIN_89`, RX em J3 `PIN_103`, TX em J3 `PIN_100` e quatro LEDs nos pinos
  `PIN_1`, `PIN_2`, `PIN_3` e `PIN_144`. RX/TX foram deslocados dos pinos da
  referência pública para os pontos realmente acessíveis no J3.
- `make cyclone4-uart-fpga`, `make cyclone4-baseline-fpga` e
  `make cyclone4-secure-fpga` passaram no Quartus 25.1 e produziram os SOFs
  correspondentes. `make cyclone4-metrics` também passou.
- `j3_scope` foi programado e medido: aproximadamente `104 µs` por bit e
  `3,32 V` em nível alto. O loopback entre `PIN_100` e `PIN_103` passou.
- O baseline integrado foi programado e o P03 histórico passou pelo caminho
  externo, com retorno exato de `55 A5 00 FF 3C`. Não havia jumper local entre
  RX e TX. A repetição atual será feita pelo CP2102 full-duplex.
- A primeira observação de borda do P04 registrou overshoot/undershoot
  preliminar; ela não fecha o teste e motivou a instrumentação de 22/09.
- Evidência e sequência completa: [bancada Cyclone IV](bancada-cyclone4-2026-09-21.md).

## Marco em 20/09: endurecimento da validação e preparação da Cyclone IV

- O wrapper integrado da DE10-Lite passou a tratar o contexto provisionado como
  de uso único: KEY0 ainda pode rearmar um ensaio antes do primeiro byte, mas
  não recarrega a mesma chave/nonce depois do início da recepção. A guarda é
  reiniciada somente por novo carregamento do bitstream, e o reset de
  inicialização do FPGA ficou determinístico mesmo sem pressionar KEY0.
- A validação de métricas passou a exigir os manifests dos builds, hashes de
  fontes e artefatos, commit, dispositivo, clock, baud rate e status final.
  Falhas de fit, Fmax ausente/duplicado, slack negativo, arquivo obsoleto ou
  build incompleto agora interrompem a coleta em vez de produzir uma tabela
  parcial.
- Foi adicionado o estudo reproduzível de capacidade para o alvo
  `EP4CE6E22C8`. Ele gera projetos baseline/secure para síntese e fit, sem
  declarar pinagem, clock de bancada, SOF ou validação da placa Cyclone IV.
  A execução atual registrou 351 LE/216 registradores no baseline e
  5.626 LE/917 registradores no secure; esses números são apenas capacidade
  exploratória e serão substituídos pelos resultados da placa quando o modelo,
  pinagem e oscilador forem confirmados.
- A captura do experimento recebeu um modo pareado para armar fonte e saída
  antes do READY, reservar arquivos privados e registrar a captura uma única
  vez. O validador NMEA passou a analisar janelas brutas sem alterar os bytes,
  aceitar identificadores padrão e proprietários válidos e relatar prefixos ou
  sufixos parciais explicitamente.
- A suíte Python local passou a 31 testes aprovados. A regressão HDL, os builds
  Quartus, o replay GPS nominal e a auditoria de métricas passaram após a
  reconciliação; nada deste marco representa validação física da Cyclone IV ou
  do GPS.

## Marco em 20/09: redução de área do AES

- Removido o banco de onze chaves. O núcleo armazena a chave original e calcula
  as chaves de rodada durante cada bloco, mantendo a interface e os 20 ciclos
  de cifragem. Preparação da chave: um ciclo; intervalo mínimo entre blocos: 21.
- `make aes`: 866 vetores independentes aprovados, lint e checagem estrutural.
  `make ctr`: 60 fluxos / 19.009 bytes recuperados, incluindo stalls e resets;
  inicialização do CTR reduzida de 34 para 25 ciclos.
- Fit exploratório após essa alteração: 5.623 LE / 915 registradores no
  EP4CE6E22C8, aprovado. Evidência local:
  `build/review-2026-09-20/cyclone4-probe/output_files/resource_probe.fit.summary`.
  O ensaio manteve o wrapper de 50 MHz, sem pinagem/SDC de bancada e sem SOF;
  não fornece uma validação da placa nem do oscilador provável de 48 MHz.
- O contrato atualizado está em [AES](aes128.md) e [CTR](ctr.md).

### Ponto de retomada

As correções de wrapper, reset, métricas, captura, validação NMEA e o estudo de
capacidade da Cyclone IV foram integrados ao histórico remoto no merge
`b065ba8`. A regressão completa, os builds baseline/secure e a auditoria de
métricas foram repetidos antes de atualizar as tabelas dos manuscritos. Os
artefatos locais não substituem a confirmação de modelo, oscilador e pinagem da
Cyclone IV nem os ensaios físicos do GPS.

## Marco intermediário em 20/09: correções sem hardware (superado)

Este registro foi escrito antes da reconciliação e preserva o diagnóstico
intermediário. Os pendentes descritos abaixo foram encerrados no marco de
endurecimento da validação, acima.

- `scripts/fpga_metrics.py` passou a rejeitar slack negativo, auditoria
  incompleta, ausência de Fmax por canto e status de build não aprovado; foram
  adicionados testes negativos em `tb/test_fpga_metrics.py`.
- O validador NMEA passou a rejeitar identificador inválido, controles ASCII,
  corpo vazio e sentenças acima de 82 bytes incluindo CRLF. O replay público
  continua com 5 sentenças e 309 bytes.
- O replay de produção foi separado do estímulo com pausas artificiais; a nova
  latência foi medida em Linux no ensaio nominal.
- O wrapper DE10-Lite não rearma o mesmo contexto estático após um reset
  operacional; nova programação é necessária antes de outro ensaio. Isso é
  proteção contra reutilização acidental, não gerenciamento de chaves.
- Evidência: [validação das correções](validacao-correcoes-2026-09-20.md).
- O conjunto final passou com 31 testes Python, `py_compile`, `git diff --check`,
  regressão HDL, replay GPS, builds DE10-Lite e `make metrics`.

O próximo passo é a validação física: executar C0/P01/P02 na Cyclone IV,
começando pela programação do `uart_scope` e pela medição do bit time. Enquanto
isso não ocorrer, os SOFs e as métricas continuam sendo evidência de Quartus,
não de funcionamento elétrico da placa.

## Marco em 20/09: revisão completa e identificação do EP4CE6

- `make check` passou novamente: 27 simulações, nove configurações de lint,
  checagens estruturais e 19 testes PC. Isso não substitui bancada integrada.
- Compilação exploratória do secure para `EP4CE6E22C8`: síntese concluída;
  fit reprovado, com 6.520 funções combinacionais para 6.272 disponíveis.
  Não houve SOF, programação, pinagem real ou análise temporal válida desse alvo.
- A latência de 169.269 ciclos registrada no replay abaixo inclui pausas
  artificiais do TX. Deve ser mantida como evidência histórica desse estímulo,
  não utilizada como latência nominal no artigo antes de nova medição.
- Testes adicionais reproduziram reutilização de máscara CTR após reset,
  aceitação de slack negativo pelo extrator de métricas e falhas do validador
  NMEA. O RTL não foi modificado nesta revisão; correções continuam pendentes.
- Um CP2102 com sinais de 3,3 V foi definido como o único host serial da
  bancada. A captura direta do GPS e o replay para a FPGA continuam pendentes.
- Próximo passo sem placa: adequar a área do AES compartilhado e os testes;
  em paralelo, Leonardo confirma placa/oscilador/pinagem e prepara as interfaces.

Detalhes, fontes, evidências e prioridades na
[revisão completa](revisao-completa-2026-09-20.md). Os marcos anteriores abaixo
preservam o que foi executado; esta revisão qualifica suas limitações.

## Marco em 18/09: DE10-Lite conectada e programada

- `jtagconfig` encontrou `USB-Blaster [1-3]` e o dispositivo `10M50DA(.|ES)/10M50DC`,
  com JTAG ID `0x031050DD`.
- `make uart-fpga` recompilou o top autônomo para `10M50DAF484C7G` com Quartus
  Prime 25.1std.0 Build 1129. O fit terminou sem erros; o relatório indicou
  213 elementos lógicos, 95 registradores e 14 pinos.
- O timing foi auditado nos três cantos, sem violações: pior setup `12,824 ns`,
  hold `0,148 ns`, recovery `16,773 ns`, removal `0,427 ns`.
- O SOF SHA-256 `3aa552c5004c35cb42602608ec8c2ab387418a98789f9bb0d080f543c7e6ec5f`
  foi programado por JTAG; o Quartus confirmou configuração bem-sucedida de
  `10M50DAF484@1`.
- A forma de onda do TX e o loopback TX→RX foram observados e registrados:
  bit de `104,22 µs`, quadro de aproximadamente `1,042 ms`, intervalo de `0,1 s`
  e loopback aprovado. Portanto, a UART autônoma física está `Concluída`.

O procedimento e os valores medidos estão no
[relatório da bancada](bancada-de10-lite-2026-09-18.md). O plano completo,
incluindo simulação, compilação e testes físicos, está em
[plano de testes](plano-de-testes.md).

## Bancada concluída: UART autônoma

1. Com o SOF programado, resetar com KEY0 e medir TX diretamente.
2. Colocar o jumper TX → RX e registrar LEDs/forma de onda.
3. Guardar as condições no relatório de bancada.
4. Programar os novos tops baseline e secure para iniciar a validação integrada.

O [roteiro UART](../fpga/de10_lite/uart_scope/README.md) descreve a montagem;
o [cadastro Cyclone IV](../fpga/cyclone4/README.md) lista os dados ainda necessários.

Os builds integrados da DE10-Lite foram concluídos em 18/09:

| Variante | Recursos | Fmax no pior canto | Pior setup | SOF |
| --- | --- | ---: | ---: | --- |
| Baseline | 342 LE, 215 FF, 8.192 bits, 14 pinos | 132,61 MHz | 12,459 ns | `build/de10_lite/baseline/uart_baseline.sof` |
| Secure | 6.984 LE, 2.196 FF, 8.192 bits, 14 pinos | 82,19 MHz | 7,833 ns | `build/de10_lite/secure/uart_secure.sof` |

Detalhes, hashes e todas as margens estão no [plano de testes](plano-de-testes.md).

## Entrega concluída em 18/09

`make integration`, `make baseline-fpga` e `make secure-fpga` foram executados.
Os relatórios de recursos e timing e o [plano de testes](plano-de-testes.md)
foram atualizados. A próxima etapa física é programar os tops baseline e
secure na DE10-Lite e realizar o ensaio integrado com uma fonte UART; o GPS
continua pendente.

## Marco em 19/09: contexto de experimento no PC

- `scripts/context.py` cria contextos `baseline` e `aes-128-ctr` para cada
  captura, com tamanho, contador, chave e nonce quando aplicável.
- O nonce secure é gerado aleatoriamente quando não é informado; o registro
  persistente guarda somente o fingerprint SHA-256 da chave e rejeita o mesmo
  par chave/nonce.
- Contexto, registro e lock são privados (`0600`), com atualização bloqueada e
  substituição atômica. Limites do contador e colisões foram testados.
- Os tops DE10-Lite passaram a aceitar `CONTEXT_KEY`, `CONTEXT_NONCE` e
  `CONTEXT_COUNTER` como parâmetros de elaboração; o testbench confirmou um
  contexto diferente do padrão (`0x55` recebido e `0xe2` transmitido).
- `make context` passou com sete testes; `make pc` passou com 15 testes; a
  integração baseline/secure e o wrapper parametrizado continuaram aprovados.

Essa etapa prepara os ensaios sem depender da placa. A configuração do wrapper
é estática no build: `CONTEXT_FILE` gera o pacote privado e o incorpora ao SOF.
Não há configuração em tempo de execução, GPS real nem validação física dos
tops integrados neste marco.

## Marco em 20/09: contexto privado aplicado ao Quartus

- `scripts/quartus_build.sh` passou a aceitar `CONTEXT_FILE` nos alvos baseline
  e secure, validar o modo e gerar `context_params.sv` com permissão `0600`.
- `make baseline-fpga` foi repetido com o pacote de bring-up: 0 erros, SOF e
  três cantos temporais aprovados.
- Um build secure recebeu um JSON privado temporário: o Quartus reconheceu o
  pacote, gerou o SOF e não apresentou violações temporais. O contexto foi
  removido depois do ensaio e o secure foi recompilado com o contexto público.
- A evidência detalhada está em
  [validação do build com contexto](validacao-build-contexto-2026-09-20.md).

Essa entrega encerra a implementação sem placa desta etapa. Ainda faltam
programar os tops integrados, transmitir uma sequência de teste, validar o
secure com o mesmo contexto registrado no PC e, depois, conectar o GPS real.

## Marco em 20/09: replay NMEA reproduzível sem placa

- Foi adicionado `reference/gps/neo-m8n-nmea-sample.txt` com cinco sentenças
  públicas/sintéticas do formato esperado do NEO-M8N: RMC, GGA, GSA, GSV e TXT.
- `scripts/gps_fixture.py` valida ASCII, checksum NMEA, limite de 82 caracteres
  e transforma as linhas de referência em uma transmissão CRLF de 309 bytes.
- O replay passou a ser o caso NMEA do vetor comum de integração. Baseline e
  secure processaram 9 streams/2.681 bytes no modo acelerado e 4 streams/49
  bytes em 50 MHz/9600, sem divergências.
- A simulação dedicada processou os 309 bytes do replay em 50 MHz/9600 nos dois
  modos, com FIFO máxima de 1 byte e latência nominal de 80 ns do RX válido ao
  início do TX e 1.041.680 ns até o fim do TX; a recuperação no PC não apresentou
  divergências.
- `make metrics` consolidou recursos, Fmax e slacks dos builds baseline/secure;
  a tabela está pronta para a seção de resultados do artigo.
- Os rascunhos em inglês e português foram consolidados com os resultados
  atuais e a marcação explícita das evidências físicas ainda pendentes.
- A suíte Python passou com 31 testes. A evidência está em
  [validação do replay NMEA](validacao-replay-nmea-2026-09-20.md).

Esta entrega valida apenas o contrato de dados e o caminho RTL/PC. Não é
captura do GPS, não testa nível elétrico, nem altera a pendência dos ensaios
P07–P11 na bancada.

## Marco em 20/09: validação de captura NMEA

- `scripts/gps_capture.py` valida arquivos binários produzidos pela captura
  serial: sentença completa, ASCII, CRLF, checksum e limite de 82 caracteres.
- O relatório registra tipos de sentença, quantidade, tamanho e SHA-256, com
  permissão `0600` e sem sobrescrever um ensaio anterior.
- O replay público foi usado como teste de contrato, com 31 testes Python aprovados.
  Isso deixa o procedimento pronto para o NEO-M8N, mas ainda não comprova uma
  captura física.
- O comando de bancada será:

  ```bash
  make gps-capture-check GPS_CAPTURE=data/private/ensaio01/gps-reference.bin
  ```

  A referência só entra no experimento depois desse comando e do registro da
  montagem física.

## Marco em 20/09: consolidação dos manuscritos

- As versões em inglês e português incorporam as métricas pós-fit da DE10-Lite,
  o replay de 309 bytes, a latência RTL e as limitações atuais.
- O plano de validação física agora exige validar a referência NMEA e guardar o
  relatório/hash antes da comparação baseline/secure.
- `make manuscript-check` passou nos dois rascunhos e verifica que o replay
  sintético e a pendência da validação física continuam declarados.
- A seção de resultados físicos permanece em aberto; não foi substituída por
  simulação ou síntese.

## Ensaio auxiliar — DE10-Nano

Em 18/09 foi disponibilizada uma DE10-Nano para repetir a medição da UART
isolada na FPGA Cyclone V. O alvo `fpga/de10_nano/uart_scope/` foi preparado
com o mesmo RTL, clock de 50 MHz, 9600 baud, 8N1 e estímulo `0x55` da
DE10-Lite. A compilação no dispositivo `5CSEBA6U23I7` foi concluída com
sucesso e o `.sof` foi gerado. A programação via JTAG e a medição no
osciloscópio ainda estão pendentes; portanto, este marco está **Pronto para
bancada** e não representa validação física.

O ensaio é auxiliar: serve para comparar período do bit, duração do quadro,
intervalo entre quadros e níveis/arestas observados no osciloscópio. Ele não
substitui os quatro builds do artigo nem constitui validação do GPS/AES-CTR.
Os números e o procedimento estão registrados em
[bancada da DE10-Nano](bancada-de10-nano-uart-2026-09-18.md).

## Marco antecipado em 07/09: preparação sem placa

- UART v2 revalidado, preservando suas fontes.
- FIFO de 1.024 bytes e ponte serial sem cifra implementadas; leitura síncrona,
  ocupação máxima, indicação persistente de overflow e erro de stop.
- Testes independentes de FIFO e retransmissão, inclusive 50 MHz/9600 baud.
- Projeto Quartus, pinagem do lado FPGA e restrições temporais definidos.
- `.sof` gerado; análise de setup, hold, recovery e removal nos três cantos.

Evidências em [validação da ponte](validacao-ponte-quartus-2026-09-07.md).
Isso antecipa a preparação da baseline física; não conclui sua validação de
bancada. O núcleo AES previsto para 08–11/09 foi implementado no marco seguinte.

## Marco em 08–09/09: AES isolado

1. Ordem de bytes e interface de chave/bloco documentadas em [AES](aes128.md).
2. S-box, ShiftRows, MixColumns e expansão testados separadamente.
3. Onze chaves de rodada armazenadas; preparação medida em 10 ciclos.
4. Datapath de 128 bits reutilizado, duas fases por rodada: 20 ciclos por bloco,
   intervalo mínimo de iniciação de 21 ciclos, ambos conferidos pelo testbench.
5. 866 vetores de comparação independente, incluindo 284 NIST CAVP.
6. Projeto Quartus separado para recursos e timing interno; não é o sistema GPS.

Validação final em 09/09: 18 simulações passando, lint e estrutura aprovados;
6.482 LEs, 1.813 registradores e menor Fmax interna de 77,91 MHz. Setup, hold,
recovery e removal internos positivos nos três modelos. Ver [relatório](validacao-aes-2026-09-09.md)
para as fronteiras excluídas, ferramentas e reprodução.

## Marco em 10/09: CTR e adaptador por byte

- Gerador de máscaras com nonce de 96 bits, contador de 32 bits e bloqueio
  depois do último contador permitido.
- Adaptador com duas reservas de máscara, transferência por `valid/ready` e
  descarte do contexto em cancelamento/reset.
- 36 contextos do gerador, 73 máscaras e 60 fluxos de 1 a 4.097 bytes conferidos
  com `cryptography`/OpenSSL, incluindo o exemplo oficial NIST.
- 19.009 bytes efetivamente produzidos pelo RTL recuperados no PC; zero divergências.
- 140 momentos de cancelamento/reset testados, seguidos de rearmamento.
- `make check` concluído com código 0: 20 simulações, lint de quatro tops,
  checagem estrutural e verificação independente no PC.

Evidências e comandos no [relatório CTR](validacao-ctr-2026-09-10.md);
interface documentada em [CTR](ctr.md). O teste do PC lê arquivos da simulação;
configuração e captura de portas seriais ainda serão implementadas.


## Marco em 14/09: UART de bancada e revisão

- `uart_scope`: gerador de 0x55 a cada 100 ms, RX independente, último byte nos
  LEDs e flags persistentes. Sem FIFO ou cifra no alvo de teste.
- Testbench com decodificador externo, RX independente, modelo de jumper,
  entrada desconectada, duração de cada bit, período, erro e reset.
- `make uart`, `make uart-waves` e `make uart-fpga` selecionam somente a UART.
  Corrigida a geração VCD ausente no testbench do top.
- Ponte recebe clock/baud por parâmetros de elaboração; top da DE10-Lite
  continua explicitamente em 50 MHz, 9600/8N1.
- Build/auditoria temporal selecionados por alvo. Erros atualizam o status e
  alertam sobre SOF antigo. Cyclone IV e builds ainda ausentes falham de forma
  explícita.
- Comparação ampliada para quatro configurações no mesmo repositório; docs,
  HTML de quatro telas e arquitetura ajustados nesta entrega.
- Quartus da UART: 213 LEs, 95 registradores, zero memória/PLLs, menor Fmax
  139,35 MHz; setup, hold, recovery e removal positivos nos três modelos.

Evidências consolidadas em [revisão e validação](revisao-2026-09-14.md).
Esses resultados não representam programação de placa ou captura GPS.

## Marco em 16/09: integração serial e software de captura

- `uart_ctr_bridge`: seleção baseline/secure por elaboração, leitura da FIFO
  com reserva/retenção de byte e consumo de máscara no aceite do TX.
- Framing/overflow interrompem a aquisição; abort/reset descartam dados
  pendentes. O último quadro termina antes de parar por esgotamento do contador.
- Quatro simulações integradas: nove fluxos por modo no teste acelerado e
  quatro por modo em 50 MHz/9600 com FIFO de 1.024 bytes. A execução histórica
  foi preservada; o replay atual é documentado no marco de 20/09.
- Cancelamento em 32 situações por modo acelerado, falhas e recuperação
  byte a byte com contexto novo. Baseline sem módulos AES confirmado pelo Yosys.
- Gravador binário Linux e comparador com contagens, hashes e primeira
  divergência; a execução atual também inclui o contrato do replay NMEA.
- Regressão completa: 27 simulações, sete configurações de lint, estrutura e
  conferência independente; 15 testes PC; evidências no [relatório](validacao-integracao-2026-09-16.md).
- Antes da consolidação desta etapa, `git fetch origin` foi executado e
  `origin/main` permaneceu alinhada ao histórico local; nenhum conteúdo remoto
  novo precisou ser incorporado.

O [contrato RTL](integracao-uart-ctr.md) e o [guia PC](captura-pc.md) delimitam
o que está pronto. O wrapper e o build já aceitam contexto privado estático por
`CONTEXT_FILE`; um JSON ainda não configura a FPGA em tempo de execução. O
registro persistente de nonces e o início alinhado seguem prontos para a
bancada; validação física e GPS continuam pendentes. `make check` foi repetido
em 20/09 e terminou com código 0.

## Contrato da integração e pendências de bancada

- FIFO de 1.024 bytes, resposta de leitura retida até aceite do próximo estágio.
- AES-CTR com nonce de 96 bits, contador de 32 bits e duas reservas de máscara;
  consumir máscara só no handshake. Não esperar 16 bytes de GPS para cifrar.
- Cada ensaio terá seu tamanho N definido pela captura no PC. O início e o fim
  do replay são metadados do experimento, não um bloco adicional no datapath.
- Usar nonce novo a cada captura com a mesma chave, inclusive após reset, e
  bloquear wrap. O PC manterá registro persistente; chave/nonce de simulação
  não são configuração para capturas reais.
- Framing, overflow ou reset invalidam a captura; recomeçar com novo contexto.
- Captura da referência GPS independente; PC decifra e compara cada byte,
  salva primeira divergência, contagens e hashes.

O comparador é **UART + FIFO + interfaces de fluxo** versus **o mesmo sistema + AES-CTR**
em cada FPGA. A UART para osciloscópio e a ponte atual são preparatórias.
A [arquitetura](arquitetura.md) detalha os alvos e a comparação entre clocks.

## Experimentos, escrita e dependências

Planejar três repetições do mesmo replay por configuração, preservando bytes
e intervalos. Acrescentar captura GPS contínua com duração registrada; almejar
uma hora por configuração quando a bancada permitir. Guardar configuração,
recursos pós-fit, Fmax, slacks, latência em ciclos e µs, taxa útil, erros/perdas e
ocupação da FIFO. Latência USB/SO não é latência interna da FPGA.

Introdução, trabalhos relacionados e metodologia avançam durante os ensaios.
A contribuição é a avaliação experimental reprodutível da integração.

A Cyclone IV já possui um perfil e SOFs preparados, mas a aprovação do alvo
depende do acesso JTAG, da confirmação dos pinos e da medição física do clock.
Se algum ponto falhar, registrar o impedimento e revisar a execução com o
orientador; não tratar um SOF compilado ou replay sintético como bancada real.
A bancada fecha em 25/09; a redação ocorre em 26–27/09 e a
submissão/contingência fica em 29–30/09.
