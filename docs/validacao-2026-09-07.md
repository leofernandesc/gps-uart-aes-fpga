# Resultado da primeira etapa — 07/09/2026

**Resultado:** revisão funcional do UART concluída. `make check` retornou código
0 com `PASS: all UART baseline checks`. Esta é a baseline RTL v2, não uma
validação física do sistema GPS + AES.

## Preservação

Os nove arquivos do UART anterior foram copiados sem alterações para
`reference/uart-v1/`. Seus SHA-256 foram conferidos. O projeto original não foi
modificado; seu diretório já era não rastreado no Git do projeto antigo.

Os quatro testes históricos continuam passando. Um teste adicional reproduz o
start bit incompleto em uma solicitação não alinhada ao tick global. Isso explica
por que os testes anteriores não eram suficientes para validar um GPS externo.

## Execuções e evidências

| Execução | Evidência observada |
| --- | --- |
| Quatro testbenches históricos | Todos passaram; checksums preservados |
| RX com divisor de teste 32 | 5.635 bytes corretos; 256 valores em 20 fases, fluxo contínuo, tolerância temporal, falsos starts, erro de stop/break e reset |
| RX com divisor de teste 33 | Mesma bateria, mais 5.635 bytes corretos; cobre contagem ímpar |
| TX com divisor de teste 32 | 257 quadros corretos, verificação a cada clock, pedidos durante busy e reset |
| TX com divisor de teste 33 | Mesma bateria, mais 257 quadros corretos |
| Integração acelerada | 64 bytes em cada direção simultaneamente; fonte e decodificador independentes |
| Configuração 50 MHz/9600 | 16 bytes em cada direção; entrada externa com período nominal fracionário e saída com divisor inteiro 5.208 |
| Regressão v1 versus v2 | Start antigo = 480 ns; novo = 640 ns; exigido = 640 ns no teste acelerado |
| Verilator `--lint-only --Wall` | Código 0, sem avisos |
| Yosys `check -assert` e seleção de latches | Zero problemas estruturais; nenhum latch inferido |

São **quatro execuções históricas e sete novas configurações de simulação**, mais
lint e síntese estrutural. Os divisores acelerados e as variações do estímulo
pertencem ao testbench, não configuram novas taxas na placa nem constituem uma
comparação de baud rates para o artigo.

O caso 480/640 ns é uma reprodução controlada do bug antigo, não uma medição na
FPGA. Da mesma forma, a ausência de erros nestes estímulos não demonstra uma taxa
de erro física nula ou cobertura formal de todos os comportamentos.

## Ferramentas e reprodução

- Icarus Verilog 13.0 devel, `s20221226-554-g25a84d5cf-dirty`.
- Verilator 5.026.
- Yosys 0.44, commit `80ba43d26`.
- Imagem Docker local `isaiassh/unic-cass-tools:1.0.7`.
- ID observado da imagem: `sha256:921d95e8cd03b8fbe5cec683ea14add4c1b6e0db1d5d05187fac7deb16b5e0f8`.
- Container sem rede, fontes read-only e resultados em `build/`.

Na raiz do projeto:

```bash
sha256sum -c docs/evidence/uart-baseline-v2.sha256
make check
```

O manifesto identifica exatamente as fontes, testbenches e executor desta
baseline. Ele é histórico: mudanças futuras exigirão uma nova versão e nova
evidência, não reescrita dos resultados antigos.

Logs reproduzíveis ficam em `build/uart_*.log`, `build/lint.log`,
`build/synth.log`, `build/tool_versions.txt`, `build/check-status.txt` e
`build/reference/`. O diretório é gerado e não é versionado.

## Limites e pendências

- Não houve execução do Quartus nem programação da DE10-Lite.
- Não houve aquisição de GPS real, medição elétrica ou confirmação do carrier M8.
- Não foram medidos LE/LUT, M9K, Fmax, potência ou latência física.
- Síntese genérica Yosys não representa mapeamento MAX 10 nem avaliação ASIC.
- Sincronizadores e liberação de reset precisam ser conferidos no fluxo físico;
  simulação digital não modela metastabilidade analógica.
- Não há FIFO, contadores de overflow, AES, CTR, sessões ou software host ainda.

Próximas frentes: implementação e testes do AES isolado; em paralelo, conferir
Quartus/USB-Blaster e materiais, seguindo [o checklist de bancada](bancada.md).
