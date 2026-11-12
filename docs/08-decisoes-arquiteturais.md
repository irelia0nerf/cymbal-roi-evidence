# Decisões arquiteturais

**Estudo independente de Alex Bolson · FoundLab**

Este documento registra decisões do protótipo local. Elas demonstram um caminho técnico; não substituem aprovação de segurança, revisão financeira ou decisões de arquitetura de produção.

## ADR-001 — manter a aritmética em um motor determinístico

**Estado:** aceito e implementado.

**Decisão:** calcular ROI com `Decimal`, contrato estrito e versão de fórmula identificável. O modelo generativo, quando vier a existir, poderá explicar o resultado, mas não será a autoridade aritmética.

**Motivo:** os mesmos dados válidos precisam produzir a mesma conclusão financeira, independentemente da redação ou do modelo que a apresenta.

**Consequência:** `roi_model.calculate` é verificável por testes e replay local. Isso não valida a origem das premissas nem o mérito financeiro delas.

## ADR-002 — assinar compromissos, não copiar o payload para o recibo

**Estado:** aceito e implementado como demonstração local.

**Decisão:** produzir um recibo sem valores do cliente. O recibo contém compromissos HMAC-SHA256 da entrada e do resultado, identificadores e versão da fórmula; ECDSA P-256 assina o envelope. O verificador precisa do payload original e da chave HMAC para repetir a análise.

**Motivo:** um SHA-256 simples de valores financeiros pode permitir ataques de dicionário. O HMAC mantém os compromissos não verificáveis por observadores sem a chave, enquanto a assinatura pode ser verificada com uma chave pública confiável.

**Consequências e limites:**

- a chave HMAC é necessária para verificar os compromissos e deve ser protegida;
- quem possui a chave HMAC consegue produzir compromissos; ela não é uma assinatura nem prova de autoria;
- ECDSA autentica o envelope apenas quando a chave pública foi confiada por um canal externo;
- este pacote não integra KMS/HSM, rotação, revogação ou política de acesso às chaves;
- o recibo não contém payload, mas processo, entrada original e arquivos temporários do sistema operacional estão fora das garantias do programa.

## ADR-003 — separar identidade, compromisso e resultado financeiro

**Estado:** aceito e implementado.

**Decisão:** atribuir um UUID aleatório a cada emissão. Não derivar o `DecisionID` dos dados de entrada: IDs determinísticos poderiam revelar igualdade entre decisões. O verificador compara os compromissos e recalcula a saída em vez de confiar em um resultado serializado dentro do recibo.

**Consequência:** o `DecisionID` identifica o recibo, mas não é identidade do cliente, timestamp confiável ou prova isolada da origem dos dados.

## ADR-004 — encadear eventos e agrupar recibos em uma árvore Merkle

**Estado:** aceito e implementado no pacote local.

**Decisão:** permitir que um recibo aponte para o hash do recibo anterior e agrupar recibos únicos em um manifesto Merkle assinado. Hashes folha usam prefixo `0x00`; nós internos usam `0x01`; em nível com quantidade ímpar, a última folha é duplicada. Assinaturas e manifestos usam JSON canônico definido para este projeto.

**Consequências:**

- o verificador detecta alteração, reordenação e elos ausentes dentro da sequência recebida;
- provas de inclusão podem demonstrar que um recibo pertence a uma raiz assinada;
- sem ancoragem externa da cabeça da cadeia ou do manifesto, rollback e truncamento do final não são detectáveis;
- recibos duplicados são recusados no mesmo manifesto;
- a CLI valida as assinaturas dos recibos antes de construir o manifesto; a função de biblioteca pressupõe que o chamador já fez essa validação;
- normalização Unicode segue o conteúdo recebido; a serialização é determinística para a mesma estrutura JSON, não uma implementação completa do padrão RFC 8785.

## Não decidido neste pacote

Identidade organizacional, relógio confiável, políticas de retenção, armazenamento imutável, integração Google Cloud, observabilidade OpenTelemetry, rotação de chaves, isolamento multi-tenant e política legal de retenção continuam fora do escopo.
