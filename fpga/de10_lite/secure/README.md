# DE10-Lite secure

Este projeto implementa a variante segura do artigo:

```text
UART RX -> FIFO -> AES-128-CTR -> UART TX
```

Parâmetros fixos: clock de 50 MHz, UART 9600 baud/8N1, dispositivo
`10M50DAF484C7G`, RX no `V10` e TX no `W10`.

O wrapper carrega automaticamente um contexto de teste após o reset. A chave,
o nonce e o contador estão documentados no RTL somente para o primeiro
bring-up; isso não representa um mecanismo de gerenciamento de chaves para
uso real.

Na raiz do repositório:

```bash
make secure-fpga
```

O SOF é gerado em `build/de10_lite/secure/uart_secure.sof`. A compilação não
programa a placa.
