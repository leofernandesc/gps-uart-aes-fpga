# AES-128 isolado — validação em 09/09/2026

**Resultado:** `make check` e `make aes-fpga` concluídos com código 0. AES-128
iterativo implementado e validado sem placa. A DE10-Lite continua indisponível;
não houve programação, captura do NEO-M8N ou medição física. CTR e integração
criptográfica à ponte UART ainda não estão implementados.

## Implementação

Cinco módulos RTL cobrem S-box, SubBytes/ShiftRows, MixColumns, expansão de
chave e controle da cifra. Datapath de 128 bits reutilizado, duas fases por
rodada e onze chaves de rodada armazenadas. O [contrato](aes128.md) documenta
ordem dos bytes, handshakes, prioridade de chave, reset e latência.

UART v2, FIFO, ponte, seus testbenches e projeto Quartus de bancada mantêm os
hashes do marco anterior. Makefile e executores foram ampliados para incluir
AES; os manifestos históricos foram preservados, não atualizados retroativamente.
O modelo GPS informado foi registrado como NEO-M8N-010; o conector da placa de
suporte ainda será conferido antes da alimentação.

## Verificação funcional

As **18 simulações** da regressão passaram: quatro históricas, sete de UART,
três de FIFO, duas da ponte e duas de AES. Os três tops passaram no Verilator
com `--Wall`; UART e AES passaram na checagem estrutural Yosys sem latches.

| Cobertura AES | Resultado |
| --- | --- |
| S-box independente, calculada por álgebra em GF(256) | 256 valores corretos |
| Expansão de chave de referência | Dez chaves derivadas corretas |
| Transformações de estado | Estados publicados + 384 entradas conferidos |
| NIST CAVP, arquivos originais com SHA-256 | 284 casos ENCRYPT corretos |
| Exemplos publicados | Seis resultados corretos |
| Entradas sintéticas reprodutíveis | 512 com troca de chave + 64 com reuso |
| Núcleo completo | 866 vetores, 870 conclusões corretas e 687 preparações de chave |
| Controle | Prioridade, busy, rekey, start mantido alto e reset em 28 estágios |

Os quatro resultados adicionais aos 866 vetores exercitam controle, recuperação
após reset e start mantido. Contagens de preparações incluem também os ensaios
de reset. Pedidos durante busy não interromperam nem enfileiraram operações.

