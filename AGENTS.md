# Orientações para continuidade do projeto

Este repositório é colaborativo. Qualquer IA ou colaborador que retomar o
projeto deve tratar `docs/cronograma.md` como um documento vivo: ele registra o
que já foi executado, o que está em andamento e qual é o próximo passo.

## Antes de iniciar uma tarefa

1. Verifique o estado local e os últimos commits:

   ```bash
   git status --short --branch
   git log --oneline -5
   ```

2. Leia `README.md`, `docs/cronograma.md` e
   `docs/PLANO_DE_EXECUCAO.md` antes de alterar o projeto.
3. Compare as tarefas previstas com as evidências existentes em testes,
   relatórios, commits e resultados de bancada. Uma tarefa não deve ser marcada
   como concluída apenas porque estava prevista no planejamento.
4. Preserve alterações locais e de outros colaboradores. Não descarte, reverta
   ou sobrescreva mudanças sem entender sua origem.

## Regra obrigatória do cronograma

Depois de cada etapa relevante — implementação, correção, simulação, execução
do Quartus, resultado de bancada, decisão técnica ou revisão do artigo — atualize
`docs/cronograma.md` na mesma entrega ou imediatamente antes do commit.

Ao atualizar o cronograma:

- registre a situação real (`Concluído`, `Em andamento`, `Pendente` ou
  `Bloqueado`), usando a data efetiva e não a data planejada;
- indique a evidência correspondente, como comando executado, commit, relatório
  ou teste realizado;
- registre o próximo passo e o responsável quando isso estiver definido;
- se uma etapa atrasar, ajuste datas, dependências e justificativa para não
  deixar o planejamento contraditório;
- não apague marcos anteriores nem transforme simulação ou síntese em resultado
  de placa; programação da DE10-Lite e captura de GPS só podem ser marcadas
  após evidência física;
- mantenha as datas de submissão e contingência consistentes com o cronograma.

`docs/cronograma.md` é a fonte de verdade do andamento. O README e o plano
detalhado podem resumir ou explicar o trabalho, mas não devem manter datas ou
status diferentes. Se uma mudança afetar esses documentos, atualize todos na
mesma alteração. Inclua também `docs/proposta_btsym_gps_fpga.html` quando houver
mudança de arquitetura, datas ou materiais. Esse é o HTML versionado; neste
computador, mantenha a cópia de apresentação em
`/home/leofernandesc/Documents/proposta_btsym_gps_fpga.html` igual ao arquivo
versionado quando ela existir.

## Alvos de FPGA e testes

- O experimento ativo usa somente a DE10-Lite MAX 10 `10M50DAF484C7G`, clock
  de 50 MHz e GPS identificado no projeto como u-blox NEO-M8N a 38400/8N1.
  Cyclone IV está fora do escopo atual; os registros anteriores são históricos.
- `make uart-fpga` é o teste autônomo de UART; `make fpga` é a ponte com FIFO.
  Nenhum dos dois representa o sistema integrado com AES-CTR.
- O comparativo tem dois builds: baseline e secure na DE10-Lite, ambos a
  50 MHz/38400/8N1. Mantenha clock, FIFO, interfaces e instrumentação iguais;
  o AES é a única diferença arquitetural. O teste GPS deve ligar diretamente
  o NEO-M8N à FPGA, sem etapa intermediária com outro microcontrolador.
- O breakout do GPS está sendo usado a 3,3 V. Verificar os níveis e o GND comum
  antes da conexão com a FPGA; manter os pinos de sinal dentro da faixa de I/O.
- A instalação e o uso do Analog Discovery 2 estão documentados em
  `docs/analog-discovery-2-waveforms.md`. WaveForms/Adept instalados ou uma
  enumeração USB bem-sucedida não equivalem a P04/P06 concluídos: preserve CSV,
  imagens, logs, hash e condições do instrumento antes de atualizar o status.

## Procedimento obrigatório ao atualizar o repositório

As tabelas e resumos pós-fit do artigo devem corresponder à seleção versionada
em `docs/evidence/de10-lite-postfit-2026-09-30.json`. `make metrics` confere
fontes e artefatos dos builds locais; `make manuscript-check` compara essa
seleção com os manuscritos e, quando presentes, com os builds. Um build novo
não atualiza automaticamente o artigo: selecionar um par revisado em um
arquivo novo, atualizar os documentos e conferir todos os hashes. Preservar
seleções anteriores como histórico. Não publicar pacotes de contexto, chaves
ou capturas GPS privadas.

`make timing-review` gera uma auditoria complementar e refits isolados em um
diretório novo de `build/timing-review/`. Os perfis com sincronizadores
explícitos não são os SOFs testados fisicamente nem atualizam o par do artigo.
Não programar seus SOFs para aquisição secure: reutilizam as entradas de
elaboração somente para análise e podem conter contexto já consumido. Uma
promoção para bancada exige nonce/contexto novo e revalidação correspondente.

Sempre que for necessário fazer `git pull`, revise cautelosamente todas as
alterações recebidas. Não faça um pull cego.

Antes do pull:

```bash
git status --short --branch
git diff --check
previous_head=$(git rev-parse HEAD)
git fetch origin
git log --oneline --decorate HEAD..origin/main
```

Se o estado local estiver sujo, preserve e compreenda as alterações antes de
continuar. Prefira atualizar sem criar merge automático:

```bash
git pull --ff-only origin main
```

Depois do pull, examine todo o intervalo recebido, arquivo por arquivo:

```bash
git log --oneline --reverse "$previous_head"..HEAD
git diff --stat "$previous_head"..HEAD
git diff --name-status "$previous_head"..HEAD
git diff "$previous_head"..HEAD
git status --short --branch
```

A revisão deve incluir RTL, testbenches, scripts, configuração do Quartus,
documentação, cronograma e qualquer arquivo removido ou renomeado. Em seguida,
execute `git diff --check` e os testes afetados; para mudanças no RTL, execute
ao menos `make check` quando as ferramentas estiverem disponíveis. Se houver
conflito, divergência de datas ou uma alteração cujo propósito não esteja
claro, não aceite versões automaticamente: preserve o trabalho, registre o
problema e resolva-o antes de implementar a próxima etapa.

## Ao concluir a tarefa

Confira o diff completo, confirme que o cronograma reflete o estado real e
registre no commit o que foi alterado e qual é o próximo passo. Antes de
informar a conclusão, verifique novamente `git status`, os testes relevantes e,
quando houver publicação, se o commit local e `origin/main` estão alinhados.
