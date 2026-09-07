# Primeira sessão de bancada

Esta etapa ainda não foi executada. A validação atual é exclusivamente de RTL.
O modelo exato da placa GPS será confirmado pelo usuário; a marcação VCC=3,3 V
foi informada, mas não substitui a conferência de pinagem e alimentação do carrier.

## Materiais

| Material | Uso | Verificação antes de ligar |
| --- | --- | --- |
| DE10-Lite + cabo USB | FPGA e programação USB-Blaster | Placa enumerada e identificada no Quartus |
| GPS u-blox M8 + antena correspondente | Fonte real dos dados | Modelo exato, pinagem, VCC e tensão da saída UART |
| Dois adaptadores USB–UART | Saída FPGA e referência crua/configuração | Confirmar **nível lógico de I/O 3,3 V**, não apenas pino VCC selecionável |
| Jumpers e conexões firmes | Sinais e terra comum | Continuidade, identificação dos pinos e ausência de curto |
| Multímetro; fonte 3,3 V regulada com limite de corrente | Conferência inicial | Um único suprimento para cada dispositivo; não unir fontes |
| PC Windows com Quartus e suporte MAX 10 | Compilação e programação | Instalação, pacote do dispositivo e driver USB-Blaster |
| Analisador lógico/osciloscópio, se disponível | Diagnóstico de sinais/latência | Entradas compatíveis com os níveis da montagem |

USB-Blaster não fornece uma porta serial de dados para o experimento. Os
adaptadores USB–UART são componentes separados. Não usar RS-232 de tensões
positivas/negativas, UART de 5 V ou alimentação direta de bateria no GPIO/GPS.

## Ordem de execução

1. **Sem conectar o GPS:** abrir o Quartus, conferir dispositivo da DE10-Lite e
   detecção do USB-Blaster no Programmer. Guardar versão do Quartus e captura da
   identificação. Não é necessário apagar ou sobrescrever memória não volátil.
2. Identificar os dois adaptadores e suas portas COM, verificar datasheet/níveis
   reais de TX/RX e executar loopback de cada adaptador no PC, em 9600 8N1.
3. Confirmar modelo/pinagem do carrier M8 e sua alimentação. Com terra comum e
   conexão adequada, capturar o GPS diretamente no PC antes de envolver a FPGA.
4. Guardar alguns minutos de bytes crus e confirmar presença de sentenças NMEA.
   A aquisição pode funcionar sem fix válido; registrar separadamente aquisição
   serial e obtenção de posição. Proteger coordenadas pessoais nos dados públicos.
5. Com esses itens verificados, finalizar wrapper/pinagem/SDC e compilar a baseline
   com FIFO no Quartus; conferir timing e sincronizadores antes da programação.
6. Fazer GPS → FPGA → PC sem AES e comparar com a captura direta antes de integrar
   criptografia. Overflow e erro de stop precisam ser observáveis.

**Primeiro ponto de validação:** Quartus reconhecendo a DE10-Lite via USB-Blaster.
Confirmado isso, seguir para os adaptadores e a captura direta. Não energizar um
carrier sem confirmar seu modelo/pinagem apenas para cumprir o cronograma.

## Ligações lógicas previstas para o sistema completo

```text
GPS TX ────────────┬──> FPGA / GPS RX
                   └──> adaptador B / RX (referência crua no PC)

FPGA / UART TX ────────> adaptador A / RX (dados para o PC)
adaptador B / TX ──────> FPGA / UART RX (configuração local de sessão)
terras compatíveis ────> GND comum
```

São conexões lógicas, **não** uma autorização de pinagem elétrica. Os números dos
pinos do carrier e o arquivo QSF só serão fechados após conferência do hardware.
Não ligar a saída TX de um adaptador ao TX do GPS. Manter TX não utilizado do
adaptador A e RX do GPS desconectados nesta configuração, salvo necessidade
explicitamente verificada. Não alimentar o GPS simultaneamente pela placa,
adaptador e fonte de bancada.

O UART revisado isolado não inclui FIFO nem ponte GPS–PC. Por isso, este marco
não entrega um `.sof` pronto para essa demonstração física.
