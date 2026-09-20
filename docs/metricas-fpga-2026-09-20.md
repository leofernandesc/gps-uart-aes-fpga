# Métricas FPGA — DE10-Lite — 20/09/2026

## Método

As métricas foram extraídas automaticamente dos relatórios pós-fit do Quartus
com:

```bash
make metrics
```

O script `scripts/fpga_metrics.py` lê os relatórios dos projetos separados
`build/de10_lite/baseline/` e `build/de10_lite/secure/`, seleciona a menor Fmax
dos três cantos e calcula a diferença absoluta e percentual do secure em relação
ao baseline. Os arquivos JSON e Markdown gerados permanecem em `build/`.

## Resultado

| Métrica pós-fit | Baseline | Secure | Secure − baseline |
| --- | ---: | ---: | ---: |
| Elementos lógicos | 342 | 6.984 | +6.642 (+1.942,11%) |
| Registradores | 215 | 2.196 | +1.981 (+921,40%) |
| Memória | 8.192 bits | 8.192 bits | 0 |
| Pinos | 14 | 14 | 0 |
| Fmax mínima | 132,61 MHz | 82,19 MHz | −50,42 MHz (−38,02%) |
| Pior setup | 12,459 ns | 7,833 ns | — |
| Pior hold | 0,102 ns | 0,111 ns | — |
| Pior recovery | 15,341 ns | 12,724 ns | — |
| Pior removal | 0,424 ns | 2,332 ns | — |

As duas variantes operam a 50 MHz com slack positivo nos quatro tipos de
análise. A inclusão do AES aumenta significativamente a lógica e os
registradores e reduz a Fmax estimada, mas não impede o clock de operação
definido para a DE10-Lite.

## Limites

Fmax, área lógica e slacks são resultados de síntese/fit e timing do Quartus;
não são medições de osciloscópio, potência ou desempenho físico. A tabela não
inclui potência, pois ainda não há atividade de bancada para uma estimativa
representativa. A validação física dos tops baseline/secure continua pendente.
