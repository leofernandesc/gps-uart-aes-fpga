# GPS + UART + AES-128-CTR em FPGA

Projeto do artigo para o BTSym’26: aquisição de dados de um GPS real e avaliação
do custo de acrescentar confidencialidade em hardware à comunicação serial.

**Estado em 07/09/2026:** primeira etapa implementada — UART revisado e testes
automatizados. AES, FIFO, controle de sessão, software do PC e integração física
ainda não estão implementados. Não há bitstream nem resultados experimentais
da DE10-Lite neste marco.

## Configuração e limites do trabalho

| Item | Decisão |
| --- | --- |
| Placa | DE10-Lite, clock de 50 MHz |
| GPS | u-blox M8; modelo exato da placa a confirmar; VCC identificado como 3,3 V pelo usuário |
| Serial | 9600 baud, 8N1, sem seleção de taxa em execução |
| Criptografia planejada | AES-128-CTR, núcleo RTL próprio e iterativo |
| Receptor | PC com decifragem por biblioteca independente |
| Avaliação | Mesmo sistema com e sem AES, dados reais e replay controlado |
| Fora do escopo | ASIC, rede neural, segunda FPGA, comparação de baud rates e de várias arquiteturas AES |
| Datas de trabalho | Congelamento em 28/09; submissão preferencial em 29/09; reserva até 30/09/2026 |

AES-CTR fornecerá **confidencialidade**, não autenticação, proteção contra
alteração/replay do tráfego ou contra falsificação do sinal GNSS. O protótipo
não deve ser apresentado como um produto de comunicação segura completo.

## Executar a validação

No Linux, a partir deste diretório:

```bash
make check
```

Executa os quatro testes históricos, sete configurações dos novos testes,
lint rigoroso e síntese estrutural. Falhas abortam o comando com código não zero.
Resultados locais ficam em `build/`, sem entrar no versionamento.

O executor usa ferramentas nativas se todas estiverem disponíveis; caso contrário,
usa a imagem Docker **já instalada** `isaiassh/unic-cass-tools:1.0.7`.
Não baixa dependências nem usa a rede. O container recebe as fontes somente para
leitura e pode escrever apenas no diretório de resultados e no seu `/tmp`.
É necessário ter acesso autorizado ao Docker.

```bash
HDL_RUNNER=docker make check
HDL_RUNNER=native make check
make test
make lint
make synth
make reference
```

A síntese Yosys é apenas uma verificação estrutural do RTL. **Não é fluxo ASIC**
e não substitui síntese, place-and-route e análise temporal do Quartus para a
DE10-Lite. Não usar suas células genéricas como LUTs/LEs, Fmax ou potência FPGA.

## Organização

```text
rtl/common/reset_sync.sv     reset: asserção assíncrona, liberação sincronizada
rtl/uart/uart_rx.sv          RX sincronizado e amostragem central por quadro
rtl/uart/uart_tx.sv          TX com duração completa de cada bit
rtl/uart/uart_top.sv         interface de bytes e configuração de produção
tb/                         fontes seriais e verificadores independentes
scripts/                    execução reproduzível dos testes e checagens
reference/uart-v1/           cópia imutável do UART anterior e checksums
docs/                       contratos, cronograma, evidências e checklist de bancada
build/                      saídas geradas, ignoradas pelo Git
```

O projeto original em
`/home/leofernandesc/uniccass-icdesign-tools/shared_xserver/projects/uart`
foi preservado. A referência contém apenas quatro fontes RTL, quatro testbenches
e a configuração antiga; não duplica runs ASIC, imagens ou binários.

## Documentos para continuar

- [Contrato e mudanças do UART](docs/uart-baseline.md)
- [Resultados da primeira etapa](docs/validacao-2026-09-07.md)
- [Cronograma e critérios de conclusão](docs/cronograma.md)
- [Primeira sessão de bancada e materiais](docs/bancada.md)

A apresentação para o orientador permanece em
`/home/leofernandesc/Documents/proposta_btsym_gps_fpga.html`.

Próximo bloco de implementação: AES-128 isolado, primeiro com vetores de
referência e interface definida, sem acoplar o desenvolvimento ao GPS físico.
