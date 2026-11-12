# Gemini Enterprise: conceito, agentes e casos de uso

**Estudo independente de Alex Bolson · FoundLab**

Este guia não é documentação oficial do Google. Organizo capacidades públicas do produto para avaliar um caso de uso; disponibilidade, permissões e integração precisam ser demonstradas no ambiente real.

## Definição e objetivo

O Gemini Enterprise é uma plataforma de pesquisa na intranet, assistência de IA e acesso a agentes para profissionais que trabalham com informação. Seu objetivo é conectar conhecimento organizacional às tarefas desses profissionais, reduzindo a busca manual entre sistemas e permitindo respostas e workflows contextualizados. [S1]

A pesquisa considera as permissões de acesso configuradas. Isso depende da integração das fontes e dos controles correspondentes; não representa autorização irrestrita para executar ações nos sistemas conectados.

| Função | Entrega |
| --- | --- |
| Pesquisa corporativa | Localizar conteúdo em documentos e aplicações conectadas |
| Assistente de IA | Responder perguntas, sintetizar informações e ajudar a criar conteúdo |
| Plataforma de agentes | Disponibilizar agentes especializados e fluxos de trabalho |

## Origem dos agentes

| Origem solicitada na aula | Responsabilidade |
| --- | --- |
| Agente padrão: Core Assistant | Atender interações em que o usuário não selecionou outro agente [S2, S3] |
| Agentes predefinidos do Google | Executar especializações prontas, como pesquisa aprofundada com Deep Research [S2, S4] |
| Agentes personalizados | Incorporar instruções, ferramentas e processos da organização; podem ser construídos na plataforma ou desenvolvidos com ADK e integrados [S2] |

A galeria atual também contempla agentes de parceiros. A disponibilidade varia conforme edição, habilitação administrativa e integrações. [S4]

## Casos de uso

| Categoria | Exemplo aplicado à Cymbal Labs |
| --- | --- |
| Pesquisa | Encontrar políticas comerciais, especificações técnicas e histórico do cliente |
| Resumo | Consolidar reuniões, documentos e registros de atendimento |
| Geração | Produzir rascunhos de propostas e justificativas financeiras contextualizadas |
| Ações | Acionar ferramentas e workflows habilitados, como solicitar uma simulação |

Os exemplos acima são aplicações propostas para o caso fictício. Pesquisa, assistência e acesso a agentes são capacidades documentadas; cada ação concreta depende da ferramenta, das permissões e da integração implementadas. [S1, S2, S4]

## Distinção entre experiência e construção

O Gemini Enterprise pode oferecer a interface usada pelo vendedor para acessar o agente. O ADK define a lógica especializada. O runtime gerenciado executa o agente. Um agente personalizado precisa ser registrado e habilitado para aparecer nessa experiência. A integração não acontece apenas pela existência do código. [S2, S5]

As referências S1-S8 estão em `06-fontes.md`.

**Lente FoundLab:** acesso a uma capacidade não prova que uma decisão esteja autorizada, que a fonte esteja atualizada ou que o resultado seja auditável. Neste estudo, trato esses pontos como requisitos de desenho, não como garantias do produto.
