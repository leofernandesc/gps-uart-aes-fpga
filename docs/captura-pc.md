# Captura e comparação no PC

`scripts/capture.py` fornece duas operações independentes: gravar bytes de uma
porta serial Linux e comparar arquivos de referência/saída. Não programa a
FPGA nem transmite chave, nonce ou comandos para ela.

## Gravar um canal

Criar uma pasta de ensaio dentro de `data/private/` ou `build/`, ambos ignorados
pelo Git. Iniciar a gravação antes de liberar o replay:

```bash
python3 scripts/capture.py record \
  --port /dev/ttyUSB0 --bytes 1024 --timeout 10 \
  --output data/private/ensaio01/saida.bin \
  --report data/private/ensaio01/saida-captura.json
```

O diretório deve existir e os arquivos devem ser novos. O programa configura
9600/8N1, sem controle de fluxo, eco, conversão de quebra de linha ou tratamento
de caracteres especiais. Limpa a fila anterior e imprime `READY` quando está
pronto. Somente então iniciar a fonte. Os nomes de porta são exemplos: conferir
qual interface corresponde à saída da FPGA.

Gravar a referência com outra instância/canal, usando nomes distintos. Ambos
devem estar prontos antes do início. Não colocar dois leitores na mesma porta.
O GPS e a FPGA também precisam ser armados de forma a compartilhar o primeiro
byte; o programa não deduz alinhamento de ciphertext nem procura `$` nele.

`--bytes` é o número de bytes de cada arquivo; `--timeout` é o prazo total,
incluindo a espera pelo início. Ao atingir N, a gravação termina; bytes futuros
da porta não fazem parte dessa janela. Em timeout, preserva os bytes parciais,
registra `INCOMPLETE` e retorna código 1. `CAPTURED` significa apenas que N bytes
foram gravados, não que sejam os bytes corretos. O tempo registrado é do PC,
inclui USB/SO e **não é uma medida de latência da FPGA**.

## Validar uma captura bruta do GPS

Depois de gravar o TX do NEO-M8N com `capture.py record`, validar o arquivo
antes de usá-lo como referência do experimento:

```bash
python3 scripts/gps_capture.py \
  --input data/private/ensaio01/gps-reference.bin \
  --report data/private/ensaio01/gps-reference.json
```

O validador exige que a captura termine em uma sentença completa e verifica,
para cada linha, ASCII, delimitador CRLF, checksum NMEA e o limite de 82
caracteres. O relatório registra quantidade de sentenças, tipos, tamanho e
SHA-256. O arquivo de relatório é criado com permissão `0600` e não é
sobrescrito.

Esse comando comprova a integridade formal do arquivo, não sua origem física:
um arquivo sintético bem formado também pode passar. A evidência de que os
bytes vieram do NEO-M8N deve permanecer no registro de bancada, com módulo,
alimentação, porta, data e montagem. Para executar apenas a validação sem
gerar relatório:

```bash
make gps-capture-check GPS_CAPTURE=data/private/ensaio01/gps-reference.bin
```

Uma captura parcial, convertida para LF pelo terminal ou com checksum inválido
deve ser rejeitada e não pode entrar como referência do baseline/secure.

## Criar e registrar um contexto

`scripts/context.py` cria o JSON privado usado pela captura e mantém um registro
de nonces já utilizados. No modo secure, omitir `--nonce-hex` para gerar um
nonce aleatório novo:

```bash
python3 scripts/context.py new \
  --mode aes-128-ctr --bytes 1024 \
  --key-hex 000102030405060708090a0b0c0d0e0f \
  --registry data/private/nonce-registry.json \
  --output data/private/ensaio01/contexto.json
```

O programa rejeita a reutilização do mesmo nonce com a mesma chave, bloqueia
overflow do contador de 32 bits e cria contexto e registro com permissão
`0600`. O registro guarda apenas o fingerprint SHA-256 da chave; a chave fica
somente no contexto privado.

