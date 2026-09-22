# Analog Discovery 2 e WaveForms

Este documento registra a instalação do WaveForms no Ubuntu e define como o
Analog Discovery 2 (AD2) deve ser usado como instrumento de validação física do
projeto GPS + UART + AES-128-CTR. Ele é complementar aos roteiros de bancada da
[DE10-Lite](bancada-de10-lite-integrada-2026-09-22.md) e da
[Cyclone IV](bancada-cyclone4-2026-09-21.md).

O AD2 fornece evidência elétrica e temporal. Ele não substitui a fonte serial,
o receptor no PC, o ESP32, o adaptador USB–UART ou o GPS. Uma forma de onda
correta também não prova, sozinha, que os bytes foram recuperados corretamente:
essa parte continua sendo verificada pelo host e pelos comparadores do projeto.

## Estado da instalação — 22/09/2026

O computador é Ubuntu 24.04 amd64, compatível com a versão Qt6 do WaveForms.
Os pacotes oficiais foram baixados pelo navegador depois que os downloads por
terminal foram bloqueados pelo Cloudflare e instalados nesta ordem:

| Pacote | Versão | Arquitetura | Situação |
| --- | --- | --- | --- |
| Digilent Adept Runtime | `2.30.1` | `amd64` | `install ok installed` |
| Digilent WaveForms | `3.25.1` | `amd64` | `install ok installed` |
| `libqt6serialport6` | `6.4.2-4build2` | `amd64` | dependência instalada |

Arquivos usados na instalação:

```text
digilent.adept.runtime_2.30.1_amd64.deb
SHA-256: e5e51d2640c2ff34ef3b436f3bdf37838120b15160d73dfbab82e90773b6b372

digilent.waveforms_3.25.1_amd64.deb
SHA-256: d2979aab726c9202a48a1c5d2b314531513171c0b62fa2f2a2edcd29202727d3
```

Verificações realizadas:

- `/usr/bin/waveforms` instalado;
- `/usr/bin/dwfcmd` instalado;
- `/usr/lib/libdwf.so.3.25.1` instalado e disponível como `libdwf.so`;
- headers do SDK em `/usr/include/digilent/waveforms/`;
- exemplos e documentação em `/usr/share/digilent/waveforms/`;
- regra USB em `/etc/udev/rules.d/52-digilent-usb.rules`;
- lançador `/usr/share/applications/digilent.waveforms.desktop` disponível no
  menu de aplicativos;
- WaveForms iniciado sem erro detectável, ainda sem hardware conectado.

O AD2 não estava conectado durante a instalação. Portanto, a enumeração física
continua pendente. `dwfcmd enumerate` retorna sucesso, mas não lista nenhum
dispositivo quando o instrumento está ausente.

## Instalação para futuros colaboradores

Antes de instalar, ler `AGENTS.md`, `README.md` e `docs/cronograma.md`. O
repositório deve ser atualizado com `git fetch` e revisão das alterações
remotas antes de qualquer `pull`; não fazer pull cego.

### 1. Conferir o sistema

```bash
uname -m
. /etc/os-release
printf '%s %s\n' "$ID" "$VERSION_ID"
getconf GNU_LIBC_VERSION
```

Para este projeto, o pacote usado é o Linux Intel/AMD 64-bit. O WaveForms
3.25.1 oficial requer Ubuntu 22.04 ou superior e glibc 2.35 ou superior na
variante Qt6. A página de versões e os links oficiais estão em:

