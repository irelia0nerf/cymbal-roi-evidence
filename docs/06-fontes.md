# Fontes e proveniência

**Estudo independente de Alex Bolson · FoundLab**

Data de referência: 12/11/2026. As páginas oficiais abaixo foram consultadas durante a pesquisa que embasou este pacote. Os links são referências vivas; não foi incluída cópia integral das páginas.

| ID | Fonte oficial | Uso |
| --- | --- | --- |
| S1 | [What is Gemini Enterprise?](https://docs.cloud.google.com/gemini/enterprise/docs) | Definição, objetivo e pesquisa com permissões |
| S2 | [Agents overview](https://docs.cloud.google.com/gemini/enterprise/docs/agents-overview) | Tipos de agentes e integração de agentes ADK |
| S3 | [Core Assistant](https://docs.cloud.google.com/gemini/enterprise/docs/core-assistant) | Agente padrão |
| S4 | [Agent Gallery](https://docs.cloud.google.com/gemini/enterprise/docs/agent-gallery) | Agentes Google, internos e de parceiros; workflows |
| S5 | [Agent Platform overview](https://docs.cloud.google.com/gemini-enterprise-agent-platform/overview) | Agent Garden, ADK, RAG e runtime |
| S6 | [Release notes](https://docs.cloud.google.com/gemini-enterprise-agent-platform/release-notes) | Mudanças de nomenclatura e limites de combinações de recursos |
| S7 | [Generative AI glossary](https://docs.cloud.google.com/docs/ai-ml/generative-ai/glossary) | Grounding reduz a probabilidade de alucinações |
| S8 | [VPC Service Controls overview](https://docs.cloud.google.com/vpc-service-controls/docs/overview) | Perímetros, IAM e limites frente a APIs externas |

## Mudanças de nomenclatura

| Nome usado na aula | Nome/contexto da documentação consultada |
| --- | --- |
| Vertex AI Agent Builder | Parte da evolução para Gemini Enterprise Agent Platform |
| Vertex AI Agent Engine | Agent Runtime |
| Agent Engine Sessions | Agent Platform Sessions |
| Agent Engine Memory Bank | Agent Platform Memory Bank |

O aplicativo Gemini Enterprise e a plataforma de desenvolvimento têm papéis distintos, mesmo compartilhando a marca. As notas de versão sustentam a correspondência acima; não há afirmação de compatibilidade automática entre SDKs, endpoints ou exemplos antigos e novos.

## Material de referência do estudo

- Cenário fictício Cymbal Labs e objetivos didáticos, consolidados editorialmente nos documentos 01-05.
- Dois recortes de uma página fornecidos com o pacote: um sobre alocação de recursos e uso de ADK e outro com a visão geral do módulo. O segundo contém a referência `https://www.skills.google/paths/4525/course_templates/1504/documents/623497`.
- Os arquivos originais permanecem em `sources/` no pacote local e são ignorados pelo Git (`sources/*.pdf`). Eles não são incluídos em uma publicação pública por padrão.

Esses recortes não comprovam a existência de uma implementação real da Cymbal Labs.

## Autoria e direitos

A concepção do estudo e o enquadramento FoundLab são de Alex Bolson. A documentação e a implementação foram preparadas com assistência de IA e devem ser revisadas antes de qualquer uso operacional. A Cymbal Labs é fictícia. Os PDFs e as marcas Google pertencem aos respectivos titulares; seu uso como referência não concede licença de redistribuição pública. A regra de ignore reduz o risco de publicar os PDFs por acidente, mas não substitui uma revisão dos direitos antes de qualquer distribuição. O código e a documentação originais deste projeto estão sob Apache-2.0; essa licença não abrange marcas ou conteúdo de terceiros.

O motor de ROI usa a biblioteca padrão do Python. A camada ECDSA P-256 depende de `cryptography==50.0.2`, fixada em `requirements.txt`. Chaves são fornecidas pelo operador e não estão no pacote. Decisões de canonicalização, assinatura e escopo estão em `08-decisoes-arquiteturais.md`; ameaças e procedimentos de replay/inclusão estão em `09-modelo-de-ameacas.md` e `10-verificacao-de-evidencias.md`.
