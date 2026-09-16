# Validação da integração — 16/09/2026

## Resultado

`make check` terminou com código 0: 26 simulações, sete configurações de lint,
checagem estrutural e oito testes PC aprovados. O novo caminho serial foi
conferido nos modos baseline e secure, com **4.982 bytes sem divergências**.
Todos os estímulos são sintéticos/públicos. Não houve teste em placa, aquisição
GPS real, compilação Quartus integrada ou nova medida de recursos/Fmax.

| Variante | Simulação | FIFO | Fluxos | Bytes de TX conferidos |
| --- | --- | --- | --- | --- |
| Baseline | Acelerada, 32 ciclos/bit | 8 bytes | 9 | 2.442 |
| Secure | Acelerada, 32 ciclos/bit | 8 bytes | 9 | 2.442 |
| Baseline | 50 MHz / 9600, 5.208 ciclos/bit | 1.024 bytes | 4 | 49 |
| Secure | 50 MHz / 9600, 5.208 ciclos/bit | 1.024 bytes | 4 | 49 |

O clock de simulação é de 20 ns. Nos testes acelerados, apenas o divisor da
UART é reduzido para executar cenários longos; isso não altera a configuração
de produção nem cria uma comparação de baud rates no artigo.

## Cobertura nova

- Fluxos de 1, 15, 16, 17, 70, 255 e 2.049 bytes; o de 70 bytes contém uma
  sentença NMEA sintética. Uma sequência longa cobre todos os valores de byte.
- Leitura síncrona da FIFO com resposta retida durante pausa do TX; máscara
  consumida somente no aceite do quadro seguinte, sem duplicação/perda.
- Entrada antes da configuração ignorada; tentativa de reconfigurar contexto
  ativo rejeitada; referência comparada após recuperação com chave/nonce novos.
- Overflow e stop inválido interrompem a aquisição e preservam diagnóstico.
- No secure, contador `0xffffffff` entrega seus 16 bytes, conclui o último
  quadro e não transmite o 17º. Não há wrap nem interrupção do último stop.
- 32 cancelamentos por variante acelerada: 24 fases da inicialização, abort e
  reset durante TX e seis posições próximas da resposta de leitura da FIFO.
- Decodificador observa apenas o fio TX. O PC verifica ordem, número e valor
  dos bytes efetivamente serializados e usa `cryptography`/OpenSSL para recuperar
  o texto claro. Não usa resultados internos do DUT como oráculo.
- Yosys: sem latches/problemas estruturais; módulos AES ausentes na elaboração
  do baseline. O aviso de expansão de `round_keys` em registradores é esperado
  para a organização existente do núcleo AES.

Os testes antigos também passaram: UART RX/TX, loopback, UART de osciloscópio,
FIFO, ponte, 866 vetores AES e 60 fluxos CTR/19.009 bytes. A integração acrescenta
quatro simulações às 22 anteriores, sem modificar suas fontes RTL.

## Software PC

Oito testes cobrem baseline/cifra, todos os valores de byte, corrupção,
truncamento, excesso, contexto inválido, wrap, flags de invalidação, códigos
de saída, arquivos exclusivos com permissão `0600`, porta virtual Linux e
timeout com preservação de captura parcial. Também conferem a restauração
da configuração da porta após a gravação.

A verificação do TX integrado chama o mesmo comparador disponibilizado pela
CLI. O gravador PTY não representa um adaptador USB–UART físico. A interface
do PC ainda não provisiona a FPGA nem gerencia um histórico persistente de
nonces; essas são as próximas entregas.

## Reprodução e evidências

```bash
make integration
make pc
make check
git diff --check
```

Ferramentas desta execução:

- Icarus Verilog 13.0 devel, `s20221226-554-g25a84d5cf-dirty`;
- Verilator 5.026;
- Yosys 0.44, `80ba43d26`;
- Python 3.12.3, `cryptography` 41.0.7, OpenSSL 3.0.13;
- imagem Docker local `isaiassh/unic-cass-tools:1.0.7`, sem rede;
- início da regressão completa: `2026-09-16T04:19:49Z`.

Artefatos locais: `build/integration_*.log`, `build/integration/verification.json`,
arquivos `baseline-fast.txt`, `baseline-50mhz.txt`, `secure-fast.txt` e
`secure-50mhz.txt` dentro de `build/integration/`, logs de lint/estrutura,
`pc-tests.log`, `build/tool_versions.txt` e
`build/check-status.txt`. O [manifesto deste marco](evidence/integracao-2026-09-16.sha256)
identifica fontes e resultados. Logs com tempos/versões podem mudar em outra
execução; o manifesto registra esta execução, não substitui os verificadores.
Os manifestos históricos anteriores não foram reescritos.

GitHub conferido antes do desenvolvimento e novamente após a validação:
`origin/main` permaneceu em `bb0f15f`, sem commits novos de colaboradores.
Não foi necessário pull/merge de contribuições externas. Desenvolvimento em
`feature/uart-ctr-integration`, mantendo os alvos UART existentes intactos.

## Próxima entrega

Implementar o carregamento de `cfg_*` no wrapper e o registro persistente de
nonces, definir o início alinhado da aquisição e gerar os builds comparáveis
baseline/secure da DE10-Lite. Auditar inclusive recovery/removal dos resets
do caminho integrado. A Cyclone IV continua dependendo da identificação de
placa, dispositivo, clock e pinagem. O [cronograma](cronograma.md) mantém
submissão em 24/09 e contingência/encerramento em 25/09.
