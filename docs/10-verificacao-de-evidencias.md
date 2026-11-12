# Guia de verificação de evidências

**Estudo independente de Alex Bolson · FoundLab**

## O que a verificação estabelece

O fluxo combina dois mecanismos:

- **ECDSA P-256/SHA-256:** autentica o envelope contra uma chave pública confiada por fingerprint obtido fora de banda.
- **HMAC-SHA-256:** compromete a entrada e o resultado sem publicar hashes diretos de valores financeiros. A chave HMAC é necessária para a verificação autorizada.

O verificador recebe o JSON original, recalcula ROI e compara os compromissos. O recibo não leva o payload nem a saída numérica. A assinatura, isoladamente, não prova a veracidade dos dados, o horário, a identidade institucional ou a autorização do operador.

## Preparar ambiente local

Requer Python 3.10+ e a dependência fixada em `requirements.txt`:

```bash
python -m venv .venv
```

No Windows PowerShell, instale e ative o ambiente com:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\Activate.ps1
```

No macOS/Linux, use:

```bash
.venv/bin/python -m pip install -r requirements.txt
source .venv/bin/activate
```

Chaves e recibos usados neste exemplo devem conter apenas dados fictícios.

## Chaves de demonstração

Gere uma chave P-256 protegida por senha e sua chave pública com OpenSSL:

```bash
openssl ecparam -name prime256v1 -genkey -noout | openssl pkcs8 -topk8 -v2 aes-256-cbc -out signing-private.pem
openssl pkey -in signing-private.pem -pubout -out signing-public.pem
```

Crie uma chave HMAC aleatória de pelo menos 32 bytes em um gestor de segredos ou local protegido. Para um teste local com valores fictícios, OpenSSL pode gerar bytes aleatórios:

```bash
openssl rand -out commitment.key 32
```

Chaves privadas, chaves HMAC e artefatos locais `*.receipt.json`/`*.manifest.json` estão no `.gitignore`, mas ignore rules não substituem controles de acesso. Não use essas instruções como gerenciamento de chaves de produção. Defina `FOUNDLAB_SIGNING_PASSWORD` por um mecanismo seguro no ambiente do processo; não coloque a senha na linha de comando.

Confira o fingerprint:

```bash
python evidence_cli.py fingerprint signing-public.pem
```

Registre/compare o valor `sha256:...` por um canal confiável. Calcular o fingerprint da chave recebida no mesmo canal que o recibo não autentica a identidade do emissor.

## Emitir e verificar um recibo

Emita um recibo. Por padrão ele vai para `stdout`; `--output` grava apenas o recibo em um arquivo novo e recusa sobrescrita:

```bash
python evidence_cli.py issue examples/roi_input.json --signing-key signing-private.pem --signing-key-password-env FOUNDLAB_SIGNING_PASSWORD --commitment-key commitment.key --commitment-key-id local-demo-v1 --output decision-01.receipt.json
```

Verifique assinatura, fingerprint, chave HMAC, compromisso da entrada e resultado reproduzido:

```bash
python evidence_cli.py verify examples/roi_input.json decision-01.receipt.json --public-key signing-public.pem --trusted-signing-key-id sha256:SUBSTITUA_PELO_FINGERPRINT_CONFIAVEL --commitment-key commitment.key --commitment-key-id local-demo-v1
```

Uma verificação bem-sucedida imprime `status: VERIFIED`. Se qualquer premissa mudar, o replay falha. A chave HMAC deve ser obtida do mesmo gestor/escopo autorizado da emissão; o identificador sozinho não é a chave.

## Encadear e verificar decisões

Para criar o próximo recibo, forneça a cabeça previamente verificada:

```bash
python evidence_cli.py issue examples/roi_input.json --signing-key signing-private.pem --signing-key-password-env FOUNDLAB_SIGNING_PASSWORD --commitment-key commitment.key --commitment-key-id local-demo-v1 --previous-receipt decision-01.receipt.json --output decision-02.receipt.json
```

Verifique a sequência na ordem original:

```bash
python evidence_cli.py verify-chain --entry examples/roi_input.json decision-01.receipt.json --entry examples/roi_input.json decision-02.receipt.json --public-key signing-public.pem --trusted-signing-key-id sha256:SUBSTITUA_PELO_FINGERPRINT_CONFIAVEL --commitment-key commitment.key --commitment-key-id local-demo-v1
```

O comando exige que o primeiro elo não tenha predecessor e que cada recibo subsequente aponte ao hash integral do anterior. Ele usa a mesma chave de assinatura e de compromisso para todos os elos; rotação de chaves dentro da cadeia ainda não é suportada.

## Criar e verificar um lote Merkle

Agrupe recibos distintos em um manifesto assinado:

```bash
python evidence_cli.py merkle-build decision-01.receipt.json decision-02.receipt.json --signing-key signing-private.pem --signing-key-password-env FOUNDLAB_SIGNING_PASSWORD --receipt-public-key signing-public.pem --trusted-receipt-key-id sha256:SUBSTITUA_PELO_FINGERPRINT_CONFIAVEL --output batch.manifest.json
```

Verifique a assinatura do manifesto e a inclusão do recibo:

```bash
python evidence_cli.py merkle-verify batch.manifest.json decision-02.receipt.json --public-key signing-public.pem --trusted-signing-key-id sha256:SUBSTITUA_PELO_FINGERPRINT_CONFIAVEL
```

Isso valida a associação do recibo à raiz Merkle assinada. Para provar também que ele representa o cálculo esperado, execute `verify` para aquele recibo. Para detectar rollback, ancore a raiz ou a cabeça mais recente em armazenamento/controlador independente; este projeto não fornece essa âncora.

## Formato e limites

- JSON de compromisso: UTF-8, chaves de objeto ordenadas, separadores compactos, sem ASCII escaping ou NaN/Infinity. Não é uma implementação completa de RFC 8785.
- `DecisionID`: UUID aleatório; não codifica identidade nem tempo.
- O processo lê o arquivo de entrada, mas não inclui valores no recibo nem apaga/gerencia o arquivo-fonte.
- O processo pode persistir somente o recibo quando `--output` é informado; esse arquivo não contém os valores originais.
- Não há KMS/HSM, armazenamento imutável, trusted timestamp, rotação/revogação automática ou garantia de zero-persistence do host.
- HMAC reduz exposição por adivinhação pública do payload, mas o compromisso continua sendo dado sensível para quem detém a chave e não é anonimização.
