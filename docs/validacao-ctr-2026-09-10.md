# CTR e adaptador por byte — validação em 10/09/2026

`make check` terminou com código 0: 20 simulações, lint dos quatro tops,
checagem estrutural e recuperação dos bytes CTR no PC por biblioteca independente.
Esse marco conclui o CTR isolado e antecipa o adaptador previsto para 11–12/09.

## Implementação

`rtl/ctr/aes128_ctr_mask.sv` conecta o AES existente a um gerador de contadores
de 32 bits com nonce de 96 bits. Ele reserva espaço antes de iniciar a cifra,
retém o resultado enquanto houver pausa e para após `0xffffffff`.

`rtl/ctr/aes128_ctr_stream.sv` acrescenta a reserva atual de 16 bytes e o XOR
com a entrada. Há duas reservas de máscara no conjunto. Somente uma transferência
aceita consome um byte. Uma mensagem de um byte pode ser processada sem esperar
um bloco completo de dados de entrada.

Cancelamento/reset invalida o contexto. Resultados AES que terminarem depois
de um cancelamento são descartados; o rearmamento aguarda o núcleo ficar livre.
O [contrato da interface](ctr.md) detalha configuração, backpressure e esgotamento.

## Resultados

| Ensaio | Resultado |
| --- | --- |
| Gerador de máscaras | 36 contextos, 73 máscaras corretas |
| Máscara retida sob backpressure | 3.327 ciclos de pausa conferidos |
| Exemplo NIST SP 800-38A F.5.1/F.5.2 | Cifragem e decifragem corretas |
| Fluxos sintéticos | 51 casos, com comprimentos de 1 a 4.097 bytes |
| Limites do contador no fluxo | Sete casos; tentativa de byte adicional bloqueada após esgotamento |
| Total do adaptador | 60 fluxos, 19.009 bytes corretos |
| Saída retida sob backpressure | 42.233 ciclos de pausa conferidos |
| Cancelamento/reset durante a operação | 70 momentos para cada mecanismo; 140 rearmes verificados |
| Conferência independente no PC | 60 fluxos recuperados, 19.009 bytes, zero divergências |
| Verilator `--Wall` | Quatro tops sem avisos |
| Estrutura Yosys | UART, AES e CTR sem problemas de conexão ou latches inferidos |

O oráculo usa `cryptography` 41.0.7 / OpenSSL 3.0.13, no Python 3.12.3.
Ele verifica primeiro o exemplo publicado pelo NIST, gera os demais casos
sintéticos e, após a simulação, lê os bytes realmente emitidos pelo testbench.
Além de comparar o ciphertext, aplica CTR novamente para recuperar a entrada.
Arquivos truncados, fora de ordem, com bytes diferentes ou excedentes causam erro.

Ferramentas HDL: Icarus Verilog 13.0 devel (`25a84d5cf-dirty`), Verilator 5.026
e Yosys 0.44 (`80ba43d26`), executadas na imagem local
`isaiassh/unic-cass-tools:1.0.7`. O aviso do Yosys sobre a
conversão de `round_keys` em registradores é esperado para o AES existente.

## Medição temporal em simulação

Com entrada válida e saída pronta, o primeiro byte é transferido **34 ciclos**
após o aceite da configuração. Com clock de 20 ns, isso corresponde a **680 ns**.
Essa medição inclui preparação da chave, geração da primeira máscara e passagem
pelas interfaces. O testbench confere o intervalo automaticamente.

É a latência de inicialização do CTR isolado. Latência serial, throughput do
sistema e ocupação da FIFO serão medidos depois da integração à UART.

## Reprodução e evidências

```bash
make ctr
make check
sha256sum -c docs/evidence/ctr-2026-09-10.sha256
sha256sum -c docs/evidence/ctr-results-2026-09-10.sha256
```

O primeiro manifesto identifica as fontes deste marco. O segundo identifica
os arquivos gerados na execução registrada; eles ficam em `build/` e precisam
existir localmente para conferência. Relatórios que incluem tempo de execução
podem ter hashes diferentes em uma nova execução.

Arquivos principais:

- `build/ctr/oracle.json`: origem, contagens, versões e hashes dos vetores;
- `build/aes128_ctr_mask.log` e `build/aes128_ctr_stream.log`: resultados RTL;
- `build/ctr/rtl-bytes.txt`: bytes efetivamente emitidos pela simulação;
- `build/ctr/pc-verification.json`: resultado e hash da saída conferida no PC;
- `build/ctr/lint.log`, `build/ctr/synth.log` e `build/check-status.txt`.

Os manifestos anteriores foram preservados. As fontes do UART, FIFO, ponte,
AES e projetos Quartus não foram alteradas nesta etapa.

## Próxima etapa

Conectar a FIFO ao CTR com retenção da resposta de leitura e enviar os bytes
cifrados pela UART TX. Validar replay serial, acrescentar o controle de sessão
e implementar configuração/captura no PC, incluindo histórico de nonces por chave.

Ainda não houve integração criptográfica à ponte, build Quartus com CTR,
programação da DE10-Lite, captura do NEO-M8N ou medição física. O `.sof` disponível
continua sendo o da ponte sem criptografia. Submissão principal em 24/09 e
contingência até 25/09 permanecem no [cronograma](cronograma.md).
