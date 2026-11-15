# DECISÕES TÉCNICAS
## Grupo 5 — Cidade Inteligente: Auditoria e Prevenção de Fraudes

**Projeto:** Projeto Integrador  
**Cliente fictício:** Prefeitura de Cidade Conectada  
**Data de atualização:** 15/11/2026  
**Status:** Decisões registradas — algumas validações pendentes

---

## 1. Objetivo

Este documento registra as principais decisões técnicas adotadas durante o desenvolvimento da solução Cidade Inteligente, apresentando suas justificativas, impactos e critérios de utilização.

O objetivo é manter a rastreabilidade das escolhas realizadas pelas frentes de Engenharia de Dados, FinOps/Machine Learning, Business Intelligence e Engenharia de Inteligência Artificial.

## 2. Decisões de arquitetura e Engenharia de Dados

### DT-001 — Utilização da arquitetura Medallion

**Decisão:** organizar o processamento dos dados nas camadas Bronze, Silver e Gold.

**Justificativa:** separar a ingestão dos dados originais, o tratamento e a disponibilização de estruturas especializadas para consumo.

**Implementação documentada:**
- Bronze: dados de origem PaySim.
- Silver: dados tratados e padronizados.
- Gold ML: features destinadas aos modelos.
- Gold BI: dados agregados para indicadores e dashboards.

**Responsável:** Engenharia de Dados.

### DT-002 — Identificação das transações por hash

**Decisão:** utilizar um identificador determinístico baseado em SHA-256, truncado em 16 caracteres.

**Justificativa:** criar uma chave de rastreabilidade para as transações processadas.

**Ponto de atenção:** a chave é derivada dos atributos da transação e não deve ser interpretada como um identificador original fornecido pelo sistema financeiro. A deduplicação deverá preservar operações legítimas distintas.

**Responsável:** Engenharia de Dados.

### DT-003 — Separação das estruturas de consumo

**Decisão:** disponibilizar estruturas Gold com finalidades distintas para Machine Learning e Business Intelligence.

**Justificativa:** permitir que cada componente consuma dados organizados conforme suas necessidades, evitando misturar estruturas de treinamento com estruturas de indicadores gerenciais.

**Responsável:** Engenharia de Dados.

## 3. Decisões de preparação e qualidade dos dados

### DT-004 — Preservação da base original

**Decisão:** manter o DataFrame original e criar cópias específicas para os experimentos de Machine Learning.

**Justificativa:** preservar as informações da EDA e permitir comparações entre diferentes estratégias de preparação.

### DT-005 — Não remover outliers indiscriminadamente

**Decisão:** adotar o Capping como estratégia principal experimental para a variável `amount`, mantendo a remoção de outliers apenas como cenário comparativo.

**Justificativa:** a análise do treinamento demonstrou que 47,36% das transações fraudulentas seriam removidas pelo critério IQR.

**Parâmetro utilizado:**

| Indicador | Resultado |
|---|---:|
| Primeiro quartil | R$ 13.473,60 |
| Terceiro quartil | R$ 209.126,25 |
| Limite superior | R$ 502.605,22 |

O limite foi calculado exclusivamente no treinamento e aplicado também à validação e ao teste.

### DT-006 — Tratamento de Missing Values

**Decisão:** não realizar imputação na base atualmente analisada.

**Justificativa:** o diagnóstico encontrou zero valores ausentes nas colunas verificadas.

A estratégia deverá ser reavaliada caso novos dados apresentem valores ausentes.

### DT-007 — Preservação de valores zerados

**Decisão:** não tratar automaticamente saldos iguais a zero como valores ausentes.

**Justificativa:** o zero representa um valor registrado no dataset e pode conter informação relevante sobre o comportamento das transações.

### DT-008 — Binning por percentis

**Decisão:** criar cinco categorias para a variável `amount`, utilizando os percentis de 20%, 40%, 60% e 80%.

**Justificativa:** representar os valores financeiros em faixas, permitindo investigar padrões adicionais.

Os limites foram calculados no treinamento e mantidos nos demais conjuntos.

### DT-009 — Transformação logarítmica

**Decisão:** criar a variável `log_amount` utilizando `np.log1p()`.

**Justificativa:** reduzir a escala e a assimetria dos valores financeiros, principalmente para os experimentos com KNN.

A assimetria observada passou de 1,1809 para -0,7375 após a