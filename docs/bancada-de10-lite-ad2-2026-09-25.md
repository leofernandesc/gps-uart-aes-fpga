# DE10-Lite + Analog Discovery 2 — 25/09/2026

## Captura preliminar da UART autônoma

A DE10-Lite foi programada por JTAG com `build/de10_lite/uart_scope/uart_scope.sof`
(SHA-256 `896fe582066ca366dc188046a0bf73305eba9ac47c10a22710f8934acdc758aa`).
O Quartus Programmer informou configuração bem-sucedida do `10M50DAF484@1`,
sem erros ou avisos. O AD2 foi enumerado como `SN:210321A7FDB4`.

Com o WaveForms fechado, `dwfcmd` gravou 8.192 amostras do canal analógico 1
em modo single, taxa efetiva de 3,030 MHz, disparo na borda de descida a
−1,3 V. O arquivo bruto está em
[`evidence/de10-lite-uart-scope-ad2-2026-09-25.csv`](evidence/de10-lite-uart-scope-ad2-2026-09-25.csv)
(SHA-256 `a21564f079aa8239c261771c53b64676d0a5b227fe3eedf379c3a0dbfb290616`).
É uma coluna de tensão em volts, sem timestamps; a amostra 0 corresponde ao
início da janela de 2,703 ms.

O quadro completo foi observado: start baixo, dados LSB-first `0x55` e stop
alto. Os intervalos entre as transições sucessivas foram de 315–316 amostras,
ou aproximadamente 104 µs por bit. Uma aquisição mais longa mostrou repetição
dos quadros com separação próxima de 100 ms. Isso confirma a temporização e a
sequência de bits do TX autônomo, mas **não** conclui a medição de níveis
elétricos: a aquisição foi de aproximadamente 0 V em repouso a −2,77 V nos
pulsos. A interpretação provável é referência diferencial ligada a um nível
alto, por exemplo 3,3 V, em vez de GND; esta era uma hipótese inicial, não
uma conclusão sobre a ligação. A causa confirmada depois foi o acoplamento AC
no adaptador BNC, descrito abaixo.

### Referência DC medida com o WaveForms

Com o canal 1 ligado à saída fixa de 3,3 V da DE10-Lite, o usuário mediu
**3,3 V no multímetro** e mostrou o Voltmeter do WaveForms indicando
`C1 = −17,2 mV`, `C1RMS = 17,3 mV` e `C1AC = 1,3 mV`. A
[imagem do instrumento](evidence/de10-lite-ad2-3v3-voltmeter-2026-09-25.png)
foi preservada com SHA-256
`52f821cb386eb9ddc6dcfca10ae67adfea4c3ae0cb85d201bfd8d54b4ef0ffe1`.
O valor do multímetro foi comunicado pelo usuário; não foi registrado por uma
interface ligada ao computador. Ele confirmou também que `1+`, `1−` e o GND
próprio do AD2 estão ligados aos pontos pretendidos.

O conjunto `3,3 V DC → ~0 V no AD2` e `UART → pulsos negativos a partir de
~0 V` é compatível com **acoplamento AC**. Segundo a documentação da Digilent,
o adaptador BNC do Analog Discovery tem jumper físico AC/DC e pode vir em AC
por padrão: <https://files.digilent.com/manuals/WaveForms/3.25.1/startadbnc.html>.
O usuário identificou o jumper azul sobre os pinos **AC + central**, moveu-o
para **central + DC** e passou a ler **3,3 V** no Voltmeter do WaveForms no
mesmo ponto da placa. Isso confirma a causa da supressão do nível DC na
captura anterior. A leitura corrigida foi comunicada pelo usuário; uma nova
imagem ou CSV com o jumper em DC ainda não foi preservada. `C1AC` na tela é a
medida de componente AC, não uma indicação da posição do jumper.

Como a placa foi desligada para trocar o jumper, o SOF JTAG anterior foi
perdido. Às 23:08 de 25/09, `quartus_pgm` reprogramou `uart_scope.sof` pelo
`USB-Blaster [1-3]`; identificou `10M50DAF484@1`, JTAG ID `0x031050DD` e
informou `Configuration succeeded`, 0 erros e 0 avisos. A programação não
equivale à nova medição elétrica do TX.

