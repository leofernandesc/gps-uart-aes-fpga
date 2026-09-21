# Arquitetura e seleção dos experimentos

Atualização: 21/09/2026. A [apresentação](proposta_btsym_gps_fpga.html) contém
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
| `make baseline-fpga` | `de10_lite_uart_baseline_top` → wrapper comum → `uart_ctr_bridge(ENABLE_AES=0)` | `build/de10_lite/baseline/uart_baseline.sof` |
| `make secure-fpga` | `de10_lite_uart_secure_top` → wrapper comum → `uart_ctr_bridge(ENABLE_AES=1)` | `build/de10_lite/secure/uart_secure.sof` |
| `make cyclone4-uart-fpga` | `cyclone4_uart_scope_top` → UART autônoma | `build/cyclone4/uart_scope/uart_scope.sof` |
| `make cyclone4-baseline-fpga` | `cyclone4_uart_baseline_top` → wrapper comum → `uart_ctr_bridge(ENABLE_AES=0)` | `build/cyclone4/baseline/uart_baseline.sof` |
| `make cyclone4-secure-fpga` | `cyclone4_uart_secure_top` → wrapper comum → `uart_ctr_bridge(ENABLE_AES=1)` | `build/cyclone4/secure/uart_secure.sof` |
| `make aes-fpga` | AES e reset, com portas virtuais | `build/quartus_aes/`, somente análise |
| `make integration` | `uart_ctr_bridge`, com e sem AES | Simulação serial, lint, estrutura e comparação no PC |
| `make pc` | Gravador/comparador Linux | Testes de software com porta virtual |
| `make check` | Regressão de todos os blocos existentes | Logs em `build/` |

No Quartus, quem seleciona o circuito é o projeto/revisão, a lista de fontes
do QSF e a hierarquia do top. Selecionar uma aba do editor não muda o alvo.
O SDC descreve o clock existente; `create_clock` não gera clock em hardware.
Testbenches são estímulos de simulação e não entram no SOF.

Os projetos `baseline` e `secure` integrados possuem QPF, QSF, SDC e tops
separados. O executor mantém as duas elaborações independentes para que o
baseline não contenha um AES apenas desabilitado em tempo de execução.

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

O wrapper inicializa `cfg_*` automaticamente com um contexto de elaboração,
sem protocolo serial adicional. Os parâmetros `CONTEXT_KEY`, `CONTEXT_NONCE` e
`CONTEXT_COUNTER` podem ser substituídos em um build privado; `CONTEXT_FILE`
valida o JSON e gera o pacote usado pelo Quartus. Os valores padrão servem
apenas ao bring-up. O software PC (ver [captura-pc](captura-pc.md)) grava e
compara arquivos. Não há configuração em tempo de execução.

## Matriz experimental

| Placa | Baseline integrado | Secure integrado | Clock |
| --- | --- | --- | --- |
| DE10-Lite / MAX 10 10M50DAF484C7G | Build concluído | Build concluído | 50 MHz |
| Cyclone IV E / EP4CE6E22C8N, ZRTECH/WXEDA V2.00 | Build concluído; programação pendente | Build concluído; programação pendente | Perfil candidato de 48 MHz; confirmar no P01 |

As quatro configurações são obrigatórias. A [revisão de 20/09](revisao-completa-2026-09-20.md)
identificou que o secure existente excedia a capacidade do EP4CE6; a otimização
do RTL comum foi aplicada e os dois builds Cyclone IV agora passam no fit e no
timing. A arquitetura do caminho de dados permanece a mesma. Os resultados
Quartus ainda não são evidência de programação ou funcionamento elétrico.

Dentro de cada placa, ambos os builds terão a mesma FIFO, interfaces,
instrumentação, clock e restrições. O AES estará ausente por
elaboração no baseline, não apenas desativado por um switch. A ponte atual e
o gerador para osciloscópio são testes preparatórios, não esse comparador final.

Os projetos da DE10-Lite estão em `fpga/de10_lite/baseline/` e
`fpga/de10_lite/secure/`; os da Cyclone IV estão em
`fpga/cyclone4/uart_scope/`, `fpga/cyclone4/baseline/` e
`fpga/cyclone4/secure/`, com saídas independentes em
`build/<placa>/<configuracao>/`. Reutilizar o RTL, evitando cópias por placa.
Dados privados e coordenadas reais ficam fora do Git.

## Clocks e comparação de desempenho

RX/TX usam contadores locais no clock do sistema. A ponte aceita `CLK_FREQ` e
`BAUD_RATE` como parâmetros de elaboração e calcula `CLKS_PER_BIT`. A DE10-Lite
declara 50.000.000/9.600 explicitamente: 5.208 ciclos por bit, sem clock gerado.
O perfil Cyclone IV usa 48.000.000/9.600: 5.000 ciclos por bit, sem clock
gerado. Esse é o valor de compilação a ser confirmado no P01 pela medição de
aproximadamente `104,17 µs` por bit; o `create_clock` do SDC não cria clock no
hardware.

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
- Plano completo e registro dos resultados: [plano de testes](plano-de-testes.md).

SignalTap pode ajudar no diagnóstico; seus builds devem ficar separados das
medições oficiais de área. Não programar um SOF de outra placa/revisão.
