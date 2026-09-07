# Referência preservada — UART v1

Origem: `/home/leofernandesc/uniccass-icdesign-tools/shared_xserver/projects/uart`.
Captura: 07/09/2026. Os nove arquivos listados em `SHA256SUMS` são cópias exatas.

Não editar esta referência para corrigir o controlador. O desenvolvimento novo
fica em `../../rtl/uart/`. O original permanece em seu próprio diretório.

Conferência, a partir deste diretório:

```bash
sha256sum -c SHA256SUMS
```

Os testes históricos passam, mas não cobrem fase serial independente. O teste
integrado alinha `tx_start` ao contador interno de baud, mascarando a duração
variável do start bit. A nova regressão reproduz esse defeito do TX de propósito;
o resultado esperado é demonstrar a falha antiga e a correção nova.

Para compilar ambas as versões, o executor renomeia somente o módulo de uma
cópia **gerada em `build/`**. Nenhuma fonte preservada é reescrita.

O `config.yaml` é histórico: 100 MHz e fluxo ASIC. Não é configuração do novo
experimento, cujo clock é 50 MHz e cuja plataforma é exclusivamente FPGA.
