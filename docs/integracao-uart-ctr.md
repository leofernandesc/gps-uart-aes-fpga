# Integração UART–FIFO–AES-CTR

O módulo `rtl/bridge/uart_ctr_bridge.sv` conecta os blocos existentes sem alterar
a UART isolada nem a ponte de bancada. A mesma fonte atende às duas variantes:
`ENABLE_AES=0` remove o AES na elaboração; `ENABLE_AES=1` inclui o CTR.
Clock, FIFO, retenção de byte e diagnósticos permanecem comuns.

## Caminho dos bytes

```text
UART RX → FIFO síncrona → byte retido → passagem direta / AES-CTR → UART TX
```

A FIFO padrão tem 1.024 posições. Sua leitura tem resposta síncrona de um
ciclo. `read_pending` reserva o registrador antes de solicitar a leitura;
`held_data` e `held_valid` guardam a resposta até o aceite do estágio seguinte.
Assim, uma pausa do TX não perde o pulso `rd_valid` nem repete um byte.

O handshake do CTR coincide com a aceitação de um novo quadro pelo TX. Só
nessa borda a posição na máscara avança. `tx_enable=0` impede iniciar outro
quadro, mas deixa o quadro em andamento terminar. Isso não para o GPS: uma
pausa prolongada pode esgotar a FIFO. O registrador de retenção e o quadro em
transmissão são reservas adicionais, não posições contabilizadas em `fifo_level`.

## Configuração e controle

| Interface | Comportamento |
| --- | --- |
| `cfg_valid && cfg_ready` | Aceita chave, nonce e contador e habilita a aquisição |
| `cfg_done` | Chave preparada no secure; confirmação de aceite no baseline |
| `active` | Aquisição habilitada; não significa máscara pronta ou FIFO vazia |
| `tx_enable` | Permissão para iniciar o próximo quadro; não aborta o atual |
| `abort_req` | Cancela o contexto, o TX e os bytes pendentes; limpa flags de erro |
| `exhausted` | No secure, todas as máscaras permitidas foram consumidas |
| `rx_event`, `tx_event` | Byte RX válido e conclusão de um quadro TX, respectivamente |
| `fifo_level`, `fifo_high_water` | Ocupação atual e máxima da RAM; máximo preservado após falha/abort |
| `overflow_sticky`, `framing_sticky` | Falha persistente até abort ou reset |

Não há configuração por comandos UART, parser NMEA ou contador de comprimento
de aquisição. A interface `cfg_*` reaproveita o contrato do CTR; é uma interface
RTL, **não uma conexão já implementada entre o PC e a placa**. O wrapper de
bancada ainda precisa carregar os parâmetros e comandar o início. Registrar
chave/nonce num JSON no PC, sozinho, não configura a FPGA.

Sequência de um ensaio:

1. Criar um contexto novo com `scripts/context.py` e registrar seus parâmetros no PC.
2. Iniciar os dois canais de captura antes de habilitar a fonte/replay.
3. Com a entrada ociosa em nível alto, apresentar `cfg_*` até o handshake.
4. Aguardar `cfg_done` e pelo menos um bit ocioso para sincronizar o RX.
5. Liberar a fonte e capturar N bytes de referência e de saída.
6. Conferir flags, salvar evidências e comparar os arquivos no PC.

Não há garantia de alinhamento ao iniciar no meio de um fluxo GPS contínuo;
esse procedimento deverá ser resolvido no wrapper e no roteiro físico. A
configuração não pode mudar enquanto `active=1`. Após abort, aguardar
`cfg_ready`: uma operação AES em andamento termina internamente e é descartada.

## Falhas e reset

Erro de stop ou escrita rejeitada por FIFO cheia interrompe a aquisição,
descarta bytes pendentes e cancela o contexto CTR. As flags ficam retidas e
bloqueiam nova configuração até um abort/reset explícito. O TX pode ser
interrompido no meio do quadro: a captura inteira é inválida, não apenas esse
byte. O erro é identificado antes de consumir outro byte da máscara.

O esgotamento do contador é diferente: o último quadro permitido termina
normalmente. Não se gera a máscara seguinte e um byte excedente fica parado;
nunca se volta ao contador zero. A captura deve respeitar o limite previsto
no contexto. Para continuar, abortar e configurar um nonce novo.

`rst` deve vir de um sincronizador de reset do wrapper. O sinal registrado
`active` mantém RX, FIFO, retenção e TX em reset quando a aquisição está
desabilitada. A liberação acontece na borda do clock comum; os caminhos de
recovery/removal dessa habilitação precisam ser auditados no Quartus integrado.
Os resultados de timing dos tops antigos não cobrem esse circuito novo.

## Validação sem placa

`make integration` executa os dois modos em simulação acelerada e em
50 MHz/9600, lint, checagem estrutural e comparação independente no PC. O
verificador decodifica o fio TX, sem ler payloads ou máscaras internos do RTL.
Os testes incluem buffers parciais, sequência maior que a FIFO, pausas,
esgotamento do contador, falhas e recuperação com contexto novo.

O Yosys confirma também a ausência dos módulos AES no baseline. Isso é
checagem de elaboração, não medição de recursos FPGA. Ver
[validação de 16/09](validacao-integracao-2026-09-16.md) e
[captura no PC](captura-pc.md). O registro de nonces no PC já está implementado;
o provisionamento no wrapper, os builds físicos e a bancada continuam pendentes.
