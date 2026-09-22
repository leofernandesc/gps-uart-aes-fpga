# Métricas FPGA — DE10-Lite — 20/09/2026

Resultado originalmente consolidado após a reconciliação com `origin/main`, no
commit `b065ba8e9cb16a10e0903d054e7927e0b22846a1`, e regenerado para a bancada em
22/09 no commit `746b0852ecf3ea0f049cf3adefec470723ed810a`. As métricas permaneceram
inalteradas.

## Método

As métricas foram extraídas automaticamente dos relatórios pós-fit do Quartus
com:

```bash
make metrics
```

O script `scripts/fpga_metrics.py` lê os relatórios dos projetos separados
`build/de10_lite/baseline/` e `build/de10_lite/secure/`, seleciona a menor Fmax
dos três cantos e calcula a diferença absoluta e percentual do secure em relação
ao baseline. Desde a correção de 20/09, também exige status PASS do build,
auditoria completa dos quatro checks em todos os cantos e um relatório Fmax por
canto; slack negativo ou artefato incompleto é rejeitado. Os arquivos JSON e
Markdown gerados permanecem em `build/`.

## Resultado

| Métrica pós-fit | Baseline | Secure | Secure − baseline |
| --- | ---: | ---: | ---: |
| Elementos lógicos | 347 | 5.622 | +5.275 (+1.520,17%) |
| Registradores | 216 | 917 | +701 (+324,54%) |
| Memória | 8.192 bits | 8.192 bits | 0 |
| Pinos | 14 | 14 | 0 |
| Fmax mínima | 123,00 MHz | 98,23 MHz | −24,77 MHz (−20,14%) |
| Pior setup | 11,870 ns | 9,820 ns | — |
| Pior hold | 0,102 ns | 0,101 ns | — |
| Pior recovery | 14,454 ns | 13,688 ns | — |
| Pior removal | 0,439 ns | 2,256 ns | — |

As duas variantes operam a 50 MHz com slack positivo nos quatro tipos de
análise. A inclusão do AES aumenta significativamente a lógica e os
registradores e reduz a Fmax estimada, mas não impede o clock de operação
definido para a DE10-Lite.

Artefatos preparados para a bancada em 22/09:

| Variante | Arquivo | SHA-256 |
| --- | --- | --- |
| Baseline | `build/de10_lite/baseline/uart_baseline.sof` | `f878f884b264c2f02a4d720c6ef3120f85ed88c3b52c3f87da7421c90437161c` |
| Secure | `build/de10_lite/secure/uart_secure.sof` | `320357adffc3f530f7908fd0abcc2016d41d5cd123b3aa22dc25b4af9db0a91a` |

## Limites

Fmax, área lógica e slacks são resultados de síntese/fit e timing do Quartus;
não são medições de osciloscópio, potência ou desempenho físico. A tabela não
inclui potência, pois ainda não há atividade de bancada para uma estimativa
representativa. A validação física dos tops baseline/secure continua pendente.
