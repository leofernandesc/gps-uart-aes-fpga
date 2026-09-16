# GPS + UART + AES-128-CTR em FPGA

Projeto do artigo para o BTSym’26: aquisição de dados de um GPS real e avaliação
do custo de acrescentar confidencialidade em hardware à comunicação serial.

**Estado em 16/09/2026:** UART v2, ponte RX → FIFO de 1.024 bytes → TX, núcleo
AES-128 e adaptador AES-CTR por byte implementados. O AES passou pelos 866
vetores de comparação independente, incluindo 284 casos oficiais NIST;
ver [contrato do núcleo](docs/aes128.md).
A ponte já tem `.sof` para a DE10-Lite; o AES tem projeto separado de análise.
A regressão completa e o fit/timing interno do AES passaram em 09/09;
ver [resultados e limites deste marco](docs/validacao-aes-2026-09-09.md).
O CTR passou em 60 fluxos, com 19.009 bytes comparados e recuperados no PC por
biblioteca independente; ver
[validação do CTR](docs/validacao-ctr-2026-09-10.md).
O teste UART autônomo gera 0x55 a cada 100 ms para observar TX no osciloscópio,
com RX e LEDs para loopback por jumper. Seu SOF e a auditoria temporal passaram;
ver [revisão e resultados de 14/09](docs/revisao-2026-09-14.md).
Ainda não há registro de programação, recepção de GPS real ou medição de
bancada. A integração UART–FIFO–CTR–TX passou nos modos baseline/secure, com
4.982 bytes decodificados do fio TX e conferidos no PC. O gravador binário e
comparador do PC passaram em testes com porta virtual Linux. Ver
[validação da integração](docs/validacao-integracao-2026-09-16.md).
Ainda faltam provisionamento de contexto, registro persistente de nonces e
builds completos. Os SOFs disponíveis continuam sendo UART de bancada e ponte
sem cifra. A comparação inclui MAX 10 e Cyclone IV; modelo, clock e pinagem da
segunda placa permanecem pendentes de confirmação.

## Configuração do protótipo

| Item | Decisão |
| --- | --- |
| Placa | DE10-Lite, clock de 50 MHz |
| Segundo alvo | Cyclone IV; placa, dispositivo e oscilador a confirmar |
| GPS | NEO-M8N-010; VCC de 3,3 V; conferir conector da placa de suporte na bancada |
| Serial | 9600 baud, 8N1, sem seleção de taxa em execução |
| Criptografia | AES-128-CTR, núcleo RTL próprio e iterativo |
| Receptor | PC com decifragem por biblioteca independente |
| Avaliação | Quatro builds: baseline/secure em cada FPGA, com o mesmo RTL |
| Datas de trabalho | Submissão em 24/09; contingência e encerramento em 25/09; prazo externo até 30/09/2026 |

AES-CTR fornecerá **confidencialidade**, não autenticação, proteção contra
alteração/replay do tráfego ou contra falsificação do sinal GNSS. O protótipo
não deve ser apresentado como um produto de comunicação segura completo.

## Executar a validação

No Linux, a partir deste diretório:

```bash
make check
```

Executa 26 simulações: quatro testes históricos, catorze configurações de UART/
bancada/FIFO/ponte, dois testbenches AES, dois de CTR e quatro da integração.
Inclui sete configurações de lint, checagem estrutural, verificação no PC dos
bytes CTR e do TX integrado, além de oito testes do software de captura.
Falhas abortam o comando com código não zero.
Resultados locais ficam em `build/`, sem entrar no versionamento.

O executor usa ferramentas nativas se todas estiverem disponíveis; caso contrário,
usa a imagem Docker **já instalada** `isaiassh/unic-cass-tools:1.0.7`.
Não baixa dependências nem usa a rede. O container recebe as fontes somente para
leitura e pode escrever apenas no diretório de resultados e no seu `/tmp`.
É necessário ter acesso autorizado ao Docker.
Os geradores dos vetores AES/CTR também requerem Python 3 e `cryptography` no host
(já disponíveis neste ambiente). Usam uma biblioteca independente do RTL;
as referências públicas NIST estão incluídas no repositório.

```bash
HDL_RUNNER=docker make check
HDL_RUNNER=native make check
make test
make lint
make synth
make reference
make uart    # Somente UART RX/TX, top e gerador de bancada; sem AES/FIFO
make uart-waves  # Gera os VCDs da UART isolada e do teste para osciloscópio
make bridge  # Apenas os novos testes de FIFO/ponte e lint do top da placa
make aes     # Vetores independentes, componentes, núcleo, lint e estrutura AES
make ctr     # Máscaras, fluxo por byte, lint, estrutura e conferência no PC
make integration  # Caminho serial completo sem/com AES; teste em 50 MHz/9600
make pc      # Comparador e gravação binária em porta virtual Linux
```

A síntese Yosys é apenas uma verificação estrutural do RTL. **Não é fluxo ASIC**
e não substitui síntese, place-and-route e análise temporal do Quartus para a
DE10-Lite. Não usar suas células genéricas como LUTs/LEs, Fmax ou potência FPGA.

## Compilar para a DE10-Lite sem a placa

Para o teste de **UART isolada**, sem depender de GPS ou adaptador USB–UART:

```bash
make uart-fpga
```

