# Plano de integração

**Estudo independente de Alex Bolson · FoundLab**

Escopo futuro. Nenhuma fase Google Cloud foi executada nesta entrega. Não há compromisso de prazo ou responsável externo atribuído.

| Ordem | Trabalho | Critério de aceite |
| --- | --- | --- |
| 1 | Aprovar definição de ROI, benefício incremental e política comercial | Financeiro reproduz casos conhecidos e aprova as premissas |
| 2 | Mapear dados e permissões | Campos, origem, atualização e limites por cliente definidos |
| 3 | Integrar ferramenta Python proprietária | Usar o motor local como referência; validar casos viáveis/inviáveis e restrições técnicas |
| 4 | Construir agente ADK com versões fixadas | Chamadas às ferramentas reais; falha explícita quando dados faltam; números vêm da ferramenta |
| 5 | Integrar BigQuery e RAG | Leitura autorizada, referências e teste de documento conflitante ou malicioso |
| 6 | Implantar no runtime escolhido | Identidade, IAM, egress, retenção, logs e observabilidade verificados no ambiente; evidências de aceite preservadas |
| 7 | Registrar no Gemini Enterprise | Acesso apenas ao público autorizado e respeito às permissões |
| 8 | Avaliar o fluxo completo | Proposta com números idênticos aos retornados pelas ferramentas e aprovação antes de envio |

## Testes relevantes para a integração

- Cliente A não acessa dados do cliente B.
- Documento recuperado não consegue autorizar desconto, envio ou chamada arbitrária de ferramenta.
- Dado ausente ou desatualizado não vira uma projeção aparentemente definitiva.
- Resultado financeiro independe da redação escolhida pelo LLM.
- Falha do algoritmo, timeout de consulta ou erro de ferramenta interrompe a proposta final.
- Reexecução de ação externa não duplica registros ou envios.
- Logs e traces obedecem à política de retenção e não expõem dados sensíveis indevidos.

## Evidência adicional que eu exigiria antes de produção

O pacote já demonstra recibos ECDSA, compromissos HMAC, cadeia SHA-256 e manifestos Merkle locais. Para produção, cada decisão ainda precisaria carregar referências autorizadas e datas das fontes, versões de ferramentas e política, estado de aprovação e ligação a uma identidade institucional. A evidência precisa evitar payloads sensíveis; assinatura de raiz, retenção imutável e gestão de chaves precisam ser integradas e verificadas no ambiente escolhido.

O artefato local não prova origem ou atualidade dos dados, identidade jurídica, horário confiável ou ausência de rollback. A cabeça da cadeia e manifestos precisam de ancoragem independente, e chaves precisam de ciclo de vida KMS/HSM.

## Escolhas ainda necessárias

Projeto, região, fontes reais, identidade do agente, edição do Gemini Enterprise, método de registro, versões do ADK/SDK e política de aprovação. Validar essas escolhas na documentação oficial antes de criar código de integração. Este pacote evita inventar APIs ou comandos de deployment.
