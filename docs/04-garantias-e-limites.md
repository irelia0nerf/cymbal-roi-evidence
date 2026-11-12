# Garantias, fórmulas e limites

**Estudo independente de Alex Bolson · FoundLab**

## Por que a calculadora é determinística

Minha escolha de engenharia neste exemplo é manter a aritmética fora do LLM: `Decimal`, contrato estrito e resultados reproduzíveis para entradas iguais. Isso torna o cálculo inspecionável, mas não basta para chamar a solução de auditável. A CLI de cálculo não atribui `DecisionID` nem registra a origem dos dados; a CLI de evidências emite um `DecisionID` e recibo assinado, mas não dispõe de fontes empresariais para estabelecer linhagem a montante.

O processo não faz chamadas de rede nem grava arquivos por conta própria; ele lê o JSON informado e escreve o resultado em `stdout`. Isso descreve o comportamento do programa, não uma garantia de zero-persistence do ambiente, nem controles de retenção do sistema operacional, terminal ou pipeline que o execute.

Também mantenho o `stdout` como JSON puro para automação: identidade e contexto FoundLab pertencem à documentação, não a um banner que quebre o contrato da CLI.

## Evidência criptográfica implementada

`evidence.py` usa JSON UTF-8 determinístico para o contrato local, HMAC-SHA-256 para comprometer entrada e saída sem publicar seus hashes diretos, ECDSA P-256 para assinar o recibo e SHA-256 para encadear eventos. `merkle.py` cria manifestos assinados e provas de inclusão com separação de domínio entre folhas e nós internos. `evidence_cli.py` oferece emissão, replay/verificação, cadeia, fingerprint e lotes Merkle.

Um verificador autorizado precisa do payload original, da chave HMAC, da chave pública confiável e dos identificadores esperados das chaves. A chave HMAC protege contra verificação pública por dicionário, mas também permite a quem a possui produzir compromissos; autoria vem da assinatura ECDSA e da confiança externa no fingerprint.

**O que o recibo não prova:** veracidade ou autorização da fonte, identidade jurídica do detentor da chave, horário, ausência de cópias do payload no host, impossibilidade de replay, retenção imutável ou ausência de rollback sem âncora externa. As chaves são carregadas de arquivos externos; KMS/HSM, rotação e revogação não estão integrados.

## Correções técnicas da narrativa da aula

| Formulação simplificada | Formulação defensável |
| --- | --- |
| RAG garante que o LLM use apenas dados verificados | RAG fornece contexto recuperado e reduz alucinações. Fonte, atualização, relevância e fidelidade da resposta exigem validação [S7] |
| O LLM entrega cálculos financeiros exatos | Ferramentas numéricas aprovadas devem calcular; o modelo pode interpretar e explicar os resultados |
| O ROI previsto é exato | A aritmética pode ser reproduzível; o retorno futuro depende das premissas |
| VPC Service Controls impede toda exfiltração | Perímetros mitigam caminhos de exfiltração em serviços abrangidos. APIs externas exigem controles adicionais [S8] |
| Runtime gerenciado torna a solução pronta para produção | O runtime oferece infraestrutura; dados, IAM, testes, avaliação e operação da solução continuam exigindo configuração |
| CMEK e residência são universais | Validar suporte por serviço, região, endpoint e configuração. Há combinações com restrições [S6] |

## Contrato do exemplo local

Entrada: objeto JSON com exatamente `currency`, `scenarios` e `assumptions`. Cada cenário tem `name`, `initial_investment`, `annual_benefits` e `annual_operating_costs`. Assumptions é uma lista não vazia de textos; é metadado declarado pelo chamador, sem verificação automática.

- Moeda aceita pelo exemplo: `BRL`. A validação é sintática e não faz conversão cambial.
- Valores monetários: strings decimais não negativas, até duas casas, sem expoente, até 15 dígitos inteiros. Exemplo: `"12500.50"`.
- Investimento inicial: estritamente positivo.
- Horizonte: de 1 a 30 anos, igual em todos os cenários comparados.
- Benefícios e custos: listas de mesmo tamanho.
- Nomes de cenários: não vazios e únicos.
- Chaves desconhecidas, chaves duplicadas, tipos incompatíveis, infinitos e valores negativos são rejeitados.

## Fórmulas v1

Para investimento inicial I, benefício anual B e custo operacional anual C:

```text
beneficio_liquido_antes_investimento = soma(B[t] - C[t])
resultado_liquido = beneficio_liquido_antes_investimento - I
roi_percentual = (resultado_liquido / I) * 100
```

Payback simples: primeiro instante em que o fluxo líquido acumulado recupera o investimento inicial. O exemplo interpola a fração do ano supondo distribuição uniforme do fluxo líquido naquele ano e converte para meses. Se não houver recuperação no horizonte, retorna `null`. O payback identifica a primeira recuperação; eventuais perdas posteriores continuam refletidas no resultado acumulado.

Exemplo fictício A: investimento de R$ 1.000.000; benefício anual de R$ 700.000; custo anual de R$ 200.000; horizonte de três anos. Fluxo líquido acumulado antes do investimento: R$ 1.500.000; resultado líquido: R$ 500.000; ROI: 50,00%; payback simples: 24,00 meses.

## Precisão e interpretação

A implementação usa `Decimal` com contexto local e arredondamento `ROUND_HALF_UP` na apresentação. As contas intermediárias não são arredondadas para centavos a cada operação. Percentuais e meses são apresentados com duas casas decimais.

Não calcula VPL, TIR, impostos, inflação, desconto temporal, financiamento, sazonalidade ou probabilidade de demanda. Benefícios não são automaticamente receita: o chamador deve evitar dupla contagem e definir contribuição econômica incremental em relação ao cenário de referência.

Os dois cenários demonstrativos são entradas manuais. O código não pesquisa preços, não valida compatibilidade técnica e não encontra a configuração ótima. Não classifica a melhor alternativa automaticamente.

## Segurança do exemplo

O motor de ROI não realiza chamadas de rede nem grava arquivos. A CLI de evidências lê chaves fornecidas pelo operador e pode gravar somente o recibo quando recebe `--output`; a criação falha se o arquivo já existir. Nenhuma CLI copia o payload para um arquivo de saída. O JSON de entrada continua no caminho indicado pelo operador, e o host pode manter cópias em memória, swap, logs ou backups. Entrada local não confiável ainda deve respeitar controles de acesso do ambiente; o exemplo não é um serviço multiusuário.
