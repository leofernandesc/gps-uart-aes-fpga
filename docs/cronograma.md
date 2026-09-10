# Execução e submissão até 25/09 — setembro de 2026

Objetivo: GPS M8 real → UART RX → FIFO → AES-128-CTR → UART TX → PC.
Encerrar a execução técnica, o manuscrito, a submissão e a contingência em
25/09. A meta é enviar a versão principal em 24/09 e usar 25/09 somente para
correções finais, problema do portal ou reenvio. Os dias 26–30/09 ficam como
folga externa, não como parte necessária do cronograma. O prazo do evento deve
ser confirmado no portal: a proposta registrou informações divergentes entre
páginas públicas do BTSym.

## Etapas e critérios

| Data | Entrega | Critério de conclusão | Situação em 09/09 |
| --- | --- | --- | --- |
| 07–08 | UART revisado e referência preservada | Testes independentes, reset/erros e checagem estrutural passando | Parte RTL concluída; ver relatório |
| 08–09 | AES-128 isolado | RTL próprio, vetores NIST e comparação com biblioteca independente | Concluído: regressão e Quartus isolado passando em 09/09 |
| 09–10 | CTR isolado | Nonce/contador, vetores oficiais e casos-limite passando | Próxima implementação |
| 11–12 | Adaptador por byte | Máscaras, pausas, backpressure, reset e comprimentos parciais verificados | Pendente |
| 13 | Integração simulada | Replay NMEA → UART → FIFO → CTR → UART → decifragem no PC | Ponto de controle |
| 14–15 | Sessões e software do PC | Armamento, nonce, captura, decifragem e comparação byte a byte | Pendente |
| 16 | Build integrado | Baseline sem AES e build com CTR compilados no Quartus | Pendente |
| 17–18 | Validação física ou replay | Se a placa chegar: GPS real e demo; caso contrário, replay documentado | Pendente |
| 19–20 | Experimentos e métricas | Três replays por build e, se possível, sessão GPS contínua | Pendente |
| 21–22 | Resultados e manuscrito | Tabelas, figuras, Results, Discussion, Conclusion e Abstract | Pendente |
| 23 | Revisão orientada | Manuscrito completo, referências e comentários do orientador | Pendente |
| 24 | Submissão principal | Versão final enviada e comprovante armazenado | Pendente |
| **25** | **Contingência e encerramento** | **Correção pequena, reenvio se necessário e confirmação final da submissão** | **Meta final** |

As janelas se sobrepõem porque bancada, escrita e RTL podem avançar em paralelo;
não significam execução simultânea por uma única pessoa. O Quartus Linux já
permite compilar sem a placa. A verificação física depende da chegada da
DE10-Lite e da conferência dos materiais do laboratório; não é necessário
aguardar isso para implementar e simular o CTR e suas interfaces.

## Marco antecipado em 07/09: preparação sem placa

- UART v2 revalidado, preservando suas fontes.
- FIFO de 1.024 bytes e ponte serial sem cifra implementadas; leitura síncrona,
  ocupação máxima, indicação persistente de overflow e erro de stop.
- Testes independentes de FIFO e retransmissão, inclusive 50 MHz/9600 baud.
- Projeto Quartus, pinagem do lado FPGA e restrições temporais definidos.
- `.sof` gerado; análise de setup, hold, recovery e removal nos três cantos.

Evidências em [validação da ponte](validacao-ponte-quartus-2026-09-07.md).
Isso antecipa a preparação da baseline física; não conclui sua validação de
bancada. O núcleo AES previsto para 08–11/09 foi implementado no marco seguinte.

## Marco em 08–09/09: AES isolado

1. Ordem de bytes e interface de chave/bloco documentadas em [AES](aes128.md).
2. S-box, ShiftRows, MixColumns e expansão testados separadamente.
3. Onze chaves de rodada armazenadas; preparação medida em 10 ciclos.
4. Datapath de 128 bits reutilizado, duas fases por rodada: 20 ciclos por bloco,
   intervalo mínimo de iniciação de 21 ciclos, ambos conferidos pelo testbench.
5. 866 vetores de comparação independente, incluindo 284 NIST CAVP.
6. Projeto Quartus separado para recursos e timing interno; não é o sistema GPS.

Validação final em 09/09: 18 simulações passando, lint e estrutura aprovados;
6.482 LEs, 1.813 registradores e menor Fmax interna de 77,91 MHz. Setup, hold,
recovery e removal internos positivos nos três modelos. Ver [relatório](validacao-aes-2026-09-09.md)
para as fronteiras excluídas, ferramentas e reprodução.

## Plano operacional até 25/09

1. **09–10/09 — CTR:** usar `nonce[95:0] || counter[31:0]`, fixar a ordem dos
   bytes, comparar com biblioteca independente e cobrir vetores CTR oficiais,
   contador final e tentativa de ultrapassagem.
2. **11–12/09 — fluxo por byte:** implementar duas reservas de máscara de 16 bytes,
   respeitar backpressure e testar pausas, reset, nova chave e comprimentos 1, 15,
   16, 17 e longos. Nenhuma máscara pode ser consumida sem aceite do próximo estágio.
