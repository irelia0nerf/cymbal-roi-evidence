# Integração ao repositório

**Estudo independente de Alex Bolson · FoundLab**

Este projeto é mantido como repositório independente em [cymbal-roi-evidence](https://github.com/irelia0nerf/cymbal-roi-evidence). O workflow do GitHub executa os testes; não há hooks ou workflow de deployment.

## Passos

1. Clonar o repositório e revisar `git status` antes de alterar arquivos.
2. Executar os comandos do README e a suíte de testes.
3. Revisar `git diff` antes de cada commit.
4. Não forçar a inclusão dos PDFs originais sem confirmar os direitos de redistribuição.

Exemplo após a revisão:

```bash
git add -A
git commit -m "docs: refine ROI evidence reference"
```

O workflow de CI valida o código; deployment e integração com Google Cloud continuam fora do escopo.

## Descrição sugerida de PR

Adiciona um estudo técnico de Alex Bolson (FoundLab) sobre Gemini Enterprise e o caso fictício Cymbal Labs. O pacote inclui um motor local determinístico de ROI, recibos ECDSA P-256 com compromissos HMAC, hash chain, manifestos Merkle e verificação independente reproduzível.

A integração ADK/BigQuery/RAG, KMS/HSM, identidade de produção, ancoragem imutável, trusted timestamp e implantação Google Cloud permanecem fora deste escopo. Os resultados de validação estão em `validation/`.
