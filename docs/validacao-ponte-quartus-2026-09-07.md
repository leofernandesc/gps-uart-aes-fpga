# Ponte UART e primeira compilação Quartus — 07/09/2026

Este documento e seu manifesto registram o marco de 07/09. Em 08–09/09, o
Makefile e os executores foram ampliados para o AES; portanto, seus hashes
atuais diferem dos históricos. As fontes e os testes da ponte foram preservados.
O marco seguinte está em [validação do AES](validacao-aes-2026-09-09.md).

**Resultado:** `make check` e `make fpga` concluídos com código 0. A ponte sem
cifra foi simulada e compilada para a DE10-Lite. A placa não estava disponível;
não houve programação, captura de GPS, teste elétrico ou medição física.

## Implementação entregue

- `sync_fifo`: RAM síncrona de 1.024 × 8 bits, ocupação, ocupação máxima e
  overflow explícito. O dado mais novo é rejeitado quando a fila cheia não tem
  leitura simultânea. Reset invalida os dados sem zerar toda a memória.
- `uart_bridge`: RX v2 → FIFO → TX v2, pausa interna de consumo e indicação
  persistente de framing/overflow. O TX termina um byte já aceito antes da pausa.
- `de10_lite_uart_top`: clock e serial fixos, reset por KEY0 e dez LEDs de
  diagnóstico. O QSF reserva GPIO[0] para RX e GPIO[1] para TX.
- Projeto `.qpf`/`.qsf`, SDC de 20 ns e comandos reproduzíveis de compilação e
  auditoria temporal. As fontes do UART v2 e do sincronizador de reset mantêm
  os hashes do marco anterior; Makefile e executor foram ampliados.

## Testes RTL

Os quatro testes históricos e as sete configurações do UART v2 passaram
novamente. Os cinco novos ensaios também passaram:

| Ensaio | Resultado |
| --- | --- |
| FIFO, profundidade 2 | 20.020 ciclos; 8.105 leituras corretas; 1.911 escritas rejeitadas e sinalizadas |
| FIFO, profundidade 8 | 20.052 ciclos; 10.033 leituras corretas; 1 escrita rejeitada e sinalizada |
| FIFO, profundidade 1.024 | 25.132 ciclos; 13.081 leituras corretas; 1 escrita rejeitada e sinalizada |
| Ponte acelerada, FIFO 8 | 340 bytes decodificados corretamente; inclui overflow provocado |
| Ponte 50 MHz/9600, FIFO 1.024 | 92 bytes decodificados corretamente; serial externa com período nominal fracionário |

As rejeições na tabela são estímulos intencionais de fila cheia, não falhas
inesperadas. Os testes da FIFO cobrem vazio, cheio, escrita/leitura simultâneas
no mesmo endereço, retorno dos ponteiros, sequência pseudoaleatória reproduzível
e reset com dados pendentes. Um modelo de fila independente confere cada leitura.

Na ponte, o decodificador observa o sinal serial TX. São verificados uma
sentença NMEA sintética, bytes binários, pausa da saída, retomada, erro de stop,
break e reset durante transmissão com dados ainda na FIFO. O caso acelerado
testa os 256 valores de byte e força overflow; o teste de produção não provoca
overflow por serial, mas a FIFO de produção é exercitada cheia no teste unitário.
NMEA sintética é estímulo de transporte, não evidência de aquisição GPS real.

Verilator `--lint-only --Wall` passou tanto para `uart_top` quanto para o top
da placa. A checagem estrutural Yosys do UART também passou. Ferramentas HDL:
mesma imagem Docker local `isaiassh/unic-cass-tools:1.0.7` do marco anterior.

## Resultados pós-fit

Quartus Prime Lite **25.1std.0, build 1129**, MAX 10 **10M50DAF484C7G**, seed 1,
dois processos permitidos, clock de 50 MHz. Fit final registrado em
07/09/2026 às 20:38:41, horário local do ambiente.

