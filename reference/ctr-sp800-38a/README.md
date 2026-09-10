# Vetores AES-128-CTR

`aes128.json` transcreve a chave, o contador inicial e os quatro blocos das
seções F.5.1/F.5.2 da [NIST SP 800-38A](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38a.pdf).
São dados públicos de teste, nunca chaves para uso real.

O gerador `scripts/ctr_vectors.py` confere os ciphertexts publicados com
`cryptography`/OpenSSL antes de produzir os vetores RTL. Os demais casos são
sintéticos e identificados separadamente em `build/ctr/oracle.json`.

O projeto incrementa somente os 32 bits inferiores e bloqueia ao esgotá-los.
O exemplo publicado não atravessa esse limite; os testes sintéticos cobrem
essa restrição específica do projeto. A execução dos vetores não constitui
certificação NIST/CAVP/FIPS.
