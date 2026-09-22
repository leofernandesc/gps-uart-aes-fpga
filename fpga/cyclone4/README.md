# Alvo Cyclone IV — ZRTech/WXEDA V2.00

O pacote Cyclone IV já foi adicionado ao Quartus Lite 25.1 deste computador.
A placa recebida corresponde ao perfil **ZRTECH V2.00 / DESIGNED BY WXEDA**, com
FPGA **EP4CE6E22C8N**. A memória marcada `W9864G6KH-6` é uma SDRAM externa de
64 Mbit e não participa da UART/AES deste projeto.

O perfil de 48 MHz em `PIN_24` foi confirmado funcionalmente pelo bit time de
aproximadamente 104 µs a 9600 baud. Como os pinos UART da referência pública
não estão acessíveis no header usado, a bancada validou `PIN_103` como RX e
`PIN_100` como TX no J3. A marca `YXC 12.0...` observada na placa pertence a
outro circuito e não é usada como clock da FPGA neste projeto.

## Perfil preparado para a bancada

| Informação | Situação |
| --- | --- |
| Fabricante/modelo e revisão da placa | **ZRTECH/WXEDA V2.00** |
| Código completo da FPGA e speed grade | **EP4CE6E22C8N** — Cyclone IV E, EQFP-144, comercial, speed grade 8 |
| Frequência e pino do clock | **48 MHz / PIN_24 — confirmado pelo TX físico** |
| UART RX/TX da bancada | **RX J3 PIN_103 / TX J3 PIN_100 — validados** |
| Reset ativo baixo | **PIN_89 — usado nos SOFs de bancada** |
| LEDs de usuário | **PIN_1, PIN_2, PIN_3 e PIN_144 — ativos em 0** |
| Alimentação e GND dos headers | I/O de 3,3 V e GND comum confirmados para a bancada UART |
| Esquema/manual da placa | Não localizado; referências públicas arquivadas no roteiro de bancada |

Cyclone IV é uma família de dispositivos, não uma frequência de clock. O
`EP4CE6E22C8N` identifica o FPGA, mas não identifica sozinho a placa nem seus
conectores. O `EP4CE22F17C6` usado na checagem da instalação do pacote não é o
dispositivo da bancada. Os ensaios P01–P03 comprovaram programação, TX,
loopback e baseline externo; eles não substituem os ensaios secure nem a
aquisição física do NEO-M8N.

## Capacidade e revisão de área

O EP4CE6 tem 6.272 elementos lógicos, 270 Kbits de RAM, 15 multiplicadores
18 × 18 e duas PLLs.
[Manual oficial](https://docs.altera.com/api/khub/documents/8ZIWxPYpX_ESk1aWBAaflA/content).

Em 20/09, o estudo de capacidade do RTL otimizado registrou 351 LE/216
registradores no baseline e 5.626 LE/917 registradores no secure, dentro dos
6.272 LE disponíveis. Esses números eram exploratórios, sem I/O físico; os
builds de bancada preparados agora devem substituir essa evidência.

Com o clock de 48 MHz, a UART usa 5.000 ciclos por bit a 9600
baud e período SDC de 20,833333 ns. A DE10-Lite permanece em 50 MHz; não há
cópia divergente de UART/AES por família.

## Projetos preparados

Os alvos abaixo já foram acrescentados ao fluxo:

| Alvo | Função | Comando | Saída |
| --- | --- | --- | --- |
| `uart_scope` | `0x55` periódico, osciloscópio e loopback | `make cyclone4-uart-fpga` | `build/cyclone4/uart_scope/uart_scope.sof` |
| `j3_scope` | `0x55` periódico, TX/RX no J3 `PIN_100`/`PIN_103` | `make cyclone4-j3-uart-fpga` | `build/cyclone4/j3_scope/uart_scope_j3.sof` |
| `baseline` | UART RX → FIFO → UART TX, sem AES | `make cyclone4-baseline-fpga` | `build/cyclone4/baseline/uart_baseline.sof` |
| `secure` | UART RX → FIFO → AES-CTR → UART TX | `make cyclone4-secure-fpga` | `build/cyclone4/secure/uart_secure.sof` |

Os três usam 48 MHz, 9600 baud, 8N1 e o mesmo RTL
compartilhado da DE10-Lite. O `baseline` remove o AES na elaboração; não é um
bypass em tempo de execução.

Nos tops integrados, os quatro LEDs ativos em nível baixo têm a mesma função no
baseline e no secure: `LED[0]` heartbeat, `LED[1]` configuração/atividade,
`LED[2]` overflow persistente da FIFO e `LED[3]` erro persistente de framing.
Os antigos toggles RX/TX foram retirados desse conjunto limitado; os eventos de
dados continuam observáveis na captura serial.

## Como acrescentar ou corrigir a placa

1. Confirmar o componente do clock e a frequência real. O período SDC é
   `1e9 / CLK_FREQ` em ns.
2. Confirmar no manual, serigrafia ou continuidade os pinos de clock, reset,
   RX, TX, LEDs, 3,3 V e GND. Não confundir o cristal de 12 MHz do USB–UART
   com o clock da FPGA.
3. Ajustar os QSF/SDC próprios, mantendo as saídas em `build/cyclone4/` e a
   auditoria temporal separada das métricas da DE10-Lite.
4. Compilar e testar `uart_scope` com osciloscópio/jumper antes do GPS.
5. Programar `baseline` e `secure`, executar os testes P03–P11 e coletar os
   recursos/timing de cada build.

As duas plataformas permanecem na `main`. Não manter cópias divergentes de
UART/AES por família. A pinagem validada foi separada dos módulos comuns para
que qualquer revisão elétrica altere somente os wrappers/QSF/SDC da Cyclone IV.

## Referências do perfil

- [Pin list pública do perfil EP4CE6E22C8N USB V2](https://land-boards.com/blwiki/index.php?title=Cyclone_IV_FPGA_EP4CE6E22C8N_Development_Board_USB_V2)
- [Referência de placa ZRTech/WXEDA e recursos](https://github.com/abbati-simone/Yoshis-Nightmare-Altera)
- [Fabricante YXC de cristais/osciladores](https://www.yxcxtal.com/)
