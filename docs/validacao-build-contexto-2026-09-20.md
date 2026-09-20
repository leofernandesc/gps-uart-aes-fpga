# Validação do contexto no build FPGA — 20/09/2026

## Objetivo

Verificar que um contexto privado criado no PC pode ser aplicado aos projetos
Quartus da DE10-Lite sem adicionar um protocolo de configuração pela UART e sem
versionar chave, nonce ou captura.

## Fluxo implementado

`CONTEXT_FILE` é aceito por `make baseline-fpga` e `make secure-fpga`. O script
`scripts/quartus_build.sh` valida o JSON por `scripts/context.py`, confere se o
modo corresponde ao projeto e gera o pacote privado
`build/de10_lite/<design>/context_params.sv`, com permissão `0600`. O QSF inclui
esse arquivo antes do wrapper, que carrega os valores por parâmetros de
elaboração. Sem `CONTEXT_FILE`, o build copia o contexto público de bring-up.

Exemplo:

```bash
CONTEXT_FILE=data/private/ensaio01/contexto.json make secure-fpga
```

O contexto utilizado no teste foi temporário e removido ao final; nenhum valor
privado foi colocado no repositório. O SOF final local foi recompilado com o
contexto público de bring-up.

## Resultados

- `make context`: 7 testes aprovados, incluindo renderização do pacote e
  rejeição de modo incompatível.
- `make integration`: variantes baseline/secure aceleradas e em 50 MHz/9600,
  lint, síntese estrutural, comparação independente e wrapper parametrizado
  aprovados; o testbench confirmou `0x55 -> 0xe2`.
- `make baseline-fpga`: Quartus 25.1, 0 erros, 3 warnings, SOF gerado e três
  cantos temporais auditados. Piores margens: setup 12,459 ns, hold 0,102 ns,
  recovery 15,341 ns e removal 0,424 ns.
- Build secure com JSON privado: Quartus reconheceu o pacote gerado, terminou
  com 0 erros e 3 warnings e gerou SOF. Piores margens: setup 7,107 ns, hold
  0,099 ns, recovery 13,460 ns e removal 2,323 ns.
- `make secure-fpga` final com contexto público: 0 erros, 3 warnings, SOF
  gerado. Piores margens: setup 7,833 ns, hold 0,111 ns, recovery 12,724 ns e
  removal 2,332 ns.

As warnings do Quartus são as já conhecidas: requisitos de I/O de 3,3 V,
licença LogicLock e inferência da S-box como lógica na família MAX 10. Não houve
violação de setup, hold, recovery ou removal.

## Limite da evidência

Esta etapa comprova o fluxo de elaboração, compilação e timing. Ela não prova
programação física do novo SOF, recepção de GPS ou comparação de bytes na
bancada. Esses ensaios continuam sendo a próxima etapa física.