Abrir [uart_scope.qpf](fpga/de10_lite/uart_scope/uart_scope.qpf) no Quartus.
O resultado é `build/de10_lite/uart_scope/uart_scope.sof`. O top transmite
0x55 a cada 100 ms. O [roteiro de osciloscópio e jumper](fpga/de10_lite/uart_scope/README.md)
explica a montagem, as medidas esperadas e o significado dos LEDs.

Para a ponte **UART + FIFO**, que retransmite o que recebe:

```bash
make fpga
```

Usa o Quartus instalado no Linux; se necessário, definir `QUARTUS_SH` com o
caminho do executável. Faz síntese, fit, geração do `.sof` e auditoria temporal
nos três cantos do dispositivo. Não executa o Programmer. Os resultados ficam
em `build/quartus/`, incluindo `uart_bridge.sof`, relatórios e `build-status.txt`.

Na interface gráfica, abrir **File → Open Project** e selecionar
[uart_bridge.qpf](fpga/de10_lite/uart_bridge.qpf). A configuração é fixa:
MAX 10 10M50DAF484C7G, 50 MHz, 9600 baud, 8N1.

Ver [pinagem e uso da ponte](fpga/de10_lite/README.md) e
[resultados deste marco](docs/validacao-ponte-quartus-2026-09-07.md).
As métricas atuais incluem FIFO e LEDs de diagnóstico, mas ainda não o AES-CTR
integrado que será comparado nos dois builds do artigo.

Para o AES isolado:

```bash
make aes-fpga
```

Faz síntese, fit e análise de **timing interno** usando pinos virtuais. Não gera
`.sof` nem valida os caminhos de interface com o futuro CTR/UART. Abrir
[aes128_analysis.qpf](fpga/aes_analysis/aes128_analysis.qpf) no Quartus, se desejado.
Ver [alcance das estimativas](fpga/aes_analysis/README.md).

## Organização

```text
rtl/common/reset_sync.sv     reset: asserção assíncrona, liberação sincronizada
rtl/common/sync_fifo.sv      FIFO síncrona, ocupação máxima e overflow
rtl/uart/uart_rx.sv          RX sincronizado e amostragem central por quadro
rtl/uart/uart_tx.sv          TX com duração completa de cada bit
rtl/uart/uart_top.sv         interface de bytes e configuração de produção
rtl/bridge/uart_bridge.sv    ponte sem cifra, flags persistentes de erro
rtl/bridge/uart_ctr_bridge.sv integração baseline/secure, retenção de byte e cancelamento
rtl/aes/                    AES-128 iterativo e transformações de rodada
rtl/ctr/                    gerador de máscaras e adaptador CTR por byte
fpga/de10_lite/              top da placa, projeto Quartus, QSF e SDC
fpga/de10_lite/uart_scope/   UART autônoma para osciloscópio e loopback por jumper
fpga/cyclone4/              dados necessários para criar o segundo alvo
fpga/aes_analysis/           análise isolada do AES, sem pinagem de bancada
tb/                         fontes seriais e verificadores independentes
scripts/                    execução reproduzível dos testes e checagens
reference/uart-v1/           cópia imutável do UART anterior e checksums
reference/aes-cavp/          vetores públicos oficiais NIST e sua procedência
reference/ctr-sp800-38a/     exemplo público AES-128-CTR do NIST
docs/                       contratos, cronograma, evidências e checklist de bancada
build/                      saídas geradas, ignoradas pelo Git
```

O projeto original em
`/home/leofernandesc/uniccass-icdesign-tools/shared_xserver/projects/uart`
foi preservado. A referência contém apenas quatro fontes RTL, quatro testbenches
e a configuração antiga; não duplica runs ASIC, imagens ou binários.

## Documentos para continuar

- [Orientações de continuidade, cronograma e revisão de pulls](AGENTS.md)
- [Contrato e mudanças do UART](docs/uart-baseline.md)
- [Arquitetura, alvos e comparação entre placas](docs/arquitetura.md)
- [UART isolada: roteiro para a bancada](fpga/de10_lite/uart_scope/README.md)
- [Revisão de código e validação em 14/09](docs/revisao-2026-09-14.md)
- [Interface, latência e limites do AES](docs/aes128.md)
- [Validação AES e recursos pós-fit](docs/validacao-aes-2026-09-09.md)
- [Interface e funcionamento do CTR](docs/ctr.md)
- [Contrato da integração UART–FIFO–CTR](docs/integracao-uart-ctr.md)
- [Captura binária e comparação no PC](docs/captura-pc.md)
- [Validação CTR e conferência no PC](docs/validacao-ctr-2026-09-10.md)
- [Resultados da primeira etapa](docs/validacao-2026-09-07.md)
- [Cronograma e critérios de conclusão](docs/cronograma.md)
- [Plano de execução e colaboração](docs/PLANO_DE_EXECUCAO.md)
- [Primeira bancada e materiais](docs/bancada.md)

A [apresentação para o orientador](docs/proposta_btsym_gps_fpga.html) está
versionada, com quatro telas e cronograma até 25/09. A cópia local em
`/home/leofernandesc/Documents/proposta_btsym_gps_fpga.html` acompanha essa versão.

Próximo passo sem placa: implementar provisionamento do contexto no wrapper,
registro persistente de nonces no PC e os builds baseline/secure da DE10-Lite,
com auditoria temporal. O cadastro da Cyclone IV depende de identificação.
Ao receber a DE10-Lite, executar primeiro a UART com osciloscópio e jumper;
depois validar a captura física. Simulação e PTY não concluem esses ensaios.
