# Métricas FPGA — DE10-Lite — 29/09/2026

Comparação Quartus pós-fit baseline/secure na DE10-Lite/MAX 10
`10M50DAF484C7G`, com clock de 50 MHz, UART 38400/8N1 e FIFO de 1.024 bytes.
Builds passam a auditoria de setup/hold/recovery/removal nos três cantos. Isto
é análise de implementação FPGA, não medição física de potência ou desempenho.

## Resultados

| Métrica | Baseline | Secure | Secure − baseline |
| --- | ---: | ---: | ---: |
| Elementos lógicos | 331 | 5.603 | +5.272 (+1.592,75%) |
| Registradores | 212 | 913 | +701 (+330,66%) |
| Memória | 8.192 bits | 8.192 bits | 0 |
| Pinos | 14 | 14 | 0 |
| Fmax mínima | 117,56 MHz | 103,38 MHz | −14,18 MHz (−12,06%) |
| Pior slack de setup | 11,494 ns | 10,327 ns | positivo |
| Pior slack de hold | 0,103 ns | 0,102 ns | positivo |
| Pior slack de recovery | 13,962 ns | 13,416 ns | positivo |
| Pior slack de removal | 0,440 ns | 2,230 ns | positivo |

Ambos os builds atendem ao clock de operação de 50 MHz. A variante secure
acrescenta lógica para AES-128-CTR e reduz a Fmax estimada, mantendo margem
positiva nos checks temporais auditados.

## Proveniência e limites

Gerado por `make baseline-fpga`, `make secure-fpga` e `make metrics`; Quartus
Prime Lite 25.1std. Os manifestos completos, hashes dos relatórios e JSON ficam
em `build/de10_lite/` (local e ignorado pelo Git). SOFs: baseline
`3132e0097eccd4194bf54f5041c992eff1fed41c0efde03e9b60902f1e5caaf7`, secure
`3507f4220efb2f5b6324cf7f5151e1da06272f70595598bf6b531e1f4a8d0783`.

Estes dados não provam programação ou operação física da FPGA. A aquisição
NEO-M9N, comunicação externa a 38400 e medições com osciloscópio/AD2 devem ser
registradas separadamente. Potência não foi incluída: o Power Analyzer foi
desabilitado e não há estimativa baseada em atividade representativa.
