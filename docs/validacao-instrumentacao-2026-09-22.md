# Validação da instrumentação anterior ao P04–P06 — 22/09/2026

Esta etapa prepara a bancada para produzir evidência repetível. Ela não altera
o caminho de dados UART/FIFO/AES-CTR e não conclui nenhum teste físico que ainda
estava pendente.

## Host ESP32

O host em `bench/esp32_uart_host_idf` passou a usar a fila de eventos do driver
UART2. Para cada sequência `55 A5 00 FF 3C`, ele:

- aceita os cinco bytes esperados por até 30 ms;
- observa mais 10 ms para detectar bytes tardios ou duplicados;
- no fluxo nominal, limpa a entrada apenas uma vez, antes do primeiro ensaio;
- inicia tentativas a cada 1 s com `vTaskDelayUntil`;
- contabiliza timeout, divergência, bytes extras, framing, paridade, overflow,
  buffer cheio, break, falha de escrita e timeout do TX;
- emite linhas estruturadas `RESULT` e `SUMMARY`.

Em caso de overflow ou buffer cheio, o host limpa o RX e reinicia a fila de
eventos como recuperação explícita; esse evento continua contabilizado no log.

O modo `baseline` exige eco. O modo `secure` captura o ciphertext sem contar a
diferença em relação ao plaintext como erro; a aprovação depende da decifragem
independente no PC. O campo `host_window_us` inclui driver e escalonamento do
ESP32 e não pode ser usado como latência física da FPGA.

As duas opções do Kconfig — baseline e secure — foram compiladas com ESP-IDF
6.0.2. A gravação no ESP32 e a observação dos novos logs pertencem à próxima
execução física.

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
| `idf.py build`, modo baseline | **PASS** |
| `idf.py build`, modo secure | **PASS** |
| `make check` | **PASS** — 27 simulações, nove configurações de lint, síntese estrutural e 31 testes PC |
| `make integration` | **PASS** — 2.681 bytes por modo no ensaio acelerado, casos de 50 MHz/9600 e 31 testes PC |
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

1. Gravar o firmware ESP32 em modo baseline e reprogramar o SOF baseline.
2. Confirmar três linhas `RESULT` consecutivas com cinco bytes, `same=1` e
   todos os contadores de erro em zero.
3. Repetir P04 com ponta ×10, entrada de 1 MΩ, acoplamento DC e massa curta.
4. Medir aproximadamente 104,17 µs por bit, 1,0417 ms por byte e 5,208 ms para
   os cinco bytes; salvar a captura de RX e TX.
5. Somente se duas capturas corretas ainda excederem `−0,3 V` a `3,6 V`, criar
   e comparar uma variante de 4 mA com slew lento.
6. Fechado o baseline, gerar contexto privado novo e executar P05/P06 secure.
