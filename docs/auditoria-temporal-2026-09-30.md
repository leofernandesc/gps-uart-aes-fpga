# Auditoria temporal complementar — DE10-Lite — 30/09/2026

**Resultado: aprovado nos três cantos, baseline e secure.** O RTL, os QSFs
originais, os contextos e os SOFs selecionados para o artigo foram preservados.
Nenhuma placa foi programada nesta etapa.

## Verificação dos builds do artigo

O comando reaplica setup, hold, recovery e removal ao banco pós-fit e exige
igualdade com as métricas selecionadas. Em seguida, verifica **minimum pulse
width**, incluindo as verificações de período mínimo fornecidas pelo Quartus.
Os arquivos novos ficam em outro diretório; os relatórios anteriores não são
sobrescritos.

| Canto temporal | Baseline: pior slack de pulso | Secure: pior slack de pulso |
| --- | ---: | ---: |
| Slow 1200 mV, 85 °C | 9,504 ns | 9,504 ns |
| Slow 1200 mV, 0 °C | 9,519 ns | 9,518 ns |
| Fast 1200 mV, 0 °C | 9,266 ns | 9,266 ns |

Todas as margens são positivas. Esses checks se referem ao clock nos elementos
internos e aos limites de período do dispositivo; não são uma medição do pulso
UART nem substituem o AD2. A operação continua em 50 MHz, com período de 20 ns.

O Quartus reconhece as duas cadeias originais com dois registradores cada:

- `UART_RX → rx_meta → rx_sync`;
- `KEY0_N → release_pipe[0] → release_pipe[1]`.

Nos builds selecionados, a identificação permanece **Automatic** e o MTBF não
é calculado. Não atribuir aos SOFs usados na bancada o MTBF de outro fit.

## Perfis separados com identificação explícita

O script cria dois projetos de análise isolados, usando as mesmas fontes,
contextos, restrições, dispositivo e seed. Somente acrescenta as atribuições
`SYNCHRONIZER_IDENTIFICATION = FORCED IF ASYNCHRONOUS` aos quatro registradores
das duas cadeias, e as hipóteses de toggle rate às entradas das cadeias.
O Quartus refaz o fit: não basta alterar o texto de um relatório pós-fit.

| Hipótese | Valor | Interpretação |
| --- | ---: | --- |
| Transições de UART RX | 38.400/s | Uma transição por bit; não modela ruído elétrico |
| Transições de KEY0 | 6.250.000/s | Hipótese conservadora de análise, não atividade medida do botão |

Nos dois novos fits, ambas as cadeias aparecem como **User Specified**, com
dois estágios, as taxas acima e inclusão no cálculo de MTBF em todos os cantos.
O Quartus reporta `Greater than 1 Billion` para as cadeias. Isso é uma
estimativa do modelo do fabricante sob essas hipóteses, **não uma medição de
vida útil ou garantia de confiabilidade do sistema**. Não publicar um número
mais preciso nem usar esse resultado como validação de ruído, alimentação,
bounce do botão ou estabilidade prolongada da bancada.

| Perfil de análise, não programado | Baseline | Secure |
| --- | ---: | ---: |
| Elementos lógicos | 329 | 5.587 |
| Registradores | 212 | 913 |
| Bits de memória | 8.192 | 8.192 |
| Fmax mínima | 148,17 MHz | 92,55 MHz |
| Pior setup | 13,251 ns | 9,195 ns |
| Pior hold | 0,099 ns | 0,109 ns |
| Pior recovery | 14,193 ns | 11,652 ns |
| Pior removal | 0,544 ns | 2,883 ns |
| Pior minimum pulse width | 9,266 ns | 9,268 ns |

Os dois perfis atendem a 50 MHz. Mudanças de identificação influenciam
otimizações, packing e posicionamento; portanto, a variação de Fmax/LEs não
representa uma mudança do algoritmo AES nem uma medição de ganho na placa.
**A tabela do artigo permanece em 331/5.591 LEs e 117,56/92,61 MHz**, vinculada
aos builds anteriores e às suas evidências físicas. Estes perfis novos não
foram promovidos a bitstreams experimentais.

Os SOFs gerados aqui são exclusivamente de análise. Não programá-los para
uma aquisição secure: seus contextos foram copiados para manter o comparativo
e podem já estar consumidos. Uma eventual adoção dessas atribuições nos alvos
de bancada exige contexto/nonce novo, build novo, nova seleção de métricas e
revalidação física correspondente.

## Reproduzir

```bash
make timing-review
# Ou escolher explicitamente um diretório novo:
make timing-review TIMING_REVIEW_OUTPUT=build/timing-review/ensaio-novo
# Apenas reaplicar STA aos fits selecionados, sem recompilar:
python3 scripts/timing_review.py --selected-only --output build/timing-review/sta-novo
make pc
make manuscript-check
```

O diretório de saída deve ser novo; a ferramenta recusa sobrescrita. São
necessários os artefatos e bancos pós-fit locais, o contexto de elaboração
existente e o Quartus. Não é necessário conectar a FPGA, CP2102 ou GPS.
`make timing-review` usa um diretório datado por padrão.

O verificador rejeita margem negativa, não finita, repetida ou ausente;
cadeias ausentes, head/estágio incorreto, atribuição ignorada e taxas diferentes
das hipóteses. Avisos críticos do Quartus invalidam a execução mesmo que o
processo retorne zero. O resultado só recebe `PASS` depois de conferir novamente
os hashes dos builds selecionados e das fontes da análise.

O `make pc` passou em **53 testes**, incluindo sete testes novos desta
auditoria. O RTL não mudou; não foi executada uma nova regressão HDL nesta
etapa. Os manuscritos e seus hashes de build continuam aprovados.

## Evidências

- Execução completa: `build/timing-review/de10-lite-2026-09-30-02/`.
- Registro público: [JSON da auditoria](evidence/de10-lite-timing-review-2026-09-30.json).
- SHA-256 do JSON: `968b6883c11d2c352d2b71d80ed7d5f5aa1bebc6c892bbb054516abb70db74d8`.
- Horário UTC da execução completa: 14:40:33–14:45:39 em 30/09/2026.

O JSON contém resultados, hipóteses, hashes de fontes e artefatos, sem chave,
nonce ou localização GPS. Relatórios e SOFs permanecem locais. O registro
original das [métricas do artigo](metricas-fpga-2026-09-30.md) é independente.

Referências técnicas: [identificação dos sincronizadores, Altera](https://docs.altera.com/r/docs/683323/18.1/intel-quartus-prime-standard-edition-user-guide-design-recommendations/force-the-identification-of-synchronization-registers)
e [análise de metastabilidade, Intel](https://www.intel.com/content/www/us/en/docs/programmable/683068/18-1/metastability-analysis.html).
A sintaxe e o comportamento de `report_min_pulse_width`, `get_min_pulse_width`
e `report_metastability` também foram conferidos na ajuda Tcl da instalação
Quartus Prime Lite 25.1std.
