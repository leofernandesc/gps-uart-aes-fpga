# GPS + UART + AES-128-CTR em FPGA

Projeto do artigo para o BTSym’26: aquisição de dados de um GPS real e avaliação
do custo de acrescentar confidencialidade em hardware à comunicação serial.

**Estado em 09/09/2026:** UART v2, ponte RX → FIFO de 1.024 bytes → TX e núcleo
AES-128 isolado implementados. O AES passou pelos 866 vetores de comparação
independente, incluindo 284 casos oficiais NIST; ver [contrato do núcleo](docs/aes128.md).
A ponte já tem `.sof` para a DE10-Lite; o AES tem projeto separado de análise.
A regressão completa e o fit/timing interno do AES passaram em 09/09;
ver [resultados e limites deste marco](docs/validacao-aes-2026-09-09.md).
A placa ainda não está disponível: não houve programação, recepção de GPS real
ou medição de bancada. CTR, controle de sessão e software de captura do PC
continuam pendentes; a ponte atual ainda transmite sem criptografia.

## Configuração e limites do trabalho

| Item | Decisão |
| --- | --- |
| Placa | DE10-Lite, clock de 50 MHz |
| GPS | NEO-M8N-010 informado pelo usuário; VCC marcado como 3,3 V; conferir conector da placa de suporte na bancada |
| Serial | 9600 baud, 8N1, sem seleção de taxa em execução |
| Criptografia planejada | AES-128-CTR, núcleo RTL próprio e iterativo |
| Receptor | PC com decifragem por biblioteca independente |
| Avaliação | Mesmo sistema com e sem AES, dados reais e replay controlado |
| Fora do escopo | ASIC, rede neural, segunda FPGA, comparação de baud rates e de várias arquiteturas AES |
| Datas de trabalho | Submissão em 24/09; contingência e encerramento em 25/09; prazo externo até 30/09/2026 |

AES-CTR fornecerá **confidencialidade**, não autenticação, proteção contra
alteração/replay do tráfego ou contra falsificação do sinal GNSS. O protótipo
não deve ser apresentado como um produto de comunicação segura completo.

## Executar a validação

No Linux, a partir deste diretório:

```bash
make check
```

Executa 18 simulações: quatro testes históricos, doze configurações de UART/FIFO/
ponte e dois testbenches AES. Inclui lint rigoroso dos três tops e checagem
estrutural do UART e do AES.
Falhas abortam o comando com código não zero.
Resultados locais ficam em `build/`, sem entrar no versionamento.

O executor usa ferramentas nativas se todas estiverem disponíveis; caso contrário,
usa a imagem Docker **já instalada** `isaiassh/unic-cass-tools:1.0.7`.
Não baixa dependências nem usa a rede. O container recebe as fontes somente para
leitura e pode escrever apenas no diretório de resultados e no seu `/tmp`.
É necessário ter acesso autorizado ao Docker.
O gerador dos vetores AES também requer Python 3 e `cryptography` no host
(já disponíveis neste ambiente). Ele usa uma biblioteca independente do RTL;
as referências públicas NIST estão incluídas no repositório.

```bash
HDL_RUNNER=docker make check
HDL_RUNNER=native make check
make test
make lint
make synth
make reference
make bridge  # Apenas os novos testes de FIFO/ponte e lint do top da placa
make aes     # Vetores independentes, componentes, núcleo, lint e estrutura AES
```

A síntese Yosys é apenas uma verificação estrutural do RTL. **Não é fluxo ASIC**
e não substitui síntese, place-and-route e análise temporal do Quartus para a
DE10-Lite. Não usar suas células genéricas como LUTs/LEs, Fmax ou potência FPGA.

## Compilar para a DE10-Lite sem a placa

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
As métricas atuais incluem FIFO e LEDs de diagnóstico, mas ainda não o controle
de sessão que será comum aos dois builds do artigo.

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
rtl/aes/                    AES-128 iterativo e transformações de rodada
fpga/de10_lite/              top da placa, projeto Quartus, QSF e SDC
fpga/aes_analysis/           análise isolada do AES, sem pinagem de bancada
tb/                         fontes seriais e verificadores independentes
scripts/                    execução reproduzível dos testes e checagens
reference/uart-v1/           cópia imutável do UART anterior e checksums
reference/aes-cavp/          vetores públicos oficiais NIST e sua procedência
docs/                       contratos, cronograma, evidências e checklist de bancada
build/                      saídas geradas, ignoradas pelo Git
```

O projeto original em
`/home/leofernandesc/uniccass-icdesign-tools/shared_xserver/projects/uart`
foi preservado. A referência contém apenas quatro fontes RTL, quatro testbenches
e a configuração antiga; não duplica runs ASIC, imagens ou binários.

## Documentos para continuar

- [Contrato e mudanças do UART](docs/uart-baseline.md)
- [Interface, latência e limites do AES](docs/aes128.md)
- [Validação AES e recursos pós-fit](docs/validacao-aes-2026-09-09.md)
- [Resultados da primeira etapa](docs/validacao-2026-09-07.md)
- [Cronograma e critérios de conclusão](docs/cronograma.md)
- [Primeira sessão de bancada e materiais](docs/bancada.md)

A apresentação para o orientador permanece em
`/home/leofernandesc/Documents/proposta_btsym_gps_fpga.html`.

Próximo bloco de implementação: CTR por byte, com nonce/contador, consumo de
máscara sob backpressure e testes independentes; depois, integração UART e
controle de sessões. Essas etapas também podem avançar sem a placa.