Os tops DE10-Lite aceitam `CONTEXT_KEY`, `CONTEXT_NONCE` e `CONTEXT_COUNTER`
como parâmetros de elaboração. O build Quartus agora aceita o mesmo JSON por
`CONTEXT_FILE`, gera um pacote SystemVerilog privado em `build/` e o incorpora
ao SOF. Essa é uma provisão estática no bitstream, não um protocolo de
configuração em tempo de execução. O testbench `de10_lite_uart_ctr_top_tb`
verifica o caminho com um ciphertext conhecido.

Exemplo para um ensaio secure:

```bash
CONTEXT_FILE=data/private/ensaio01/contexto.json make secure-fpga
```

Para o baseline, use um JSON criado com `--mode baseline`:

```bash
CONTEXT_FILE=data/private/ensaio01/baseline.json make baseline-fpga
```

Sem `CONTEXT_FILE`, os projetos usam o contexto público de bring-up. O pacote
gerado é temporário, tem permissão `0600` e não deve ser versionado.

Para um ensaio baseline, use `--mode baseline` sem chave, nonce ou registro.
`--nonce-hex` deve ser reservado a testes determinísticos, nunca reutilizado em
capturas reais.

## Contexto do ensaio

Guardar um JSON local com os mesmos parâmetros efetivamente carregados na
FPGA. Exemplo exclusivamente público para simulação:

```json
{
  "mode": "aes-128-ctr",
  "bytes": 1024,
  "key_hex": "000102030405060708090a0b0c0d0e0f",
  "nonce_hex": "101112131415161718191a1b",
  "initial_counter": 0
}
```

Para baseline, bastam `{"mode": "baseline", "bytes": 1024}`. N deve ser
positivo. Chave e nonce têm 16 e 12 bytes; contador é inteiro de 32 bits.
A comparação rejeita N que ultrapasse a capacidade restante do contador.

Não usar o exemplo público em capturas reais. Cada nova captura com a mesma
chave exige nonce novo, inclusive após reset. O gerador acima controla a
reutilização no registro do PC; o comando de build aplica o JSON somente ao
bitstream privado daquela captura. Proteger também o JSON de contexto; arquivos
criados pelo gravador/comparador têm permissão `0600` e nunca sobrescrevem
arquivos existentes.

## Comparar a saída

```bash
python3 scripts/capture.py compare \
  --reference data/private/ensaio01/referencia.bin \
  --received data/private/ensaio01/saida.bin \
  --context data/private/ensaio01/contexto.json \
  --recovered data/private/ensaio01/recuperado.bin \
  --report data/private/ensaio01/comparacao.json
```

O caminho com cifra usa `cryptography`/OpenSSL para decifrar; baseline compara
diretamente. O relatório registra N, contagens, faltas/excessos, primeira
divergência e hashes dos três fluxos. Não inclui chaves ou coordenadas.
Código 0 indica comparação aprovada; 1 indica divergência/captura inválida;
2 indica erro de configuração, arquivo ou operação.

Se houve reset, framing ou overflow, acrescentar, por exemplo,
`--invalid reset --invalid overflow`. Mesmo bytes idênticos não tornam uma
captura com essas ocorrências válida. A coleta automática das flags da FPGA
ainda depende da instrumentação de bancada. O serial Linux não substitui
esses diagnósticos. A comparação requer referência independente e não fornece
autenticação criptográfica.

## Testes disponíveis

```bash
make pc
make gps-capture-check GPS_CAPTURE=data/private/ensaio01/gps-reference.bin
make context
make integration
make check
```

`make pc` testa comparação, corrupção, truncamento, excesso, limites do contexto,
códigos de saída, preservação de arquivos e captura binária/timeout em uma porta
virtual Linux (PTY), incluindo `0x00`, `0xff`, CR/LF e XON/XOFF. O teste integrado
passa os bytes efetivamente decodificados do TX pelo mesmo comparador.
Nenhum desses testes comprova funcionamento de um adaptador USB–UART físico.
