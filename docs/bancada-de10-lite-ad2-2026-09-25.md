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
uma conclusão sobre a ligação. O teste DC abaixo aponta outra possibilidade.

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
Isso **ainda não está confirmado**, pois é preciso identificar se esse
adaptador está sendo usado e observar a posição do jumper. `C1AC` na tela é a
medida de componente AC, não uma indicação da posição do jumper.

O WaveForms aberto ocupa o dispositivo (`dwfcmd enumerate` retorna
`Is Busy?: YES`), e `dwfcmd connect` falha com `FDwfDeviceOpen` nessa condição.
Uma tentativa de executar um script na instância gráfica encerrou o WaveForms
com código 139, sem gerar CSV. O aplicativo foi reaberto normalmente e voltou
a reconhecer o AD2. Para a próxima captura, usar o Scope e a exportação CSV
pela própria interface, sem repetir a chamada de script que falhou.

Próximo passo: identificar se a entrada do canal 1 passa por um adaptador BNC.
Se sim, com a placa desligada, colocar o jumper CH1 em **DC** e repetir a
leitura do pino JP1 29; o esperado é cerca de +3,3 V. Se forem usados fios
diretos, medir com o multímetro entre os próprios contatos de `1+` e `1−` e
revisar a configuração do canal. Só depois devolver `1+` ao JP1 pino 2
(`W10`, TX) e repetir a captura. Esta medição é da UART autônoma; baseline,
secure e GPS integrados continuam pendentes.
