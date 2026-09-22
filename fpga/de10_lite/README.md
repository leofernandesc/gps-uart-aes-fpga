# Projetos da DE10-Lite

Há três alvos Quartus para a placa:

| Alvo | Função | Comando | SOF |
| --- | --- | --- | --- |
| `uart_scope` | UART autônoma que gera `0x55`, usada no osciloscópio e loopback | `make uart-fpga` | `build/de10_lite/uart_scope/uart_scope.sof` |
| `baseline` | UART RX → FIFO → UART TX, sem AES | `make baseline-fpga` | `build/de10_lite/baseline/uart_baseline.sof` |
| `secure` | UART RX → FIFO → AES-128-CTR → UART TX | `make secure-fpga` | `build/de10_lite/secure/uart_secure.sof` |

O projeto `uart_bridge` antigo continua disponível com `make fpga` como
referência. Ele não é um dos dois tops usados na comparação final do artigo.

Todos os alvos usam 50 MHz, 9600 baud, 8N1 e FIFO de 1.024 bytes. Compilar não
exige a placa; programar e validar os sinais externos exigem a montagem real.
O [plano de testes](../../docs/plano-de-testes.md) registra resultados de
simulação, Quartus e bancada.

## Pinagem comum

| Sinal | Recurso da DE10-Lite | Pino FPGA | Uso |
| --- | --- | --- | --- |
| `MAX10_CLK1_50` | Oscilador de 50 MHz | P11 | Clock interno |
| `KEY0_N` | Botão KEY0 | B8 | Reset ativo baixo |
| `UART_RX` | GPIO[0], pino físico 1 de JP1 | V10 | Entrada serial do GPS/fonte de teste |
| `UART_TX` | GPIO[1], pino físico 2 de JP1 | W10 | Saída serial |
| GND | Pino físico 12 ou 30 de JP1 | — | Referência comum |

Fonte: manual da **Terasic**, edição de 05/06/2020, pp. 5, 24–27 e 30–31
([PDF hospedado pela Mouser](https://www.mouser.com/datasheet/2/598/DE10-Lite_User_Manual-1100361.pdf)).
Confirmar a orientação do pino 1 na placa e a pinagem do conector do módulo
NEO-M8N-010 antes de ligar o GPS.

Os sinais usam I/O de 3,3 V; KEY0 usa o padrão Schmitt Trigger da placa. A RX
tem pull-up fraco para manter repouso quando desconectada. UART e LEDs usam
força de saída explícita de 8 mA.

## Configuração dos tops integrados

Após o reset, os tops `baseline` e `secure` carregam automaticamente um contexto
de elaboração por `cfg_valid/cfg_ready`. Os parâmetros `CONTEXT_KEY`,
`CONTEXT_NONCE` e `CONTEXT_COUNTER` podem ser substituídos em um build privado;
os valores padrão são apenas para o primeiro bring-up:

```text
key      = 000102030405060708090a0b0c0d0e0f
nonce    = 101112131415161718191a1b
counter  = 00000001
```

Isso não é um protocolo de configuração pela UART nem gerenciamento de chaves.
Para aplicar um JSON privado ao build secure, use `CONTEXT_FILE`:

```bash
CONTEXT_FILE=data/private/ensaio01/contexto.json make secure-fpga
```

Para o baseline, use um contexto criado com `--mode baseline` e
`make baseline-fpga`. O script gera `context_params.sv` em `build/` com
permissão `0600`; não há transferência pela UART nem provisão em tempo de
execução. Sem `CONTEXT_FILE`, o build copia o contexto público de bring-up.
O baseline fixa `ENABLE_AES=0` na elaboração; o secure fixa `ENABLE_AES=1`.

## Indicadores dos tops integrados

| LED | Significado |
| --- | --- |
| 0 | Heartbeat da placa |
| 1 | Aquisição configurada/ativa |
| 2 | Alterna a cada byte recebido |
| 3 | Alterna a cada quadro transmitido |
| 4 | TX ocupado |
| 5 | Configuração concluída |
| 6 | Overflow da FIFO |
| 7 | Erro de framing |
| 8 | FIFO contém dados |
| 9 | FIFO atingiu alta ocupação ou contexto CTR esgotou |

Os LEDs são diagnóstico visual; não substituem captura binária nem contagem de
bytes no PC.

## Procedimento físico

1. Compilar o alvo escolhido e confirmar a cadeia MAX 10 antes de programar o
   `.sof` por JTAG.
2. Manter a fonte UART inativa até a configuração e o carregamento do contexto.
3. Para `baseline` ou `secure`, apresentar uma sequência UART de teste em V10.
4. Observar a retransmissão em W10 e verificar LEDs 6 e 7 apagados.
5. Medir no osciloscópio o quadro 8N1, o período de aproximadamente 104,17 µs
   por bit e, com dois canais, a latência entre RX e TX.
6. Não pressionar KEY0 depois do primeiro byte. O contexto é de uso único e um
   reset nesse ponto exige reprogramar o SOF antes de uma nova captura.
7. Repetir com o GPS depois de concluir os bytes conhecidos.

Comandos, pinagem do ESP32, vetores esperados e campos de evidência estão no
[roteiro integrado de 22/09](../../docs/bancada-de10-lite-integrada-2026-09-22.md).

O `uart_scope` é o único alvo que transmite sem uma fonte externa: ele envia
`0x55` a cada 100 ms. O roteiro e os resultados desse ensaio estão em
[`uart_scope/README.md`](uart_scope/README.md) e em
[`docs/bancada-de10-lite-2026-09-18.md`](../../docs/bancada-de10-lite-2026-09-18.md).

## Interface da FIFO e da ponte

`sync_fifo` aceita escrita quando há espaço, inclusive no ciclo de leitura de
uma fila cheia. A leitura entrega `rd_data` com `rd_valid` após a borda; os
testes cobrem ordem, colisão, overflow, reset e pausa do TX.

`uart_ctr_bridge` reserva o TX enquanto aguarda a leitura síncrona da FIFO e só
avança a máscara CTR quando o byte é aceito pelo estágio seguinte. Framing,
overflow, abort e reset invalidam a captura. A FIFO não pausa o GPS nem
compensa indefinidamente uma entrada cuja taxa média exceda a saída.

## Alcance da análise temporal

O SDC define o clock de 20 ns e exceções apenas para a entrada assíncrona até
os primeiros registradores de sincronização e para as saídas UART/LED. RX
meta→sync e a liberação interna do reset continuam sujeitos a timing.

O script verifica setup, hold, recovery e removal nos três cantos disponíveis,
falha com slack negativo/cobertura ausente e registra os relatórios em
`build/de10_lite/<configuracao>/`.
