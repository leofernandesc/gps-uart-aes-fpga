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
alto, por exemplo 3,3 V, em vez de GND; a ligação física precisa ser conferida
antes de atribuir valores de tensão ao pino TX.

O WaveForms aberto ocupa o dispositivo (`dwfcmd enumerate` retorna
`Is Busy?: YES`), e `dwfcmd connect` falha com `FDwfDeviceOpen` nessa condição.
Uma tentativa de executar um script na instância gráfica encerrou o WaveForms
com código 139, sem gerar CSV. O aplicativo foi reaberto normalmente e voltou
a reconhecer o AD2. Para a próxima captura, usar o Scope e a exportação CSV
pela própria interface, sem repetir a chamada de script que falhou.

Próximo passo: com a placa desligada, confirmar fisicamente `1+` no JP1 pino 2
(`W10`, TX) e `1−` no JP1 pino 12 ou 30 (GND; **não** pino 29, que é 3,3 V).
Após religar, repetir a captura e aceitar o nível elétrico somente se o
repouso ficar próximo de 3,3 V e os bits baixos próximos de 0 V. Esta medição
é da UART autônoma; baseline, secure e GPS integrados continuam pendentes.
