# Alvo Cyclone IV

O pacote Cyclone IV já foi adicionado ao Quartus Lite 25.1 deste computador.
O alvo de bancada aguarda a identificação da placa em 15/09/2026.

Registrar antes de criar QSF/SDC e gerar um SOF:

| Informação | Situação |
| --- | --- |
| Fabricante/modelo e revisão da placa | A confirmar |
| Código completo da FPGA e speed grade | A confirmar |
| Frequência do oscilador e pino do clock | A confirmar |
| GPIO RX/TX, alimentação dos bancos e GND | A confirmar |
| Reset e LEDs disponíveis | A confirmar |
| Esquema/manual da placa | A confirmar |

Cyclone IV é uma família de dispositivos, não uma frequência de clock.
O EP4CE22F17C6 usado na checagem da instalação do pacote não identifica a placa
do experimento. Nenhuma pinagem ou frequência hipotética deve ser programada.

## Como acrescentar a placa

1. Criar um wrapper de placa que instancie `rtl/uart/uart_scope.sv`, com
   `CLK_FREQ` igual ao oscilador real e `BAUD_RATE=9600`.
2. Elaborar QSF/SDC próprios. O período SDC é `1e9 / CLK_FREQ` em ns.
   Selecionar o pino dedicado de clock, I/O e reset a partir do manual.
3. Acrescentar o alvo ao dispatch de `scripts/quartus_build.sh`; gravar as saídas
   em `build/cyclone4/uart_scope/` e adaptar a auditoria ao número de portas e
   modelos temporais desse dispositivo. Não copiar exceções cegamente.
4. Simular a temporização com o clock confirmado, compilar e testar a UART com
   osciloscópio/jumper antes do experimento GPS.
5. Criar projetos `baseline/` e `secure/` com o mesmo RTL integrado do MAX 10,
   mesma FIFO, controle e instrumentação. Incluir o AES apenas em `secure` por
   elaboração; um bypass em execução não mede a remoção do hardware AES.

As duas plataformas devem permanecer na `main`. Usar uma branch temporária
para o suporte à placa, revisar os resultados e integrar os commits. Não
manter cópias divergentes de UART/AES por família.

Até o alvo existir, `make uart-fpga BOARD=cyclone4` retorna erro explícito,
sem compilar silenciosamente para a DE10-Lite.
