# Arquitetura e seleção dos experimentos

Atualização: 16/09/2026. A [apresentação](proposta_btsym_gps_fpga.html) contém
o desenho da arquitetura proposta. O [cronograma](cronograma.md) registra o
estado efetivo de cada etapa.

## Organização do RTL e dos alvos

`rtl/` é compartilhado por todas as placas. Cada alvo em `fpga/` possui seu
wrapper, dispositivo, pinagem e restrições. A `main` contém as plataformas;
branches temporárias servem para desenvolver e revisar alterações.

| Comando | Hierarquia selecionada | Saída / uso |
| --- | --- | --- |
| `make uart` | RX, TX, top UART e estímulo de bancada | Testes isolados, lint e estrutura |
| `make uart-waves` | Testbenches UART e bancada | VCD dos sinais públicos |
| `make uart-fpga` | `de10_lite_uart_scope_top` → `uart_scope` → reset, RX, TX | `build/de10_lite/uart_scope/uart_scope.sof` |
| `make fpga` | `de10_lite_uart_top` → ponte → RX, FIFO, TX | `build/quartus/uart_bridge.sof` |
| `make aes-fpga` | AES e reset, com portas virtuais | `build/quartus_aes/`, somente análise |
| `make integration` | `uart_ctr_bridge`, com e sem AES | Simulação serial, lint, estrutura e comparação no PC |
| `make pc` | Gravador/comparador Linux | Testes de software com porta virtual |
| `make check` | Regressão de todos os blocos existentes | Logs em `build/` |

No Quartus, quem seleciona o circuito é o projeto/revisão, a lista de fontes
do QSF e a hierarquia do top. Selecionar uma aba do editor não muda o alvo.
O SDC descreve o clock existente; `create_clock` não gera clock em hardware.
Testbenches são estímulos de simulação e não entram no SOF.

Os projetos `baseline` e `secure` integrados ainda serão criados. O executor
rejeita alvos ausentes; não os substitui pela ponte ou pelo AES isolado.

## Teste UART de bancada

O gerador interno de `uart_scope` solicita um byte `0x55` a cada 100 ms.
O TX o transmite mesmo com o RX desconectado; um osciloscópio basta para
observar o sinal. O RX entrega o último byte aos LEDs. Com um jumper externo
TX → RX, o teste também passa pelos pinos físicos de entrada e saída.

Esse top não ecoa a entrada. A transmissão periódica é independente de RX.
LED 8 registra recepção; LED 9 retém framing ou byte diferente de 0x55.
O roteiro e os limites do ensaio estão no [guia de bancada UART](../fpga/de10_lite/uart_scope/README.md).

## Caminho integrado; aquisição GPS ainda pendente

```text
GPS TX ──┬── UART RX → FIFO → estágio selecionado → UART TX → PC / comparação
         │                              │
         │                 baseline: passagem direta
         │                 secure: AES-128-CTR
         │
         └── captura da referência ─────────────────────────────── PC
```

A FIFO entrega dados com um pulso `rd_valid`; o CTR usa `valid/ready`. Na
integração, `uart_ctr_bridge` usa um registrador de byte com flag válida para
reter cada resposta até o aceite do próximo estágio. Reserva espaço antes de
pedir a leitura e só avança a máscara no aceite do TX. Os dois modos passaram
na simulação serial e na comparação independente; ver [contrato](integracao-uart-ctr.md).

O tamanho do replay, a chave, o nonce e o contador são parâmetros registrados
no PC para cada experimento; não formam um bloco adicional no datapath. O PC
decifra o fluxo, registra erros e compara o resultado com a referência original.
Usar nonce novo em cada captura e bloquear o wrap do contador. Não há
autenticação com CTR; as alegações do artigo serão de confidencialidade e
comportamento do transporte.

A interface RTL `cfg_*` inicializa o contexto, sem protocolo serial adicional.
Ainda é necessário implementá-la no wrapper e controlar o início da aquisição;
registrar parâmetros no PC não os transfere automaticamente à FPGA. O
[software PC](captura-pc.md) grava e compara arquivos; provisionamento e
registro persistente de nonces ainda estão pendentes.

## Matriz experimental

| Placa | Baseline integrado | Secure integrado | Clock |
| --- | --- | --- | --- |
| DE10-Lite / MAX 10 10M50DAF484C7G | Pendente | Pendente | 50 MHz |
| Cyclone IV | Pendente do cadastro da placa/build | Pendente do cadastro da placa/build | Oscilador a confirmar |

Dentro de cada placa, ambos os builds terão a mesma FIFO, interfaces,
instrumentação, clock e restrições. O AES estará ausente por
elaboração no baseline, não apenas desativado por um switch. A ponte atual e
o gerador para osciloscópio são testes preparatórios, não esse comparador final.

Projetos futuros: `fpga/<placa>/baseline/` e `fpga/<placa>/secure/`, com saídas
independentes em `build/<placa>/<configuracao>/`. Reutilizar o RTL, evitando
cópias por placa. Dados privados e coordenadas reais ficam fora do Git.

## Clocks e comparação de desempenho

RX/TX usam contadores locais no clock do sistema. A ponte aceita `CLK_FREQ` e
`BAUD_RATE` como parâmetros de elaboração e calcula `CLKS_PER_BIT`. A DE10-Lite
declara 50.000.000/9.600 explicitamente: 5.208 ciclos por bit, sem clock gerado.
A frequência de uma placa Cyclone IV só será definida após consultar seu manual.

50 MHz é o clock de operação da DE10-Lite, não a frequência máxima da FPGA.
Fmax é uma estimativa temporal de um circuito específico no dispositivo. Um
build de UART não determina a Fmax do sistema que também contém AES.

Registrar cada comparação na frequência de operação da respectiva placa e
apresentar latência tanto em ciclos quanto em tempo: `tempo = ciclos / clock`.
Comparar primeiro o acréscimo `secure − baseline` em cada placa. Entre placas,
identificar dispositivo, speed grade, clock, condições temporais e ferramenta.
Não atribuir ao AES uma diferença causada só pelo oscilador.

Recursos devem incluir LEs, registradores, bits e blocos de memória. Reportar
valores absolutos e percentuais do dispositivo; não somar LEs e registradores
como se fossem recursos independentes. Potência é opcional: comparar apenas
estimativas com atividade e condições registradas, separando-as de medição.

A UART permanece 9600/8N1 nos quatro builds. Seu teto nominal de payload é
960 bytes/s por direção (dez bits por byte), reduzido por pausas/protocolo.
Isso não é o throughput interno do AES. Uma FIFO absorve rajadas, mas não
sustenta indefinidamente entrada com taxa média maior que a saída.

## Evidência necessária

- Simulação: vetores independentes e verificadores de bytes/tempo, incluindo
  erros, reset e pausas.
- Quartus: fit e timing do alvo completo, SHA, versão, seed e restrições.
- Bancada UART: captura do osciloscópio, montagem e resultado após reset.
- Experimento GPS: entrada capturada e saída recuperada, hashes, contagens,
  primeira divergência e parâmetros do ensaio. Osciloscópio sozinho não prova
  ausência de perdas em um fluxo longo.

SignalTap pode ajudar no diagnóstico; seus builds devem ficar separados das
medições oficiais de área. Não programar um SOF de outra placa/revisão.
