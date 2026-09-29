# Diagnóstico do P04 na DE10-Lite — 26/09/2026

Este registro é histórico e foi feito com a configuração serial anterior,
9600/8N1. Desde 29/09, a taxa ativa é 38400/8N1; resultados e temporizações
abaixo não comprovam o P04 na configuração final. O utilitário de diagnóstico
`scripts/ad2_uart_source.py` usa 38400 por padrão e aceita `--baud 9600` para
reproduzir este ensaio histórico.

## Montagem e interpretação

DE10-Lite `10M50DAF484@1`, clock de 50 MHz; CP2102 identificado em
`/dev/ttyUSB0` como USB `10c4:ea60`, UART 9600/8N1; AD2
`SN:210321A7FDB4`. CH1 mede diretamente o pino **TXD do CP2102**, que
estava ligado por jumper ao `V10` (RX da FPGA); CH2 mede `W10` (TX da FPGA).
Ambos usam GND comum. Não houve medida independente no metal de `V10`
durante esta rodada.

| Hora local | Ensaio | Observação |
| --- | --- | --- |
| 02:32 | Baseline integrado reprogramado e vetor `55 A5 00 FF 3C` enviado | 0/5 bytes recebidos pelo CP2102 em 1,501 s; `p04-echo-report.json` |
| 02:41 | `uart_scope.sof` programado; leitura passiva do CP2102 por 1,5 s | **15 bytes `0x55` recebidos**, provando o trecho `W10 → CP2102 RXD → PC` e a decodificação do host |
| 02:41 | Ponte histórica `uart_bridge.sof`, sem guarda de contexto | 0/5 no primeiro burst; `diagnostic-bridge-report.json` |
| 02:45 | SOF de continuidade `UART_TX = UART_RX` compilado e programado | Quartus: 0 erros, 3 avisos; JTAG: sucesso, checksum `0x002724A5`; `diagnostic-wire-report.json` retornou 0/5 |
| 02:46–02:50 | Bypass direto com `pyserial` | 0/5 em envio único; 0/250 em 50 bursts e 0/375 em 75 bursts |
| 02:50 | AD2 gravou 6 s a 250 kS/s por canal; durante a aquisição, o PC escreveu e escoou 500 bytes pela porta serial | **TXD do CP2102 permaneceu alto:** 3,2659–3,2882 V em 1.500.000 amostras; **W10 permaneceu alto:** 3,3102–3,3323 V em 1.500.000 amostras. Nenhuma amostra abaixo de 1,5 V. O envio ocorreu entre 02:50:54,150 e 02:50:56,716, dentro da janela iniciada às 02:50:53,149. A recepção foi 0/500. |
| 02:52 | Comando de break da porta serial durante captura | TXD e W10 continuaram altos, mas o AD2 advertiu possível perda de amostras; este ensaio é auxiliar. |
| 02:53 | `uart_scope.sof` programado; AD2 gravou 0,5 s a 250 kS/s sem enviar dados pelo PC | CH2/W10 teve pulsos até −0,045 V, com repetição de aproximadamente 100 ms; CH1/TXD permaneceu 3,2622–3,2882 V. Isso confirma que o instrumento detecta comutação em W10; TXD continuou ocioso. |
| 02:54 | `usbreset 001/023` no CP2102 e retorno ao SOF de continuidade | Dispositivo USB reconectado, mas novo teste `pyserial` retornou 0/5. |

O SOF de continuidade está em `build/de10_lite/wire_diag/uart_wire_diag.sof`
(SHA-256 `75047ed6334dc2a59dedb68665e237687a51f9841504f44c079aeca04a5f01f6`).
O projeto fonte fica em [`fpga/de10_lite/wire_diag/`](../fpga/de10_lite/wire_diag/README.md).
Os arquivos brutos abaixo foram preservados em `data/private/de10-2026-09-26/`:

| Arquivo | SHA-256 |
| --- | --- |
| `diagnostic-bridge-report.json` | `73e3146278feaa142433b5c84fa64ef6896260559cde7dd4f638308ccba2b4fa` |
| `diagnostic-wire-report.json` | `f8de3a589da1bbecddffbf640e3fec8e5d8db3710d552de19c002685145b1466` |
| `diagnostic-ad2-timed-ch1.csv` | `a32d7366af80ab45daba37e47071ec3e642be266d60b0136fb186a6b23ba40db` |
| `diagnostic-ad2-timed-ch2.csv` | `e3117f839ea2aa2ae4e28e6f852617600fa51e7c03affa536192b4818752f123` |
| `diagnostic-scope-ch1.csv` | `c5c05792a38d283260aa4aeaf5e65a545b8333f41b3b69dfe565863994435784` |
| `diagnostic-scope-ch2.csv` | `64e7d4f381918cf6b047b8bdf209b1ad1aafa281a0f63bf77d53913d83d18be7` |

## Conclusão atual e próximo teste

