# Execução até a submissão — setembro de 2026

Objetivo: GPS M8 real → UART RX → FIFO → AES-128-CTR → UART TX → PC.
Congelar código e resultados em 28/09; submeter preferencialmente em 29/09 e
reservar 30/09 para contingência. O prazo do evento deve ser confirmado no portal:
a proposta registrou informações divergentes entre páginas públicas do BTSym.

## Etapas e critérios

| Data | Entrega | Critério de conclusão | Situação em 07/09 |
| --- | --- | --- | --- |
| 07–08 | UART revisado e referência preservada | Testes independentes, reset/erros e checagem estrutural passando | Parte RTL concluída; ver relatório |
| 08–09 | Ambiente de bancada | Quartus com suporte MAX 10, USB-Blaster reconhecido, adaptadores e níveis verificados | Pendente no laboratório |
| 08–11 | AES-128 isolado | RTL próprio, vetores NIST e comparação com biblioteca independente | Próxima implementação |
| 10–11 | Baseline física sem AES | GPS recebido e retransmitido com FIFO, sem perda não detectada | Pendente |
| 12–14 | CTR, FIFO e sessões | Fluxo de bytes, backpressure interno, limites e reset verificados | Pendente |
| 15–17 | Demonstração ponta a ponta | Captura real cifrada e recuperação idêntica à referência no PC | Pendente |
| 18–20 | Estabilização | Testes de longa duração, diagnóstico e builds comparáveis | Pendente |
| 21–24 | Experimentos | Replays repetidos e sessões GPS reais nos dois builds | Pendente |
| 25–27 | Análise e artigo | Tabelas/figuras rastreáveis e revisão com orientador | Pendente |
| 28 | Congelamento | Código, dados, scripts e figuras identificados por versão | Pendente |
| 29–30 | Submissão | Revisão final, portal, arquivos e comprovante | Pendente |

As janelas se sobrepõem porque bancada, escrita e RTL podem avançar em paralelo;
não significam execução simultânea por uma única pessoa. A verificação física
depende de acesso ao computador Windows e aos materiais do laboratório.

## Próxima implementação: AES isolado

1. Fechar ordem de bytes conforme os exemplos NIST e interface de chave/bloco.
2. Implementar S-box e transformações de rodada, testadas individualmente.
3. Expandir e armazenar as onze chaves de rodada uma vez por sessão.
4. Implementar datapath de 128 bits reutilizado, com dois estágios temporais por
   rodada. Medir a latência real; não tratar os 20 ciclos planejados como resultado.
5. Comparar AES com os vetores oficiais e blocos pseudoaleatórios reprodutíveis.
6. Só depois acrescentar CTR e sua integração por byte.

Referências de implementação:
[FIPS 197 — AES](https://csrc.nist.gov/pubs/fips/197/final) e
[SP 800-38A — modos de operação](https://csrc.nist.gov/pubs/sp/800/38/a/final).

## Contrato de sistema a implementar

- FIFO síncrona de 1.024 bytes na entrada; high-water mark e overflow explícitos.
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
- Confirmar modelo do carrier M8, níveis lógicos e alimentação antes de energizar.
- Não acrescentar parser NMEA em RTL: o FPGA transportará bytes opacos.
- Não acrescentar ASIC, rede neural, segunda FPGA ou uma segunda arquitetura AES.
- Se o AES isolado não estiver validado até 11/09, revisar o cronograma com o
  orientador antes de expandir escopo. A base UART e os testes continuam úteis.