- [WaveForms — versões oficiais](https://digilent.com/reference/software/waveforms/waveforms-3/previous-versions)
- [Como baixar o WaveForms](https://support.digilent.com/hc/en-us/articles/16470375224475-How-to-download-WaveForms)
- [Manual de instalação do WaveForms 3.25.1](https://files.digilent.com/manuals/WaveForms/3.25.1/main.html)

### 2. Obter os pacotes

Os arquivos necessários para Ubuntu amd64 são:

- [Adept Runtime 2.30.1](https://files.digilent.com/Software/Adept2%20Runtime/2.30.1/digilent.adept.runtime_2.30.1_amd64.deb)
- [WaveForms 3.25.1](https://files.digilent.com/Software/Waveforms/3.25.1/digilent.waveforms_3.25.1_amd64.deb)

Na tentativa anterior, `curl`, endpoints S3 e algumas alternativas do site
receberam HTTP 403. O servidor `files.digilent.com` respondeu com
`cf-mitigated: challenge`; o conteúdo recebido era uma página de desafio, não
um pacote Debian. Por isso:

- não instalar um arquivo que `file` identifique como HTML;
- não renomear uma página de erro para `.deb`;
- não usar espelhos não verificados para substituir os pacotes oficiais;
- se o terminal receber 403, abrir a página no navegador e completar o desafio
  Cloudflare pela sessão gráfica;
- confirmar que os dois arquivos chegaram a `~/Downloads` antes de instalar.

Verificação mínima dos arquivos:

```bash
find "$HOME/Downloads" -maxdepth 1 -type f \
  \( -name 'digilent.adept.runtime*.deb' -o -name 'digilent.waveforms*.deb' \) \
  -printf '%f\t%s bytes\n'

file "$HOME/Downloads/digilent.adept.runtime_2.30.1_amd64.deb" \
  "$HOME/Downloads/digilent.waveforms_3.25.1_amd64.deb"

dpkg-deb --info "$HOME/Downloads/digilent.adept.runtime_2.30.1_amd64.deb"
dpkg-deb --info "$HOME/Downloads/digilent.waveforms_3.25.1_amd64.deb"
```

O resultado de `file` deve indicar `Debian binary package`. Os metadados devem
mostrar arquitetura `amd64` e dependência do WaveForms em
`digilent.adept.runtime`.

### 3. Instalar na ordem correta

O Adept Runtime é a camada de comunicação USB usada pelo WaveForms. Instalar o
Runtime antes do aplicativo:

```bash
sudo apt install \
  "$HOME/Downloads/digilent.adept.runtime_2.30.1_amd64.deb" \
  "$HOME/Downloads/digilent.waveforms_3.25.1_amd64.deb"
```

O `apt` pode buscar dependências Ubuntu, como `libqt6serialport6`. A senha do
Ubuntu deve ser digitada localmente no prompt; nunca deve ser colocada em logs,
issues ou mensagens do repositório.

### 4. Validar a instalação

```bash
dpkg-query -W -f='${binary:Package}\t${Version}\t${Status}\n' \
  digilent.adept.runtime digilent.waveforms

command -v waveforms
command -v dwfcmd
ldconfig -p | grep -E 'libdwf|libdabs'
test -f /etc/udev/rules.d/52-digilent-usb.rules

sudo udevadm control --reload-rules
```

O estado esperado dos pacotes é `install ok installed`. Se o instrumento já
estiver conectado, desconectá-lo e conectá-lo novamente depois de recarregar as
regras USB.

### 5. Detectar o AD2

Com o cabo USB conectado:

```bash
lsusb | grep -i -E 'digilent|analog|discovery'
dwfcmd enumerate
waveforms
```

`dwfcmd enumerate` deve listar pelo menos um dispositivo. O WaveForms também
pode ser aberto pelo menu de aplicativos. A enumeração só prova que o USB e o
driver encontraram o instrumento; ainda é necessário configurar e executar a
captura.

Se não houver detecção:

1. usar o cabo USB original ou outro cabo de dados;
2. testar outra porta USB, preferencialmente sem hub;
3. conferir se o LED de alimentação do AD2 acende;
4. desconectar e reconectar após recarregar as regras udev;
5. verificar `dmesg --ctime | tail -80` imediatamente após conectar;
6. conferir se outro processo WaveForms está segurando o dispositivo;
7. revisar permissões e a presença de `52-digilent-usb.rules`.

Não marcar a instalação como validada fisicamente apenas porque o aplicativo
abre sem erro: a validação física começa quando `dwfcmd enumerate` lista o
instrumento.

## Uso do AD2 na validação física

### Instrumentos e responsabilidades

| Instrumento | Responsabilidade |
| --- | --- |
| AD2 — Scope | Forma de onda analógica, níveis, bit time, bordas e RX→TX |
| AD2 — Logic/Protocol UART | Decodificação digital opcional dos bytes UART |
| ESP32 ou CP2102 | Fonte/receptor serial e log de bytes no PC |
| GPS NEO-M8N | Fonte física das sentenças NMEA |
| Quartus/USB-Blaster | Programação e identificação da FPGA |

O AD2 não é um USB–UART. Ele não deve ser usado como fonte única para provar
que o GPS foi recebido nem como substituto do verificador AES. Para o artigo,
usar o ESP32 ou o CP2102 para transportar os bytes e o AD2 para produzir a
evidência elétrica/temporal independente.

### USB–UART TTL: obrigatório ou opcional?

Para o arranjo atual, o adaptador USB–UART TTL **não é obrigatório**:

| Situação | Adaptadores necessários |
| --- | ---: |
| P03/P05 com vetor conhecido, usando ESP32 como fonte e receptor | 0 |
| P04/P06 com AD2 observando RX/TX | 0 adicionais; o AD2 fornece a captura |
| GPS e AD2 capturando simultaneamente GPS TX e FPGA TX | 0, desde que os dois sinais sejam lidos pelos DIOs do AD2 |
| GPS com captura serial convencional no PC, sem usar o AD2 como segundo canal | 1 |
| Dois canais independentes feitos exclusivamente por USB–UART | 2 |

O AD2 consegue observar os dois sinais ao mesmo tempo, e o ESP32 já funciona
como fonte/receptor para os vetores conhecidos. Portanto, não comprar dois
adaptadores apenas por causa deste projeto. Se for desejada uma interface
serial convencional como redundância, comprar **um** CP2102 configurado para
I/O lógico de 3,3 V é suficiente: ele pode capturar a referência do GPS ou a
saída da FPGA, enquanto o AD2 observa o outro canal.

Um único CP2102 não captura dois fluxos seriais independentes ao mesmo tempo.
Nesse caso, usar o segundo canal do AD2 ou o ESP32 para o outro fluxo. O
adaptador também não deve alimentar a FPGA ou o GPS automaticamente: conectar
TX, RX e GND conforme o ensaio e manter as fontes separadas. O pino de I/O
deve estar em 3,3 V; nunca conectar a saída lógica de 5 V aos pinos da FPGA,
do GPS ou do ESP32.

Recomendação de compra: um CP2102 TTL com nível lógico de 3,3 V, para servir
como interface serial independente e plano de contingência. Ele não é requisito
para começar os testes com ESP32 + AD2.

### Pontos de medição

Desligar as placas antes de mudar jumpers. Conectar o GND do AD2 ao GND comum
da bancada primeiro e somente depois conectar os sinais.

| Plataforma | RX da FPGA | TX da FPGA | CH1 recomendado | CH2 recomendado |
| --- | --- | --- | --- | --- |
| DE10-Lite | JP1 físico 1 / `V10` | JP1 físico 2 / `W10` | `V10` | `W10` |
| Cyclone IV | J3 `PIN_103` | J3 `PIN_100` | `PIN_103` | `PIN_100` |

Para os canais analógicos do AD2:

- ligar `1+` ao RX e `1-` ao GND;
- ligar `2+` ao TX e `2-` ao GND;
- com o adaptador BNC, usar o centro do BNC como sinal e a blindagem como
  referência;
- não ligar `W1` ou `W2` aos sinais UART;
- não ligar as fontes `V+`/`V-` do AD2 às placas;
- cada FPGA, GPS e ESP32 deve permanecer alimentado por sua própria fonte;
- não conectar diretamente sinais RS-232 ou sinais de 5 V aos GPIOs de 3,3 V.

As entradas digitais do AD2 podem ser usadas no Logic Analyzer/Protocol para
uma leitura UART. Nesse caso, ligar um DIO ao TX observado e o GND comum. A
captura digital serve para bytes e temporização lógica; a captura analógica é a
referência para níveis, overshoot e undershoot.

### Configuração recomendada

Para todos os ensaios deste artigo:

```text
UART:       9600 baud, 8N1, idle alto
Analógico:  DC, entrada de alta impedância, faixa compatível com 0–3,3 V
Trigger:    borda de descida no RX, aproximadamente 1,65 V
CH1:        RX da FPGA
CH2:        TX da FPGA
```

Para capturar o quadro e medir o timing, usar inicialmente pelo menos 10 MS/s e
uma janela de 10–20 ms. Para avaliar as bordas, usar uma taxa maior disponível,
com pontas/cabos curtos e referência de terra curta. O AD2 possui dois canais
analógicos, resolução de 14 bits e taxa nominal de até 100 MS/s; a largura de
banda anunciada de 30 MHz ou mais depende do adaptador BNC e das pontas usadas.
Para esta UART de 9600 baud, a taxa é suficiente para o quadro completo, mas
não deve ser apresentada como equivalente a um osciloscópio de bancada de alta
largura de banda em medições de integridade de sinal.

No Protocol Analyzer/Logic, selecionar UART, 9600, oito bits, sem paridade, um
stop bit e linha ociosa alta. Confirmar o número do DIO e a direção antes de
iniciar a captura.

## Aplicação aos testes P03–P06

### P03 — baseline no PC

1. Programar o SOF baseline e confirmar o cabo JTAG correto.
2. Preparar o monitor ESP32 e deixar o AD2 armado.
3. Enviar quatro vezes `55 A5 00 FF 3C` pelo caminho externo.
4. Verificar no ESP32 o eco exato e todos os contadores de erro em zero.
5. Usar o AD2 para confirmar que RX e TX possuem quadros completos em 8N1.

O critério de bytes continua sendo o log/verificador do host; o AD2 fornece a
evidência elétrica associada ao mesmo ensaio.

### P04 — baseline no instrumento

Registrar pelo menos duas capturas com RX e TX simultâneos:

- níveis baixo e alto;
- aproximadamente `104,17 µs` por bit;
- aproximadamente `1,0417 ms` por byte 8N1;
- cinco bytes em aproximadamente `5,208 ms`;
- início do start bit no RX e no TX;
- latência RX→TX medida diretamente na forma de onda;
- ausência de quadro truncado.

Salvar CSV bruto e imagem com escalas, canais, trigger e configurações visíveis.
Não usar `host_window_us` do ESP32 como latência física.

### P05 — secure e AES-CTR

1. Desconectar o TX da fonte durante a troca do bitstream.
2. Programar o SOF secure e registrar seu SHA-256.
3. Carregar o contexto definido para o ensaio.
4. Armar o AD2 antes de reconectar o TX da fonte.
5. Capturar o ciphertext no TX da FPGA.
6. Verificar os bytes independentemente no PC, usando o contexto registrado.

O AD2 não decifra o AES. Ele pode mostrar e decodificar os bytes cifrados; a
aprovação P05 exige a recuperação independente do plaintext pelo verificador.

### P06 — secure no instrumento

Repetir o P04 no SOF secure e comparar com o baseline:

- bit time e níveis;
- tamanho do quadro;
- RX→TX físico;
- ausência de framing/overflow;
- diferença de latência atribuível ao caminho AES-CTR, sempre medida na forma
  de onda e não inferida apenas dos timestamps do host.

## GPS e ensaios P07–P11

Para o GPS, primeiro capturar o TX do NEO-M8N diretamente no receptor serial e
guardar uma referência bruta. Depois observar simultaneamente a entrada e a
saída da FPGA com o AD2.

O AD2 pode ser usado para confirmar:

- UART do GPS em 9600/8N1;
- nível lógico compatível;
- presença das sentenças NMEA;
- perda, truncamento ou framing na entrada;
- transmissão correspondente no TX da FPGA.

Ele não confirma por si só checksum NMEA, posição válida, origem física do
arquivo ou decifragem do secure. Esses critérios continuam nos validadores e
nos logs do PC. Coordenadas e capturas brutas do GPS devem permanecer em
`data/private/` quando puderem revelar localização.

## Evidências e nomenclatura

Guardar dados privados fora do Git, por exemplo:

```text
data/private/2026-09-22/ad2/
├── de10_baseline_p04_rx-tx.csv
├── de10_baseline_p04_scope.png
├── cyclone4_baseline_p04_rx-tx.csv
├── de10_secure_p06_rx-tx.csv
├── de10_secure_p06_scope.png
└── README.txt
```

O `README.txt` de cada ensaio deve registrar:

| Campo | Exemplo |
| --- | --- |
| Data/hora | ISO 8601 com fuso |
| Commit | `git rev-parse HEAD` |
| Placa e variante | DE10-Lite baseline/secure |
| SOF | caminho e SHA-256 |
| AD2 | número de série, quando disponível |
| WaveForms | versão |
| Canal/ponto | CH1 RX, CH2 TX |
| Taxa/faixa | 10 MS/s, faixa 5 V |
| Trigger | CH1 falling, 1,65 V |
| Ponteira/cabo | atenuação e adaptação usada |
| GND | ponto comum utilizado |
| Resultado | aprovado/reprovado/bloqueado e motivo |

Após salvar cada arquivo:

```bash
sha256sum data/private/2026-09-22/ad2/*
```

O hash deve ser copiado para o registro do ensaio. Captura visual sem arquivo
bruto ou sem condições do instrumento não é evidência suficiente para métricas
reprodutíveis.

## Limites de interpretação

- `lsusb`, `dwfcmd enumerate` e a abertura do WaveForms validam a instalação e
  a conexão do AD2, não o sinal da FPGA.
- CSV do Scope contém amostras de tensão; bytes exigem decodificação UART.
- Bytes decodificados pelo AD2 não substituem o retorno verificado pelo ESP32 ou
  CP2102.
- P04/P06 só podem ser marcados como concluídos com captura física registrada.
- Um replay NMEA no testbench não é equivalente à captura de um GPS real.
- A forma de onda não comprova autenticação, integridade criptográfica ou
  validade da posição GPS.
- Qualquer anomalia de amplitude deve ser repetida com terra curto, faixa e
  atenuação conferidas antes de alterar o RTL ou a força de saída.

## Checklist rápido para o próximo usuário

```bash
cd /home/leofernandesc/gps-uart-aes-fpga
git status --short --branch
git fetch --prune origin
git log --oneline HEAD..origin/main
dpkg-query -W -f='${binary:Package}\t${Version}\t${Status}\n' \
  digilent.adept.runtime digilent.waveforms
dwfcmd enumerate
```

Depois:

1. ler este documento e o roteiro específico da placa;
2. conferir JTAG, SOF, pinagem e GND;
3. conectar o AD2 primeiro ao GND e depois aos sinais;
4. configurar 9600/8N1 e armar a captura;
5. executar o teste do host;
6. salvar CSV, imagem, log, hash e condições;
7. atualizar `docs/cronograma.md` somente com a evidência produzida;
8. nunca transformar a instalação, uma simulação ou uma captura isolada em
   teste P03–P11 concluído.