No ensaio de continuidade, o FPGA apenas espelha `V10` em `W10`; portanto,
o retorno 0/5 não pode ser causado pelo AES, pela FIFO ou pelo receptor UART.
Durante um envio confirmado pelo sistema operacional, não houve transições
no próprio **TXD do CP2102**. Isso afasta a hipótese de que apenas o jumper
TXD→V10 tenha interrompido os pulsos: a saída do adaptador não os forneceu
na medição atual. A causa exata da ausência de comutação do TXD ainda não está
determinada. O sucesso anterior de P03 não altera a observação atual.

Próximo ensaio: substituir temporariamente a fonte UART pelo DIO0 do AD2,
**retirando antes** o fio CP2102 TXD→V10 para evitar dois drivers no mesmo
nó. Manter `W10→CP2102 RXD` e o GND comum. Somente após observar quadros em
V10 e o eco byte a byte se repete P04 no baseline integrado. P04 permanece
**pendente**; os dados acima são diagnóstico físico, não validação do artigo.

### Ensaio de substituição da fonte UART

O AD2 fornece saída digital DIO0 em 3,3 V
([manual oficial](https://files.digilent.com/manuals/WaveForms/3.24.3/start3.html#digital-io)).
Com `wire_diag.sof` programado,
WaveForms fechado e apenas `DIO0→V10`, `W10→CP2102 RXD` e GND comum:

```bash
python3 scripts/ad2_uart_source.py --design wire_diag \
  --confirm-txd-disconnected \
  --report data/private/de10-2026-09-26/ad2-wire-echo.json
```

O script, em sua versão desta época, enviava `55 A5 00 FF 3C` em 9600/8N1 pelo DIO0 e compara os bytes
capturados pelo CP2102. Se passar, programar o baseline integrado e repetir
com `--design baseline` e outro relatório. A confirmação da desconexão de
TXD é uma barreira de segurança: nunca ligar DIO0 e CP2102 TXD juntos em
V10. Se falhar, medir DIO0 e V10 para localizar o sinal antes de atribuir a
falha ao UART em RTL.

#### Resultado parcial — 03:07–03:10 (Manaus)

Com TXD do CP2102 retirado de V10, DIO0 ligado a V10 conforme montagem e
`wire_diag.sof` ainda programado, o primeiro envio AD2 de `55 A5 00 FF 3C`
retornou **0/5 bytes** pelo RXD do CP2102. A captura simultânea de V10 (CH1)
e W10 (CH2) a 250 kS/s, 8.192 amostras/canal, na faixa analógica de 10 V,
registrou V10 entre **3,2622–3,2807 V** e W10 entre **3,3065–3,3249 V**,
sem nenhuma amostra abaixo de 1,5 V. O ensaio inicial na faixa de 5 V
achatou a leitura para aproximadamente 2,77 V e não é usado para inferir o
nível lógico. O relatório da captura válida é
`data/private/de10-2026-09-26/ad2-wire-scope-range10-report.json`
(SHA-256 `6e5f494776f1b90d1eb3791bea711c9e747141e172bb6baa8b99f2e4b17be217`)
e o CSV é `ad2-wire-v10-w10-range10.csv`
(SHA-256 `efab7dde1c53c2b5261f6e849c265b032416cc7916ebeb814581b7a386c77ab2`).

No teste estático independente, `scripts/ad2_dio_probe.py` comandou DIO0
alto→baixo→alto. A leitura digital do próprio AD2 seguiu **1→0→1**, mas CH1
em V10 permaneceu em **3,27–3,28 V** e CH2 em W10 em **3,31–3,33 V**. Isso
indica que o nível baixo não foi observado no ponto de medida V10; ainda é
preciso distinguir saída física DIO0, terminal/fio e contato em V10. **Não**
é evidência de defeito no RTL da UART. O próximo passo é medir o próprio
terminal DIO0 com CH1, mantendo o fio para V10, antes de alterar bitstream ou
pinagem.

Às 03:12, com CH1 movido para o terminal identificado na bancada como DIO0,
o teste alto→baixo→alto repetiu a leitura digital interna **1→0→1**, porém
CH1 permaneceu em **3,240–3,244 V** e W10 em **3,310–3,321 V**. Relatório:
`data/private/de10-2026-09-26/ad2-dio0-terminal-probe.json`
(SHA-256 `dff205e6b5dfd0bbe5af0c48e33bce887d61e9c0d7ab264a830af12381d58aea`).
Essa divergência entre readback interno e ponta externa exige conferir qual
fio/terminal está sendo medido, o encaixe do flywire e a continuidade até V10.
O [pinout oficial do AD2](https://digilent.com/reference/_media/reference/test-and-measurement/analog-discovery-2/ad2_rm.pdf)
mostra DIO0 imediatamente após T1 na fileira de `1+`, `2+`, GND, V+, W1,
GND, T1, 0–7. Ainda não há base para atribuir defeito ao FPGA ou concluir P04.

Uma segunda implementação do teste estático, o utilitário Digilent `dwfcmd`,
com `digitalio oe=0x1 out=0x0`, leu `Digital In=0x0000`, mas o voltímetro
analógico do AD2 registrou **CH1=3,229 V** no terminal indicado como DIO0 e
**CH2=3,314 V** em W10. Portanto, o contraste não depende apenas de
`scripts/ad2_dio_probe.py`. A etapa seguinte é medir esse terminal também
com multímetro independente enquanto DIO0 é mantido baixo.
