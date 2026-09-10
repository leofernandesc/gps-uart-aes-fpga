# Vetores públicos NIST AESAVS

Quatro arquivos originais, sem alterações, extraídos em 08/09/2026 de
[KAT_AES.zip](https://csrc.nist.gov/CSRC/media/Projects/Cryptographic-Algorithm-Validation-Program/documents/aes/KAT_AES.zip),
publicado na [página CAVP do NIST](https://csrc.nist.gov/projects/cryptographic-algorithm-validation-program/block-ciphers).
SHA-256 do ZIP: `a203b16c9246b2ebae31dee5de21a606be80cf78ceabaca37150236fa098eb60`.

O teste usa somente as seções ENCRYPT de AES-128: GFSbox (7), KeySbox (21),
VarKey (128) e VarTxt (128), totalizando 284 casos. Os arquivos contêm também
DECRYPT, que não é implementado pelo núcleo forward usado futuramente em CTR.
O uso de ECB nesses vetores verifica a primitiva de um bloco; o transporte GPS
planejado continua sendo CTR. Não são chaves nem capturas privadas.

Executar estes vetores não equivale à certificação CAVP/FIPS. Os checksums locais
permitem verificar a integridade da cópia sem depender de downloads nos testes.