| Métrica do build da ponte | Resultado |
| --- | --- |
| Elementos lógicos | 278 / 49.760 |
| Registradores | 166 |
| Bits de memória | 8.192 |
| Blocos M9K | 1 |
| Pinos usados | 14 |
| PLLs / multiplicadores | 0 / 0 |
| Menor Fmax reportada | 140,27 MHz |
| Clock de operação especificado | 50 MHz |

A Fmax é resultado da análise estática do Quartus; não foi medida na placa.
LEs e registradores são categorias sobrepostas e não devem ser somados.
O build inclui FIFO e indicadores, mas não AES nem controle de sessões. Estas
métricas são preliminares: o comparativo do artigo exigirá recompilar os dois
caminhos com o mesmo controle e instrumentação.

| Modelo | Setup (ns) | Hold (ns) | Recovery (ns) | Removal (ns) |
| --- | ---: | ---: | ---: | ---: |
| Slow, 1.200 mV, 85 °C | 12,871 | 0,238 | 14,270 | 5,132 |
| Slow, 1.200 mV, 0 °C | 13,468 | 0,247 | 14,716 | 4,627 |
| Fast, 1.200 mV, 0 °C | 16,927 | 0,092 | 17,092 | 2,448 |

Todos os slacks auditados são positivos. Os relatórios de caminhos sem
restrição reportaram zero em setup/hold, considerando as exceções explícitas
do SDC para os pinos assíncronos. `check_timing` lista dois inputs sem delay,
onze outputs sem delay e ausência de clock virtual, esperados neste contrato;
os demais itens reportaram zero. Isso não equivale a verificar timing elétrico
externo. [O README da placa](../fpga/de10_lite/README.md) explica as exceções.

O Quartus reconheceu duas cadeias de sincronização com dois registradores,
correspondentes a RX e reset. Não calculou MTBF; não há alegação quantitativa
de confiabilidade contra metastabilidade.

## Avisos conferidos

O fluxo final teve zero erros e três avisos:

- **276020:** lógica adicional inferida para manter o comportamento de leitura
  durante escrita da RAM. O relatório de memória confirma um M9K, 1.024 × 8,
  leitura de dado antigo; a lógica adicional já está incluída no uso de LEs.
- **292013:** aviso de disponibilidade do recurso LogicLock por licença. O
  projeto não define regiões LogicLock; o fit Lite foi concluído.
- **169177:** requisitos elétricos das entradas MAX 10 em 3,3 V. A conferência
  dos níveis da fonte UART e da montagem continua sendo uma etapa de bancada.

## Reprodução e evidências

Na raiz do projeto:

```bash
sha256sum -c docs/evidence/uart-bridge-quartus.sha256
make check
make fpga
```

Arquivos gerados, ignorados pelo Git:

- `build/check-status.txt`, logs `build/sync_fifo_*.log`,
  `build/uart_bridge_*.log` e `build/bridge-lint.log`.
- `build/quartus/uart_bridge.sof`: configuração volátil via JTAG; não foi carregada.
- `build/quartus/uart_bridge.fit.summary` e `.fit.rpt`: recursos e mapeamento RAM.
- `build/quartus/timing-audit.log`, `*_corner*.rpt`, `check_timing.rpt`,
  `unconstrained.rpt`, `exceptions.rpt` e `metastability.rpt`.

O manifesto novo identifica as fontes e os executores deste marco. O manifesto
`uart-baseline-v2.sha256` continua identificando o commit histórico `5d07790`.
O projeto Quartus pode ser aberto por
[uart_bridge.qpf](../fpga/de10_lite/uart_bridge.qpf).

**Próxima entrega sem depender da placa:** AES-128 iterativo isolado, com
vetores NIST e comparação independente; depois, CTR e controle de sessões.
Programação e comparação de dados reais de GPS continuam pendentes.