O WaveForms aberto ocupa o dispositivo (`dwfcmd enumerate` retorna
`Is Busy?: YES`), e `dwfcmd connect` falha com `FDwfDeviceOpen` nessa condição.
Uma tentativa de executar um script na instância gráfica encerrou o WaveForms
com código 139, sem gerar CSV. O aplicativo foi reaberto normalmente e voltou
a reconhecer o AD2. Para a próxima captura, usar o Scope e a exportação CSV
pela própria interface, sem repetir a chamada de script que falhou.

## Captura da UART autônoma com o canal em DC

O workspace `TesteAD2UART.dwf3work`, salvo às 23:15 de 25/09, contém dez
aquisições de 8.192 amostras por canal. O canal 1 da aquisição 6 contém um
quadro UART completo; as demais aquisições ficaram em repouso alto. O arquivo
original foi preservado em
[`evidence/de10-lite-uart-scope-ad2-dc-2026-09-25.dwf3work`](evidence/de10-lite-uart-scope-ad2-dc-2026-09-25.dwf3work)
(SHA-256 `9fdc4c2b0c8ceb0410ca7ab0d7ccadf7dbb63301e15d7f880a5cb117ebc5cfb2`).
As amostras do canal 1 foram extraídas sem alterar o original para
[`evidence/de10-lite-uart-scope-ad2-dc-2026-09-25.csv`](evidence/de10-lite-uart-scope-ad2-dc-2026-09-25.csv)
(SHA-256 `b3dc2c2a771e882ca3802ea17c3c1c9085ef78e90e8f0eabd203be2274650264`).
O CSV contém índice, tempo em µs desde a primeira amostra e tensão em V.
A extração interpretou a entrada comprimida `/scope0buffer/6.0.data` como
8.192 valores `float64` little-endian e conferiu a taxa no campo `.info`
correspondente; essa interpretação é corroborada pela configuração salva e
pelo quadro UART observado.

Os metadados da aquisição informam taxa real de **3,125 MHz**, ou 0,32 µs
por amostra; a janela de 8.192 amostras dura **2,62144 ms**. O canal 1
estava configurado com atenuação `1×`; o arquivo indica acoplamento DC, e o
jumper físico do adaptador BNC já havia sido movido para DC. O trigger do
workspace ainda estava em modo automático, borda de subida e 0 V; não é uma
captura disparada pelo start bit, embora o quadro esteja completo na janela.

| Medida | Resultado no canal 1 |
| --- | ---: |
| Repouso/nível alto, mediana das amostras acima de 1,65 V | **3,308 V** |
| Nível baixo, mediana das amostras abaixo de 1,65 V | **−0,072 V**, próximo de GND |
| Extremos da aquisição | −0,101 a 3,360 V |
| Transições sucessivas | 325 ou 326 amostras |
| Período médio entre nove transições | **104,18 µs/bit** |
| Taxa serial derivada | aproximadamente **9.599 baud** |
| Quadro | start `0`, dados LSB-first `10101010`, stop `1` |
| Byte decodificado | **`0x55`** |

Os dez bits amostrados nos centros são `0 | 1 0 1 0 1 0 1 0 | 1`.
O tempo de um quadro 8N1, inferido de dez períodos, é aproximadamente
**1,042 ms**. A pequena leitura negativa no patamar baixo é uma leitura do
instrumento; ela não indica que o FPGA produza alimentação negativa. A
captura em DC confirma os níveis e a temporização do **TX da UART autônoma**
na DE10-Lite e complementa o teste de repetição e loopback de 18/09.

Esta janela de 2,62 ms contém apenas um quadro e não mede o intervalo de
100 ms entre quadros, taxa de erro em longa duração, FIFO, AES-CTR ou GPS.
P03–P11 dos sistemas integrados continuam dependentes dos seus próprios
ensaios físicos. Para capturas subsequentes, configurar trigger na borda de
descida do canal 1 em aproximadamente 1,6 V facilita enquadrar o start bit.
