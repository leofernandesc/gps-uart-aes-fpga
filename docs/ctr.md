# AES-128-CTR: interface e funcionamento

O CTR reutiliza o [núcleo AES](aes128.md) para produzir máscaras, combinadas
com os bytes de entrada por XOR. A interface trabalha com bytes individuais;
o primeiro byte pode ser cifrado assim que houver máscara disponível.

```text
chave + nonce + contador
           │
           ▼
   aes128_ctr_mask         AES + reserva da próxima máscara
           │ 128 bits
           ▼
  aes128_ctr_stream        reserva atual, consumida do byte mais significativo
           │
byte de entrada ── XOR ── byte de saída
```

## Representação dos dados

Cada entrada do AES é `{nonce[95:0], counter[31:0]}`. O nonce tem 12 bytes; o
contador tem 4 bytes em ordem big-endian. A primeira máscara fornece os bytes
`[127:120]`, `[119:112]` e assim por diante. Depois de 16 transferências, entra
a próxima máscara.

O contador avança quando uma operação AES é iniciada e seu espaço de saída
é reservado. Ele identifica a máscara produzida, não os bytes transmitidos.
A posição do byte dentro da máscara só avança em uma transferência aceita.

`0xffffffff` é permitido uma vez; depois dele o gerador para. Nenhum incremento
atinge o nonce. A capacidade restante é `16 × (2^32 − contador_inicial)` bytes.
Uma mensagem parcial utiliza somente os bytes necessários, sem padding.

A convenção segue o modo CTR e a geração de contadores descritos na
[NIST SP 800-38A, seção 6.5 e apêndice B](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38a.pdf).
O bloqueio antes do wrap é uma restrição explícita desta implementação.

## Interface de configuração

Todos os sinais são síncronos a `clk`, exceto a asserção de `rst`. A liberação
de reset deve ser sincronizada pelo chamador, como no restante do projeto.

| Sinal | Contrato |
| --- | --- |
| `cfg_valid`, `cfg_ready` | Chave, nonce e contador são aceitos na borda em que ambos são 1 |
| `cfg_key[127:0]` | Chave AES-128 para esse contexto |
| `cfg_nonce[95:0]` | Nonce atribuído pelo controlador externo |
| `cfg_counter[31:0]` | Contador inicial, sem valor implícito |
| `active` | Existe contexto configurado; permanece ativo até `abort_req` ou reset |
| `cfg_done` | Pulso de um ciclo ao terminar a expansão da chave; a máscara ainda será calculada |
| `abort_req` | Cancela o contexto na próxima borda e bloqueia os handshakes enquanto estiver alto |
| `exhausted` | Todos os bytes permitidos foram consumidos; exige novo contexto para continuar |

Uma configuração ativa não pode ser sobrescrita. Para trocar chave, nonce ou
contador, o chamador deve abortar, aguardar `cfg_ready` e apresentar uma nova
configuração. Alterações nos pinos de configuração sem handshake não alteram
o processamento atual.

`abort_req` descarta as reservas de máscara e qualquer resultado pendente. Uma
operação AES já iniciada termina internamente, e sua saída é ignorada.
`cfg_ready` só permite rearmar depois de o núcleo estar livre. Abort não é um
procedimento de apagamento físico de chaves: o núcleo mantém suas chaves até
reset ou nova expansão.

## Transferência por byte

O adaptador tem uma reserva de 16 bytes; o gerador tem outra. O AES pode preparar
a próxima máscara enquanto a atual é consumida. Não há buffer de texto claro
ou cifrado dentro do adaptador.

Uma transferência ocorre na borda em que:

```text
in_valid && in_ready == out_valid && out_ready == 1
```

A fonte deve manter `in_valid` e `in_data` estáveis enquanto `in_ready` estiver
baixo. O consumidor pode pausar com `out_ready = 0`. O XOR é combinacional;
enquanto a fonte respeita o contrato, o ciphertext fica estável durante a pausa.
Ausência de entrada ou pausa na saída não consome bytes da máscara.

O último byte pode ser aceito na mesma borda em que a próxima máscara ocupa a
reserva atual. Se ela ainda não estiver pronta, o adaptador aplica backpressure
até a conclusão do AES. A interface não promete um byte por ciclo indefinidamente.

A conexão implementada em `uart_ctr_bridge` guarda a resposta de leitura da
`sync_fifo`, que é um pulso `rd_valid`, até o aceite do CTR/TX. Ligar esse pulso
diretamente a `in_valid` sem retenção poderia perder um byte durante uma pausa.
Ver [integração e cancelamento](integracao-uart-ctr.md).

## Parâmetros de execução

O CTR isolado não determina comprimento da aquisição, início em `$`, formato
dos comandos ou histórico de nonces. Essas decisões pertencem ao procedimento
de captura e ao software do PC; não constituem um bloco adicional no datapath.

O PC define N para cada ensaio, registra o contexto usado e compara somente os
bytes esperados. Framing error, overflow ou reset invalidam a captura. Para cada
chave, o PC deverá garantir um nonce novo em cada captura, inclusive após
reinicialização. Os testes usam somente chaves e nonces públicos; eles não
fornecem um provisionamento para uso real.

AES-CTR oferece confidencialidade. Autenticação e detecção de alterações no
ciphertext não são fornecidas por esse modo.

## Reproduzir os testes

```bash
make ctr
make check
```

`make ctr` gera vetores por `cryptography`/OpenSSL, executa os testbenches do
gerador e do adaptador, faz lint e checagem estrutural e verifica no PC os bytes
efetivamente gravados pela simulação. Os arquivos ficam em `build/ctr/`.

O conjunto cobre o exemplo público NIST em cifragem e decifragem, comprimentos
parciais, sequências longas, pausas, carry entre bytes do contador, esgotamento,
troca de chave e cancelamento/reset durante o processamento. Ver o
[relatório de validação](validacao-ctr-2026-09-10.md) para resultados medidos.