O oráculo usa Python `cryptography`/OpenSSL sem importar/ler o RTL. Ele confere
também sua própria saída contra os ciphertexts publicados. Os arquivos
[NIST CAVP](https://csrc.nist.gov/projects/cryptographic-algorithm-validation-program/block-ciphers)
ficam em `reference/aes-cavp/`; executar esses testes **não é certificação CAVP/FIPS**.
NMEA sintética dos testes anteriores não equivale a dados GPS reais.

| Medição no testbench, clock de 20 ns | Ciclos | Tempo |
| --- | ---: | ---: |
| Preparação da chave | 10 | 200 ns |
| Aceitação do bloco até conclusão | 20 | 400 ns |
| Menor intervalo entre aceitações | 21 | 420 ns |

Derivação ideal do throughput do núcleo com chave pronta: 304,76 Mbit/s.
Não é taxa da UART, latência ponta a ponta nem medição em hardware.

## Quartus: recursos e timing interno

Quartus Prime Lite 25.1std.0 build 1129, dispositivo 10M50DAF484C7G, seed 1,
dois processos, clock de 50 MHz. Fit concluído em 09/09 às 08:49:33 (-04).

| Métrica do harness AES isolado | Resultado |
| --- | ---: |
| Elementos lógicos | 6.482 / 49.760 (13%) |
| Registradores | 1.813 |
| Bits de memória / multiplicadores / PLLs | 0 / 0 / 0 |
| Pino físico de clock / pinos virtuais | 1 / 393 |
| Menor Fmax interna reportada | 77,91 MHz |

Inclui os dois registradores de sincronização de reset. LEs e registradores
são categorias sobrepostas. S-boxes e chaves foram mapeadas em lógica/registradores,
não M9K. Não somar estes recursos aos da ponte para obter uma área supostamente
integrada: será necessária nova compilação do sistema completo.

| Modelo | Fmax (MHz) | Setup (ns) | Hold (ns) | Recovery (ns) | Removal (ns) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Slow, 1.200 mV, 85 °C | 77,91 | 7,164 | 0,341 | 13,041 | 5,882 |
| Slow, 1.200 mV, 0 °C | 83,79 | 8,066 | 0,306 | 13,629 | 5,321 |
| Fast, 1.200 mV, 0 °C | 168,24 | 14,056 | 0,148 | 16,379 | 2,846 |

Os valores são análise estática pós-fit, não medições físicas. As interfaces
virtuais foram explicitamente excluídas do timing; só os caminhos internos e
a liberação interna de reset estão cobertos. Isso não certifica a futura
integração CTR/UART nem qualquer interface elétrica. Ver o
[alcance exato do ensaio](../fpga/aes_analysis/README.md).

`check_timing` reportou as quantidades previstas de portas virtuais sem delay
e ausência de clock virtual; demais categorias foram zero. O relatório de
caminhos sem restrição tem seis categorias zeradas, considerando as exceções
explícitas. Não confundir isso com verificação das interfaces excluídas.

## Ajustes e avisos conferidos

- Armazenamento das chaves separado em blocos de índice constante para eliminar
  o aviso de estado/latch associado ao contador do laço de reset.
- Dependências da expansão expressas por quatro palavras distintas; lint sem
  aviso de realimentação aparente entre fatias de um mesmo barramento.
- Testbench usa redução-XOR para detectar qualquer X/Z nos controles, evitando
  o comportamento divergente observado com `$isunknown` sobre concatenação.
- A primeira tentativa de timing modelava as entradas virtuais com delay zero
  e apresentou violações de hold na fronteira. Essa modelagem foi retirada:
  o resultado final é deliberadamente interno, **não uma correção comprovada
  de timing dessas interfaces**. O SDC isolado não deve ser usado na integração.
- Yosys avisa que `round_keys` virou registradores, conforme a arquitetura.
  A checagem de latches e conexões passou; não são métricas de FPGA/ASIC.
- Quartus final: zero erros, zero avisos de síntese, dois avisos de fit:
  LogicLock/licença (292013, recurso não usado) e requisitos elétricos de I/O
  3,3 V (169177, conferência de bancada pendente). STA sem avisos/erros.

## Reprodução

```bash
sha256sum -c docs/evidence/aes128-2026-09-09.sha256
make check
make aes-fpga
```

Para testar somente o novo bloco, usar `make aes`. O oráculo requer Python 3
e `cryptography` no host; HDL usa ferramentas nativas ou a imagem Docker local
`isaiassh/unic-cass-tools:1.0.7`, sem rede. Neste ensaio: Python 3.12.3,
cryptography 41.0.7, OpenSSL 3.0.13; Icarus 13.0 devel, Verilator 5.026 e
Yosys 0.44. Quartus roda diretamente no Linux.

Saídas em `build/`, ignoradas pelo Git:

- `check-status.txt`, `aes_components.log`, `aes128_core.log` e `aes-regression-run.log`.
- `aes/oracle.json`, `aes/vectors.txt`, `aes/lint.log` e `aes/synth.log`.
- `quartus_aes/`: status, relatórios de fit, Fmax, slacks, restrições e exceções.

SHA-256 do conjunto de vetores gerado:
`f26c1ea07baa9f0666a890052a6eef6c92c7569b27c3d45797c76f8899944d78`.
O manifesto de fontes inclui scripts, RTL, testes e projetos; os resultados
gerados têm manifesto separado, válido para este ensaio específico.

**Próxima entrega:** CTR por byte e testes de nonce/contador, limites,
backpressure e comprimentos parciais; depois, sessões e integração serial.
Não usar este núcleo isolado como se já fosse um canal criptografado completo.
