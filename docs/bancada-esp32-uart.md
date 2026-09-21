# ESP32 como fonte e captura UART

O adaptador USB–UART não é obrigatório para os ensaios integrados. O ESP32
pode gerar a entrada UART e receber a saída da Cyclone IV; o cabo USB do ESP32
fica responsável apenas por exibir os resultados no PC.

A implementação recomendada usa ESP-IDF e está em
[`bench/esp32_uart_host_idf`](../bench/esp32_uart_host_idf/). O sketch Arduino
anterior permanece no repositório como alternativa, mas não é necessário para
o ensaio principal.

## Ligações

Usando um ESP32 DevKit com GPIO16/GPIO17 disponíveis:

| ESP32 | Cyclone IV | Função |
| --- | --- | --- |
| GPIO17 / TX2 | J3 `PIN_103` | entrada RX da FPGA |
| GPIO16 / RX2 | J3 `PIN_100` | saída TX da FPGA |
| GND | GND do J3 | referência comum |

Na relação física do J3 usada neste ensaio, `PIN_103` é o nono contato da
primeira fileira informada e `PIN_100` é o décimo. Confirme sempre a inscrição
do pino na placa antes de conectar; `PIN_101` é reservado para programação e
não deve ser usado como UART.

Não conectar o `5V` ou o `3V3` do ESP32 à Cyclone IV. Cada placa deve ser
alimentada separadamente; interligar apenas sinais de 3,3 V e GND.

O firmware ESP-IDF em `main/uart_host_main.c` transmite, em 9600/8N1, a sequência:

```text
55 A5 00 FF 3C
```

e imprime no USB Serial do ESP32 os bytes que retornam da FPGA. Use o monitor
do ESP-IDF a 115200 baud para visualizar o log. As instruções de instalação,
compilação e gravação estão no README do projeto.

## Baseline

1. Compilar e gravar o firmware ESP-IDF no ESP32.
2. Programar `build/cyclone4/baseline/uart_baseline.sof`.
3. Ligar GPIO17, GPIO16 e GND conforme a tabela.
4. Abrir o monitor ESP-IDF a 115200 baud.
5. Confirmar `RX: 55 A5 00 FF 3C` e cinco bytes recebidos.

O baseline deve retransmitir os mesmos bytes na mesma ordem.

## Secure

1. Programar `build/cyclone4/secure/uart_secure.sof` com o contexto do ensaio.
2. Repetir a mesma sequência e guardar o `RX` hexadecimal.
3. Recuperar o ciphertext no PC usando o contexto correspondente e comparar
   com a referência.

O secure não deve ser validado pela aparência dos bytes no terminal: a
verificação deve ser feita por comparação binária e recuperação AES-CTR.

Se o ESP32 não expuser GPIO16/GPIO17, alterar as constantes do sketch para
dois GPIOs livres do modelo disponível e manter a mesma ligação cruzada.
