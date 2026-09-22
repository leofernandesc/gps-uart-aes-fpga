# Primeira bancada

O primeiro ensaio previsto para 15/09 é a
[UART isolada com osciloscópio e jumper](../fpga/de10_lite/uart_scope/README.md):
`make uart-fpga`, padrão 0x55 a cada 100 ms. Esse teste não precisa de USB–UART.
O roteiro abaixo trata da etapa seguinte, com GPS e captura no PC.

Esta etapa física ainda não foi executada. A ponte sem cifra já foi simulada e
compilada no Quartus Linux, com `.sof` e relatórios pós-fit disponíveis.
O módulo utilizado é o **NEO-M8N-010**, com alimentação indicada de 3,3 V.
Ainda será conferida a pinagem da placa de suporte (carrier), que não é
determinada pelo código impresso no receptor u-blox.

## Materiais

| Material | Uso | Verificação antes de ligar |
| --- | --- | --- |
| DE10-Lite + cabo USB | FPGA e programação USB-Blaster | Placa enumerada e identificada no Quartus |
| GPS NEO-M8N-010 + antena correspondente, disponíveis | Fonte real dos dados | Conector do carrier, VCC e tensão da saída UART |
| Um adaptador USB–TTL (CP2102 ou equivalente) | Fonte/receptor serial e captura no PC | Confirmar **nível lógico de I/O 3,3 V**, não apenas pino VCC selecionável |
| Osciloscópio e pontas | Níveis e duração dos bits; teste UART isolado | Terra em GND, fator da ponta correto e instrumento acessível na bancada |
| Analog Discovery 2 + WaveForms, opcional | Captura CSV, decodificação UART e medidas repetíveis de RX/TX | WaveForms instalado; AD2 físico deve ser enumerado antes do P04/P06 |
| Jumpers e conexões firmes, disponíveis | Sinais e terra comum | Continuidade, identificação dos pinos e ausência de curto |
| Multímetro; fonte 3,3 V regulada com limite de corrente | Conferência inicial | Um único suprimento para cada dispositivo; não unir fontes |
| PC com Quartus e suporte MAX 10 | Compilação e programação | Quartus Linux já compila; USB-Blaster e permissões/driver dependem da placa |
| Analisador lógico/osciloscópio, se disponível | Diagnóstico de sinais/latência | Entradas compatíveis com os níveis da montagem |

USB-Blaster não fornece uma porta serial de dados para o experimento. O projeto
usa um único adaptador USB–TTL full-duplex conectado ao PC: ele transmite
vetores/replays e recebe a saída da FPGA. O adaptador deve preservar bytes
binários, ordem e 9600/8N1, sem conversão de texto ou perdas. Não usar RS-232 de tensões
positivas/negativas, UART de 5 V ou alimentação direta de bateria no GPIO/GPS.

O Analog Discovery 2 pode substituir o osciloscópio de bancada para as medidas
de timing e captura, desde que o GND seja comum e o dispositivo seja
enumerado pelo WaveForms. Ele não substitui a fonte/receptor serial nem a
verificação independente do AES. O procedimento de instalação, conexões e
registro das evidências está em
[Analog Discovery 2 e WaveForms](analog-discovery-2-waveforms.md).
Um único adaptador USB–TTL basta para a bancada. Ele é usado em full-duplex nos
testes baseline/secure e, no ensaio GPS, em duas etapas: primeiro captura a
referência do GPS; depois transmite essa mesma captura para a FPGA e recebe a
saída. Dois adaptadores só seriam necessários para observar referência e saída
simultaneamente, o que não é requisito do protocolo atual.

## Ordem de execução

1. **Sem conectar o GPS:** abrir o Quartus, conferir dispositivo da DE10-Lite e
   detecção do USB-Blaster no Programmer. Guardar versão do Quartus e captura da
   identificação. Não é necessário apagar ou sobrescrever memória não volátil.
2. Identificar a porta do adaptador no PC, verificar os níveis reais de TX/RX e
   executar um loopback local em 9600 8N1 antes de conectá-lo à FPGA.
3. Conferir pinagem do carrier NEO-M8N e sua alimentação. Com terra comum e
   conexão adequada, capturar o GPS diretamente no PC pelo adaptador antes de
   envolver a FPGA.
4. Guardar alguns minutos de bytes crus e confirmar presença de sentenças NMEA.
   A aquisição pode funcionar sem fix válido; registrar separadamente aquisição
   serial e obtenção de posição. Proteger coordenadas pessoais nos dados públicos.
5. Conferir na placa a [pinagem preparada](../fpga/de10_lite/README.md). Abrir o
   projeto Quartus e usar o `.sof` da ponte sem cifra, já gerado, ou executar
   `make fpga`. Programar via JTAG e pressionar/soltar KEY0 antes de enviar dados.
6. Reproduzir a captura GPS pelo mesmo adaptador, executar GPS → FPGA → PC sem
   AES e comparar com a referência. Overflow e erro de stop precisam ser
   observáveis.

**Primeiro ponto de validação:** Quartus reconhecendo a DE10-Lite via USB-Blaster.
Confirmado isso, seguir para os canais seriais e a captura direta. Não energizar um
carrier sem confirmar seu modelo/pinagem apenas para cumprir o cronograma.

## Ligações lógicas previstas para o sistema completo

```text
CP2102 TXD ────────────> FPGA / UART RX
FPGA / UART TX ────────> CP2102 RXD
CP2102 GND ────────────> FPGA GND
```

Para a captura direta, use GPS TX → CP2102 RXD e GND; o RX do GPS não é
necessário para as mensagens periódicas. Para o replay, remova esse fio e use
CP2102 TXD → FPGA UART RX, mantendo FPGA UART TX → CP2102 RXD. Nunca una duas
saídas TX. Não alimentar o GPS simultaneamente pela placa, pelo adaptador e por
uma fonte de bancada.

A ponte atual retransmite continuamente os bytes válidos, sem AES ou comandos
do PC. Erro de stop e overflow permanecem indicados nos LEDs até reset e
invalidam a captura. O roteiro de comandos e a política de arquivos estão em
[bancada serial com um CP2102](cp2102-serial-bench.md).

## GPS utilizado

A documentação oficial do u-blox para o **NEO-M8N-0-10** está na
[nota oficial UBX-20013367](https://content.u-blox.com/sites/default/files/NEO-8Q-M8Q-M8N-M8P-M8T_PCN_%28UBX-20013367%29.pdf).

O [datasheet da família NEO-M8](https://content.u-blox.com/sites/default/files/NEO-M8-FW3_DataSheet_UBX-15031086.pdf),
seções 4.2 e 8, informa VCC de 2,7 a 3,6 V para o M8N e UART padrão 9600/8N1
com mensagens NMEA habilitadas. Portanto, a marcação 3,3 V é compatível com essa
faixa. Isso não comprova a alimentação nem a configuração persistida do exemplar:
ambas serão verificadas na bancada. Não há necessidade de alterar o RTL UART.

Para a captura, o TX do GPS alimentará a entrada RX da FPGA; o RX do GPS não é
necessário para receber as mensagens periódicas. Antena e recepção de satélites
serão verificadas separadamente da recepção de bytes. O transporte no RTL não
dependerá de latitude, longitude, talker ID específico ou interpretação de NMEA.
