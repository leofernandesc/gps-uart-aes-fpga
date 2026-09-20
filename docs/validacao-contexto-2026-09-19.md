# Validação do contexto de experimento — 19/09/2026

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

Os JSONs privados, o registro e o arquivo de lock são criados com permissão
`0600`. A atualização do registro usa lock e substituição atômica. O utilitário
também rejeita saída já existente, contador fora do intervalo de 32 bits e
ensaios que ultrapassariam o contador. Ele prepara o contexto no PC, mas ainda
não o envia para a FPGA.

## Verificações executadas

```bash
make context
make pc
make integration
```

Resultados:

- `make context`: 5 testes aprovados;
- `make pc`: 13 testes aprovados, incluindo os testes anteriores de captura e
  comparação;
- `make integration`: variantes baseline/secure aceleradas e em 50 MHz/9600,
  lint, estrutura e comparação independente aprovados.

Depois dessas verificações, `make check` também terminou com código 0, cobrindo
26 simulações, sete configurações de lint, a estrutura dos tops e os 13 testes
do PC.

Os dados temporários permanecem em `build/` ou `data/private/` e não entram no
versionamento. A etapa seguinte é conectar o contexto ao wrapper de bancada,
sem alterar o contrato UART fixo em 50 MHz, 9600 baud e 8N1.
