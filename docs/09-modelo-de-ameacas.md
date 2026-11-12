# Modelo de ameaças

**Estudo independente de Alex Bolson · FoundLab**

## Escopo e hipótese de segurança

O alvo é o fluxo local de emissão e verificação de recibos: o operador fornece um JSON, o motor calcula ROI, cria compromissos HMAC e assina o recibo com ECDSA P-256. Um verificador independente recebe novamente o JSON, o recibo, uma chave pública confiável e a chave HMAC correspondente.

O objetivo é detectar adulteração do cálculo, do envelope e da sequência de evidências. Este modelo não declara conformidade LGPD, segurança de produção ou proteção contra comprometimento do host.

## Ativos

| Ativo | Sensibilidade | Proteção no protótipo |
| --- | --- | --- |
| JSON de entrada e premissas | Pode conter dados comerciais sensíveis | Não é copiado para o recibo; continua sob controle do operador e do sistema operacional |
| Chave privada ECDSA P-256 | Crítica; permite assinar recibos | Lida de PEM externo; não é incluída no repositório nem gerenciada pelo programa |
| Chave HMAC de compromisso | Crítica; permite testar ou criar compromissos | Lida de arquivo externo; não é incluída no recibo nem gerenciada pelo programa |
| Recibo assinado | Artefato sem payload, mas vinculável e sensível a quem possui a chave HMAC | Contém compromissos, metadados e assinatura; não contém valores de entrada ou resultado |
| Chave pública e fingerprint confiável | Necessárias para autenticar o emissor | Verificador exige fingerprint esperado obtido externamente |
| Cabeça da cadeia/raiz Merkle | Necessária para detectar rollback | Deve ser ancorada externamente; persistência/ancoragem não implementada |

## Fronteiras de confiança

1. **Operador → processo local:** entrada, PEM e chave HMAC são fornecidos ao processo. O programa não verifica quem controla esses arquivos.
2. **Processo → recibo:** o código calcula compromissos e assinatura. A correção depende do código, runtime e dependências instalados.
3. **Emissor → verificador:** o recibo pode ser transportado sem o payload, mas a chave pública precisa ser autenticada fora de banda.
4. **Verificador → âncora:** uma cadeia ou raiz assinada não prova que é a versão mais recente. Um armazenamento ou checkpoint externo deve preservar a cabeça esperada.

## Ameaças, controles e risco residual

| Ameaça | Controle no protótipo | Risco residual |
| --- | --- | --- |
| Alterar a entrada depois da emissão | Compromisso HMAC da entrada e replay no verificador | Operadores que têm a chave HMAC podem emitir compromissos próprios |
| Alterar o resultado ou campos do recibo | Assinatura ECDSA e comparação do compromisso do resultado recalculado | Comprometimento da chave privada permite forjar recibos |
| Substituir a chave pública no momento da verificação | Fingerprint esperado obrigatório | Distribuição do fingerprint não é automatizada |
| Adivinhar entradas por hashes publicados | HMAC, em vez de hash público direto dos valores | A chave HMAC pode ser comprometida; IDs e metadados ainda podem revelar contexto |
| Reordenar ou omitir recibos no meio da cadeia | Hash encadeado e verificação estrita da ordem | Se a cabeça esperada não estiver ancorada, truncamento do final/rollback não é detectável |
| Inserir/remover folhas em um lote | Manifesto Merkle assinado e prova de inclusão | Manifesto antigo pode ser reapresentado sem timestamp ou âncora externa |
| Reutilizar recibo ou repetir ação de negócio | `DecisionID` aleatório identifica cada emissão | Não há banco de deduplicação nem prevenção de replay operacional |
| Expor entrada em logs, swap, dumps ou backups | O código não registra nem copia o payload por conta própria | O host, shell, editor, backup e sistema de arquivos não são controlados pelo projeto |
| Negar que uma assinatura foi emitida em determinado horário | Nenhum controle | Não há timestamp authority nem prova temporal |

## Não coberto

Comprometimento de host, side channels, malware, DoS, exfiltração por ferramentas externas, autorização multi-tenant, rotação e revogação, armazenamento imutável, disponibilidade, falhas de infraestrutura cloud, segurança do ADK/RAG e avaliação jurídica. Esses riscos exigem controles e evidências do ambiente real.

**Conclusão:** a implementação prova criptograficamente a integridade e a consistência de um artefato sob chaves confiáveis; não prova por si só que os dados são verdadeiros, que o operador é autorizado ou que o sistema não reteve dados.
