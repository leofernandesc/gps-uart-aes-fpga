# Análise isolada do AES no Quartus

Executar `make aes-fpga` na raiz ou abrir `aes128_analysis.qpf` no Quartus.
O projeto usa MAX 10 10M50DAF484C7G, clock de 50 MHz, seed 1 e duas threads.
Inclui somente `aes128_core` e um sincronizador de reset de dois registradores.

Os 393 sinais de interface, exceto clock, são **pinos virtuais**: permitem que
o Quartus preserve os operandos e resultados sem exigir centenas de GPIOs físicos.
O script roda síntese, fit e análise estática. **Não roda o Assembler, não gera
`.sof` e não oferece pinagem para conectar o GPS.** O projeto de bancada continua
em `fpga/de10_lite/`.

## O que o timing significa

Este é um ensaio de **timing interno entre registradores**, não o fechamento
temporal das interfaces com o futuro CTR/UART. Os 258 inputs de dados/controle
e 134 outputs virtuais têm exceções explícitas de fronteira no SDC. O reset
externo é cortado somente até os dois registradores de entrada do sincronizador;
a liberação interna de reset permanece sob análise.

Não foram inventados atrasos externos de zero para representar circuitos ainda
ausentes. As fronteiras virtuais não modelam GPIO, cabo nem os registradores
dos futuros produtores/consumidores. Esses caminhos terão de ser analisados
na compilação do sistema integrado; **não copiar as exceções deste SDC para lá**.

O script audita setup, hold, recovery e removal nos três modelos do dispositivo.
Slacks negativos ou ausência de cobertura interrompem o comando. `check_timing`
lista 259 inputs sem delay (incluindo reset), 134 outputs sem delay e ausência
de clock virtual: quantidades previstas apenas neste ensaio. Demais categorias
devem ser zero. Zero caminhos sem restrição no relatório considera as exceções,
não significa que interfaces excluídas foram verificadas.

As métricas de recursos incluem o sincronizador. Não somar LEs e registradores,
nem somar esta área isolada à da ponte e apresentar como área do sistema: fit,
otimizações e lógica de integração alteram o resultado. Fmax é estimativa estática
interna; medições de placa e energia continuam pendentes.

## Resultados locais

`build/quartus_aes/` contém `build-status.txt`, versão do Quartus, logs de
map/fit, `aes128_analysis.fit.summary`, relatório hierárquico e relatórios de
timing por modelo. O status só recebe PASS se toda a auditoria terminar.
O manifesto do marco em `docs/evidence/` identifica as fontes utilizadas.
