# Validação do contexto de experimento — 19–20/09/2026

## Objetivo

Preparar, sem a placa e sem o GPS, os metadados que serão usados em cada
captura baseline/secure. O contexto deve registrar o tamanho do ensaio e, no
modo AES-CTR, a chave, o nonce e o contador inicial. O registro persistente não
deve guardar a chave em claro nem permitir a reutilização do mesmo nonce com a
mesma chave.

## Implementação

`scripts/context.py` fornece o comando `new` para dois modos:

- `baseline`: cria somente o tamanho e a identificação do ensaio;
- `aes-128-ctr`: valida a chave de 128 bits, gera nonce de 96 bits quando ele
  não é fornecido e registra o fingerprint SHA-256 da chave.

Os JSONs privados, o registro, o arquivo de lock e o pacote SystemVerilog
gerado são criados com permissão `0600`. A atualização do registro usa lock e
substituição atômica. O utilitário também rejeita saída já existente, contador
fora do intervalo de 32 bits e ensaios que ultrapassariam o contador. O build
Quartus aceita o JSON por `CONTEXT_FILE`, valida o modo solicitado e gera o
pacote em `build/de10_lite/<design>/context_params.sv`; a configuração continua
estática no bitstream e não é um protocolo de runtime.

## Verificações executadas

```bash
make context
make pc
make integration
make secure-fpga
```

Resultados:

- `make context`: 7 testes aprovados;
- `make pc`: 15 testes aprovados, incluindo os testes anteriores de captura e
  comparação;
- `make integration`: variantes baseline/secure aceleradas e em 50 MHz/9600,
  lint, estrutura e comparação independente aprovados.

Depois dessas verificações, `make check` também terminou com código 0, cobrindo
27 simulações, sete configurações de lint, a estrutura dos tops e os 15 testes
do PC.

O testbench do wrapper DE10-Lite substituiu o contexto padrão por uma chave,
nonce e contador de teste. Observando somente o TX serial, confirmou
`0x55 -> 0xe2`, conforme o oráculo independente AES-CTR. O teste também exigiu
um bit de repouso após a ativação do datapath, condição necessária para o
rearme do receptor UART.

Os dados temporários permanecem em `build/` ou `data/private/` e não entram no
versionamento. A aplicação do contexto ao build está validada; ainda falta
programar os tops baseline/secure e validar o tráfego na placa, sem alterar o
contrato UART fixo em 50 MHz, 9600 baud e 8N1.
