# Métricas FPGA — DE10-Lite — 30/09/2026

Par selecionado para os manuscritos: MAX 10 `10M50DAF484C7G`, clock de
50 MHz, UART 38400/8N1, FIFO de 1.024 bytes e seed 1. Os dois fits e as
auditorias de setup, hold, recovery e removal passaram nos três cantos.
O arquivo [de seleção](evidence/de10-lite-postfit-2026-09-30.json) preserva
métricas, horários, hashes de fontes, relatórios e SOFs sem incluir chaves,
nonces ou dados GPS.

## Resultados

| Métrica | Baseline | Secure | Secure − baseline |
| --- | ---: | ---: | ---: |
| Elementos lógicos | 331 | 5.591 | +5.260 (+1.589,12%) |
| Registradores | 212 | 913 | +701 (+330,66%) |
| Bits de memória | 8.192 | 8.192 | 0 |
| Pinos | 14 | 14 | 0 |
| Fmax mínima | 117,56 MHz | 92,61 MHz | −24,95 MHz (−21,22%) |
| Pior slack de setup | 11,494 ns | 9,202 ns | positivo |
| Pior slack de hold | 0,103 ns | 0,105 ns | positivo |
| Pior slack de recovery | 13,962 ns | 13,390 ns | positivo |
| Pior slack de removal | 0,440 ns | 2,487 ns | positivo |

A utilização de lógica é 0,67% do dispositivo no baseline e 11,24% no secure.
As Fmax mínimas restritas também são 117,56 e 92,61 MHz; o extrator preserva
as duas colunas do Quartus e rejeita um par cujo clock de operação exceda a
Fmax restrita. Fmax é uma estimativa do circuito pós-fit; o clock efetivo
permanece em 50 MHz. LEs e registradores não devem ser somados como recursos
independentes.

O relatório hierárquico atribui 208 elementos lógicos a cada uma das 20
S-boxes, totalizando 4.160 LEs dentro dos 5.591 do secure. Essa atribuição
não representa um recurso adicional à contagem total.

## Identificação do par

| Campo | Baseline | Secure |
| --- | --- | --- |
| Build encerrado, UTC | 2026-09-30T06:37:38.162339+00:00 | 2026-09-30T07:05:32.510947+00:00 |
| SHA-256 do SOF | `3132e0097eccd4194bf54f5041c992eff1fed41c0efde03e9b60902f1e5caaf7` | `81a8e176f531c46756af4e5557d8b30f01bd0918e55f0d3fed93216b866e31c0` |

As fontes compartilhadas possuem SHA-256
`70c604efca7a9e9ee8b946f152dcda89172f1da68d168b5508f23e00a3ee1ebe`.
O manifesto registra a revisão base e os hashes exatos das entradas;
a revisão Git isolada não substitui esses hashes quando há alterações locais.
O Quartus é Prime Lite 25.1std.

Os ensaios secure usam contextos estáticos novos por aquisição. Isso pode
alterar síntese e posicionamento mesmo com o mesmo datapath; o quadro de
29/09 (5.603 LEs e 103,38 MHz) pertence ao
[registro anterior](metricas-fpga-2026-09-29.md), não ao par selecionado aqui.
Não houve alteração do datapath entre essa revisão e o par congelado.

## Reproduzir e conferir

```bash
make metrics
make manuscript-check
python3 scripts/manuscript_check.py --offline
```

`make metrics` confere os hashes das entradas e dos artefatos locais antes
de extrair números. `make manuscript-check` compara todas as linhas pós-fit
e os valores do resumo nos dois idiomas com a seleção versionada. Havendo
builds locais, confere também sua igualdade com o par selecionado; um par
incompleto, alterado ou diferente faz a checagem falhar.

Em um clone sem relatórios locais, ou com `--offline`, a checagem usa a seleção
publicada e verifica as fontes versionadas. Esse modo não reexecuta o Quartus
nem verifica os artefatos ausentes. O pacote de contexto gerado em `build/`
permanece privado; somente seu hash é publicado.

Para selecionar outro par após compilar e revisar:

```bash
make metrics-snapshot METRICS_SNAPSHOT=docs/evidence/nova-selecao.json
python3 scripts/manuscript_check.py --snapshot docs/evidence/nova-selecao.json
```

A seleção recusa sobrescrever um arquivo existente. Revisar as tabelas,
resumos e a referência padrão do verificador quando escolher um novo par.

## Alcance da análise

A potência não foi estimada nem medida. Nos builds selecionados, o relatório
de metastabilidade encontrou sincronizadores automáticos, mas não calculou
MTBF. Uma [auditoria complementar](auditoria-temporal-2026-09-30.md) reaplicou
setup, hold, recovery e removal aos mesmos fits e verificou explicitamente
minimum pulse width nos três cantos: pior margem de 9,266 ns em ambos.

A identificação explícita e as hipóteses para MTBF foram verificadas em dois
perfis separados, com novos fits e sem programação física. As estimativas
desses perfis não pertencem aos SOFs selecionados nem substituem evidência
de confiabilidade da bancada. O arquivo de seleção e a tabela acima permanecem
inalterados; resultados complementares têm registro e hashes próprios.

Essas métricas descrevem implementação; evidências elétricas, replays e
aquisição GPS ao vivo são registradas no [plano de testes](plano-de-testes.md).