3. **13–15/09 — sessões e PC:** definir armamento, nonce por sessão, limite de
   bytes, invalidação por erro/reset e formato de controle separado do ciphertext.
   O PC deve configurar, capturar e decifrar por biblioteca externa.
4. **16–18/09 — integração e validação:** gerar os builds comparáveis com e sem
   CTR, repetir fit/timing com as conexões efetivas e testar GPS real se a placa
   estiver disponível. Sem placa, usar replay controlado e declarar a limitação.
5. **19–20/09 — experimentos:** executar três repetições por build, guardar
   contagens, comparação byte a byte, latência, throughput, ocupação da FIFO,
   erros e condições de teste. Captura GPS real será uma evidência adicional,
   não substituída silenciosamente por dados sintéticos.
6. **21–23/09 — artigo:** fechar tabelas e gráficos, revisar a argumentação e
   incorporar comentários do orientador. A introdução, trabalhos relacionados e
   metodologia devem ser escritos em paralelo desde o início.
7. **24–25/09 — envio:** enviar a versão principal em 24/09; no dia 25/09,
   resolver somente problemas finais, conferir arquivos e fazer reenvio se o
   portal exigir. Depois do dia 25, o projeto é considerado encerrado.

Assim a ausência da placa não paralisa RTL, testes nem preparação dos scripts.
Captura GPS real, programação e medições físicas permanecem condicionadas à
chegada da placa; a submissão não dependerá dos últimos dias do prazo externo.

Referências de implementação:
[FIPS 197 — AES](https://csrc.nist.gov/pubs/fips/197/final) e
[SP 800-38A — modos de operação](https://csrc.nist.gov/pubs/sp/800/38/a/final).

## Contrato de sistema a implementar

- FIFO síncrona de 1.024 bytes na entrada; high-water mark e overflow explícitos
  já implementados na ponte, a conectar ao futuro controle de sessões.
- AES-CTR com nonce de 96 bits e contador de 32 bits; codificação dos blocos
  documentada e testada antes de conectar os bytes da UART.
- Duas reservas de máscara de 16 bytes; consumir máscara só quando o byte for
  efetivamente aceito no próximo estágio. Não esperar 16 bytes de GPS para cifrar.
- Sessões limitadas a N bytes, configuradas pelo PC antes da captura; aquisição
  começa no próximo `$` após o armamento. Controle não se mistura ao ciphertext.
- Nonce novo para cada sessão com a mesma chave, inclusive após reset; impedir
  wrap do contador. O PC manterá o histórico de nonces usados por chave.
- Chaves de teste provisionadas localmente; não enviar segredos pela saída de
  dados nem versionar chaves/sessões privadas. Canal de configuração é de bancada
  confiável, não um protocolo de distribuição segura de chaves.
- Stop inválido, perda de byte ou reset invalidam a sessão: não tentar ocultar
  dessincronização CTR com bytes de preenchimento.
- PC captura em paralelo a saída crua do GPS para comparação exata com o texto
  recuperado. CSV de métricas e hashes identificam cada ensaio.

## Avaliação e escrita

O comparador é **UART v2 + FIFO + controle** versus **o mesmo sistema + AES-CTR**.
AES deve ser removido por elaboração no build baseline, não apenas desligado em
tempo de execução. Restrições, dados de entrada e fronteiras de medição iguais.

Medir recursos pós-fit, timing a 50 MHz/Fmax, preparação da chave, latência e
intervalo de iniciação do AES, latência de hardware por byte, ocupação da FIFO e
erros/perdas. Latência no PC inclui USB/SO e não substitui medição de hardware.
Potência é opcional e apenas como estimativa com atividade, identificada como tal.

Planejar três repetições de um mesmo replay em cada build, preservando os intervalos
e rajadas da captura, e uma sessão GPS real de uma hora por build. Guardar contagens,
comparação byte a byte e condições de teste. Não transformar dados sintéticos em
evidência de recepção real. Builds com SignalTap devem ser separados das medições
oficiais de utilização de recursos.

Introdução, trabalhos relacionados e metodologia devem avançar durante a
implementação. FPGA + AES já existem na literatura: a contribuição pretendida é
a avaliação experimental reprodutível desta integração, não uma cifra nova.

## Controle de escopo e riscos

- GPS é o objetivo principal. Uma falha física deve ser explicitada e discutida
  antes de trocar a aplicação por replay/PC; não declarar GPS real sem aquisição.
- Módulo informado em 08/09: NEO-M8N-010. Conferir conector da placa de suporte,
  níveis lógicos e alimentação antes de energizar; a identificação do receptor
  não determina a ordem dos pinos de uma placa de terceiros.
- Não acrescentar parser NMEA em RTL: o FPGA transportará bytes opacos.
- Não acrescentar ASIC, rede neural, segunda FPGA ou uma segunda arquitetura AES.
- AES isolado validado antes de 11/09. O próximo ponto de controle é 14/09:
  CTR/sessões simulados ponta a ponta. Se houver atraso, revisar as janelas de
  bancada com o orientador sem acrescentar funcionalidades.
