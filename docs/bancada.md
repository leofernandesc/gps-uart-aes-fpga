# Bancada DE10-Lite + NEO-M8N

O ensaio físico ativo usa uma única FPGA, a DE10-Lite/MAX 10, e o receptor
u-blox **NEO-M8N** a 38400/8N1. Registros
anteriores a 9600 baud e de outras placas são históricos; consulte o [plano de testes](plano-de-testes.md) para distinguir
repetições pendentes de resultados já obtidos.

## Materiais e segurança elétrica

| Material | Uso | Verificação antes de conectar |
| --- | --- | --- |
| DE10-Lite + USB-Blaster | FPGA e programação | MAX 10 `10M50DAF484C7G`, JTAG reconhecido |
| NEO-M8N + antena | Fonte real de NMEA | Identificar carrier, pinos, tensão de entrada e nível UART |
| Adaptador USB–TTL CP2102 | Capturar GPS e transmitir/recolher ensaios | TXD/RXD em lógica 3,3 V; sem unir fontes de alimentação |
| Analog Discovery 2 ou osciloscópio | Medidas elétricas/temporais e capturas | GND comum, ponta/configuração corretas, limite de entrada respeitado |
| Jumpers, cabos e multímetro | Conexões e conferência elétrica | Identificar JP1 e testar continuidade/níveis antes de energizar |
| PC com Quartus e WaveForms | Compilar, programar, registrar e comparar | Confirmar porta serial e instrumento enumerados |

O breakout usado na bancada foi observado/alimentado em 3,3 V; a tensão de
entrada depende da placa carrier e não se deduz somente do receptor. Confirme
serigrafia e GND comum. Nunca aplique 5 V às entradas da DE10-Lite nem conecte
saídas TX entre si.

## Pinagem ativa na DE10-Lite

| Sinal | DE10-Lite | Uso |
| --- | --- | --- |
| UART RX | V10 / JP1, posição física 1 | Entrada do CP2102 TXD ou GPS TX |
| UART TX | W10 / JP1, posição física 2 | Saída para CP2102 RXD ou AD2 |
| GND | JP1, posição física 12 ou 30 | Referência comum |
| Clock | P11 | Oscilador de 50 MHz na placa |

Confirme a orientação do pino 1 no conector. O caminho full-duplex conhecido é:

```text
CP2102 TXD ──> V10 / FPGA RX
CP2102 RXD <── W10 / FPGA TX
CP2102 GND ─── GND DE10-Lite
```

O CP2102 é a fonte/receptor de bytes ligada ao PC. O Analog Discovery 2 observa
os sinais, mas não substitui o caminho serial do host nem o comparador
criptográfico.

## Ordem dos ensaios

1. **P01/P02 — UART autônoma:** programar `make uart-fpga`, observar TX W10
   (`0x55` a cada 100 ms) e depois fechar o loopback W10→V10. Em 38400 baud,
   esperar 26,04 µs por bit e 260,4 µs por quadro. Guardar captura e LEDs.
2. **P03/P04 — baseline:** programar `make baseline-fpga`, enviar o vetor
   `55 A5 00 FF 3C` pelo CP2102, receber o mesmo vetor e capturar RX/TX no AD2.
   LEDs de overflow/framing devem permanecer apagados.
3. **P05/P06 — secure:** criar contexto privado com nonce novo, compilar e
   programar o secure, enviar os mesmos bytes e verificar ciphertext e
   recuperação independente no PC. Capturar também RX/TX.
4. **P07 — NEO-M8N direto:** capturar GPS TX→CP2102 RXD a 38400/8N1 com TXD
   do adaptador desconectado; validar NMEA/CRLF/checksums com
   `scripts/gps_capture.py`. Em seguida, ligar GPS TX→V10 da FPGA, GND comum e
   W10→CP2102 RXD para validar a aquisição direta. Não unir saídas TX.
5. **P08–P10 — integração com GPS:** reproduzir a mesma captura do CP2102 para
   a DE10-Lite e comparar baseline (eco exato) e secure (decifragem exata no PC).
   Executar uma captura contínua e registrar perdas, framing, overflow e
   condições. Não apresentar o tempo do Linux/USB como latência isolada da FPGA.

Os detalhes reproduzíveis, IDs e campos de evidência estão em
[`plano-de-testes.md`](plano-de-testes.md), e os comandos host em
[`cp2102-serial-bench.md`](cp2102-serial-bench.md). Nunca reutilize contexto
AES-CTR/nonce em nova captura; gere nonce novo e reprograme o bitstream.

## Referências do módulo

- [u-blox NEO-M8 firmware 3 datasheet](https://content.u-blox.com/sites/default/files/NEO-M8-FW3_DataSheet_UBX-15031086.pdf)
- [u-blox 8/M8 receiver description and protocol specification](https://content.u-blox.com/sites/default/files/products/documents/u-blox8-M8_ReceiverDescrProtSpec_UBX-13003221.pdf)
- [Terasic DE10-Lite User Manual](https://www.mouser.com/datasheet/2/598/DE10-Lite_User_Manual-1100361.pdf)
