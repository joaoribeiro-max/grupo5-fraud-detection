# ESCOPO DO PROJETO
## Grupo 5 BANK Inteligente: Auditoria e Prevenção de Fraudes

**Cliente fictício:** Prefeitura de Cidade Conectada  
**Projeto Integrador:** Grupo 5  
**Status:** Em desenvolvimento  
**Data de atualização:** 15/11/2026

---

## 1. Contextualização

O projeto Cidade Inteligente tem como proposta desenvolver uma solução tecnológica voltada à auditoria e prevenção de fraudes em transações financeiras.

A solução utiliza recursos de Engenharia de Dados, Machine Learning, Business Intelligence e Inteligência Artificial para organizar informações, identificar padrões suspeitos, apresentar indicadores e apoiar a análise de possíveis irregularidades.

O desenvolvimento utiliza o dataset PaySim, um conjunto de dados financeiros sintéticos que permite simular operações legítimas e fraudulentas para experimentação e avaliação dos modelos.

## 2. Objetivo geral

Desenvolver um protótipo integrado de auditoria e prevenção de fraudes, capaz de processar dados financeiros, identificar padrões associados a transações suspeitas, apresentar indicadores gerenciais e disponibilizar recursos de consulta e análise por meio de um agente de Inteligência Artificial.

## 3. Objetivos específicos

- Construir uma estrutura organizada de processamento de dados utilizando arquitetura Medallion.
- Implementar processos de limpeza, padronização e transformação dos dados.
- Desenvolver modelos de Machine Learning para identificação de transações fraudulentas.
- Comparar os algoritmos KNN e LightGBM.
- Avaliar os modelos utilizando métricas adequadas para bases desbalanceadas.
- Desenvolver dashboards para acompanhamento de indicadores.
- Construir um agente de Inteligência Artificial para apoiar consultas e análises.
- Estimar a exposição financeira associada às transações classificadas como fraudulentas.
- Integrar os componentes desenvolvidos pelas diferentes frentes de trabalho.

## 4. Escopo funcional

A solução contempla quatro grandes componentes.

### 4.1 Engenharia de Dados

Responsável pela ingestão, organização, limpeza, validação e transformação dos dados.

A arquitetura contempla:

- Bronze: dados de origem.
- Silver: dados tratados e padronizados.
- Gold: dados preparados para Machine Learning e Business Intelligence.

O processamento é desenvolvido utilizando Databricks e Delta Live Tables.

### 4.2 Machine Learning e FinOps

Responsável pelo desenvolvimento e avaliação dos modelos preditivos.

Atividades previstas:

- Análise exploratória dos dados.
- Investigação de Data Leakage.
- Tratamento de valores extremos e ausentes.
- Feature Engineering e Binning.
- Normalização das variáveis para KNN.
- Treinamento dos modelos KNN e LightGBM.
- Comparação de desempenho.
- Estimativa de exposição financeira.
- Desenvolvimento de função Python modular para utilização das previsões.

### 4.3 Business Intelligence

Responsável pela construção de indicadores e visualizações para apoiar o acompanhamento das transações e dos registros classificados como fraudulentos.

Os indicadores deverão permitir análises por tipo de operação, período e volume financeiro, entre outras dimensões disponíveis.

### 4.4 Engenharia de Inteligência Artificial

Responsável pelo desenvolvimento de um agente baseado em Google ADK, com recursos de consulta e apoio à análise.

A proposta contempla integração com ferramentas de consulta SQL, recursos de busca lexical e componentes de análise desenvolvidos pelas demais frentes.

## 5. Entregáveis previstos

| Entregável | Descrição |
|---|---|
| Pipeline de dados | Processamento e organização na arquitetura Medallion |
| Base Gold ML | Dados e features preparados para treinamento e inferência |
| Modelos de ML | Implementação e comparação entre KNN e LightGBM |
| Avaliação dos modelos | Métricas, resultados e análise de desempenho |
| Função modular Python | Execução reutilizável das previsões e estimativas |
| Dashboard de BI | Visualização dos principais indicadores |
| Agente de IA | Interface de consulta e apoio à análise |
| Documentação técnica | Registro da arquitetura, decisões e resultados |
| Apresentação final | Demonstração integrada da solução |

## 6. Fora do escopo

Para manter os limites do projeto claros, não fazem parte do escopo do protótipo:

- Implantação de um sistema bancário ou financeiro real.
- Processamento de transações financeiras reais.
- Bloqueio efetivo de operações bancárias.
- Recuperação de valores financeiros.
- Garantia de prevenção de todas as fraudes.
- Substituição de sistemas corporativos de auditoria.
- Comprovação de prejuízos reais a partir do dataset sintético.

O protótipo tem finalidade acadêmica, experimental e demonstrativa.

## 7. Premissas e restrições

- O PaySim é um dataset sintético.
- Os resultados dos modelos representam experimentos realizados sobre dados simulados.
- A qualidade dos resultados depende da qualidade e das características da base utilizada.
- A arquitetura considera a integração entre Engenharia de Dados, ML, BI e IA.
- As funcionalidades deverão respeitar as tecnologias e ferramentas definidas pelo projeto.
- Os resultados financeiros deverão ser apresentados como estimativas baseadas nas premissas adotadas, e não como perdas ou recuperações reais.

## 8. Equipe e responsabilidades

| Integrante | Frente de atuação |
|---|---|
| Rodrigo | Engenharia de Dados |
| João Batista | FinOps e Machine Learning |
| Rafael | Engenharia de Inteligência Artificial |
| Raphael Aires | Business Intelligence |
| Ramon | TechSales e proposta de valor |

As responsabilidades poderão ser ajustadas conforme a necessidade de integração e validação das entregas.

## 9. Critérios gerais de sucesso

O projeto será considerado tecnicamente consistente quando:

- A pipeline de dados estiver estruturada e documentada.
- Os dados estiverem disponíveis para consumo pelas frentes de ML e BI.
- Os modelos KNN e LightGBM tiverem sido treinados e comparados.
- A avaliação dos modelos apresentar métricas adequadas ao desbalanceamento das classes.
- O componente de estimativa financeira estiver documentado e integrado.
- O dashboard apresentar indicadores coerentes com os dados.
- O agente de IA estiver integrado aos recursos previstos.
- A solução apresentar uma demonstração integrada e documentada.

---

**Documento:** Escopo do Projeto  
**Projeto:** BANK Inteligente Auditoria e Prevenção de Fraudes  
**Equipe:** Grupo 5