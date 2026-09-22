# Validação da instrumentação anterior ao P04–P06 — 22/09/2026

Esta etapa prepara a bancada para produzir evidência repetível. Ela não altera
o caminho de dados UART/FIFO/AES-CTR e não conclui nenhum teste físico que ainda
estava pendente.

## Host PC com um CP2102

O host ativo é `scripts/serial_bench.py`, executado no PC através de um único
adaptador USB–TTL em nível lógico de 3,3 V. Para cada sequência `55 A5 00 FF 3C`,
ele transmite cinco bytes, aguarda a resposta por até 1 s, observa mais 10 ms
para detectar bytes tardios ou duplicados e grava um relatório JSON.

O modo `baseline` exige eco. O modo `secure` captura o ciphertext e o decifra
independentemente no PC com o contexto registrado. O host contabiliza timeout,
divergência, bytes faltantes e extras, mas não inventa flags de framing ou
overflow que o CP2102 não fornece; essas flags continuam sendo lidas nos LEDs
da FPGA e na instrumentação elétrica.

O mesmo adaptador atende a DE10-Lite e Cyclone IV. Para GPS, a referência é
capturada diretamente primeiro e depois reapresentada à FPGA pelo comando
`replay`, garantindo que a comparação use os mesmos bytes. O relatório inclui
tempo do host, que não é latência isolada da FPGA.

## Diagnósticos da Cyclone IV

Os quatro LEDs disponíveis nos tops integrados, todos ativos em nível baixo,
foram organizados da mesma forma no baseline e no secure:

| LED | Diagnóstico |
| --- | --- |
| `LED[0]` | heartbeat |
| `LED[1]` | contexto configurado / aquisição ativa |
| `LED[2]` | overflow persistente da FIFO |
| `LED[3]` | erro persistente de framing |

Os toggles de eventos RX/TX deixaram de ocupar LEDs. A atividade continua
observável na captura serial, enquanto overflow e framing permanecem visíveis
até reset/abort.

Não foram alterados clock, pinos, UART, FIFO, AES, CTR, força de saída ou slew
rate. O TX permanece em 8 mA. SignalTap também não foi incluído nos builds de
métricas.

## Verificações executadas

| Verificação | Resultado |
| --- | --- |
| `python3 -m unittest tb.test_serial_bench -v` | **PASS** — baseline e secure em porta serial virtual full-duplex |
| `make check` | **PASS** — repetido após a preparação DE10-Lite; 27 simulações, nove configurações de lint, síntese estrutural e 34 testes PC |
| `make integration` | **PASS** — 2.681 bytes por modo no ensaio acelerado, casos de 50 MHz/9600 e 34 testes PC na regressão atual |
| `make cyclone4-baseline-fpga` | **PASS** — SOF gerado e três cantos temporais aprovados; não programado nesta etapa |
| `make cyclone4-secure-fpga` | **PASS** — SOF gerado e três cantos temporais aprovados; não programado nesta etapa |
| `make cyclone4-metrics` | **PASS** |

Métricas pós-fit regeneradas:

| Métrica | Baseline | Secure |
| --- | ---: | ---: |
| Elementos lógicos | 299 | 5.580 |
| Registradores | 189 | 889 |
| Memória | 8.192 bits | 8.192 bits |
| Fmax mínima | 104,08 MHz | 83,56 MHz |
| Pior setup | 11,225 ns | 8,866 ns |
| Pior hold | 0,162 ns | 0,156 ns |

Os dois builds atendem ao clock de operação de 48 MHz. Esses números vêm do
Quartus e não constituem medição física.

## Próxima execução

1. Conectar o CP2102 em TXD→RX, RXD←TX e GND, sem aplicar 5 V aos GPIOs.
2. Reprogramar o SOF baseline e executar `serial_bench.py run` com quatro
   quadros; conferir `PASS`, 20 bytes e zero extras.
3. Repetir P04 com ponta ×10, entrada de 1 MΩ, acoplamento DC e massa curta.
4. Medir aproximadamente 104,17 µs por bit, 1,0417 ms por quadro de 10 bits e
   salvar as capturas de RX e TX.
5. Somente se duas capturas corretas ainda excederem `−0,3 V` a `3,6 V`, criar
   e comparar uma variante de 4 mA com slew lento.
6. Fechado o baseline, gerar contexto privado novo, reprogramar o secure e
   executar P05/P06 com o mesmo CP2102.
