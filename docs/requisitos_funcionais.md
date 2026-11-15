# REQUISITOS FUNCIONAIS
## Grupo 5 Cidade Inteligente: Auditoria e Prevenção de Fraudes

**Projeto:** Projeto Integrador  
**Cliente fictício:** Prefeitura de Cidade Conectada  
**Data de atualização:** 15/11/2026  
**Status:** Em desenvolvimento

---

## 1. Objetivo

Este documento apresenta os requisitos funcionais da solução Cidade Inteligente, descrevendo as funcionalidades que o sistema deverá disponibilizar para processar transações, identificar padrões suspeitos, apresentar indicadores e apoiar auditorias financeiras.

Os requisitos estão organizados de acordo com as frentes de Engenharia de Dados, Machine Learning, Business Intelligence e Engenharia de Inteligência Artificial.

## 2. Requisitos Funcionais — Engenharia de Dados

### RF-001 — Ingestão de dados
O sistema deverá permitir a ingestão do dataset financeiro PaySim para processamento e análise.

**Critério de aceite:** os dados deverão estar disponíveis na camada Bronze do ambiente Databricks.

### RF-002 — Tratamento dos dados
O sistema deverá executar processos de limpeza, padronização e conversão dos tipos de dados.

**Critério de aceite:** os registros deverão estar estruturados e preparados para consumo pelas camadas posteriores.

### RF-003 — Organização em arquitetura Medallion
O sistema deverá organizar os dados nas camadas Bronze, Silver e Gold.

**Critério de aceite:** as tabelas deverão estar organizadas conforme suas finalidades de armazenamento, tratamento e consumo.

### RF-004 — Validação da qualidade dos dados
O sistema deverá aplicar regras de qualidade para identificar registros inválidos ou inconsistentes.

**Critério de aceite:** as regras de validação deverão estar documentadas e disponíveis na pipeline.

## 3. Requisitos Funcionais — Machine Learning e FinOps

### RF-005 — Análise exploratória
O sistema deverá permitir a análise estatística e exploratória das transações financeiras.

**Critério de aceite:** deverão ser disponibilizadas análises sobre distribuição das classes, valores, saldos, tipos de transação e comportamento temporal.

### RF-006 — Preparação dos dados para Machine Learning
O sistema deverá disponibilizar recursos para tratamento de valores extremos, valores ausentes, codificação categórica, normalização e criação de novas variáveis.

**Critério de aceite:** os conjuntos de dados deverão estar preparados para o treinamento dos algoritmos selecionados.

### RF-007 — Identificação de transações fraudulentas
O sistema deverá utilizar modelos de Machine Learning para classificar transações como legítimas ou potencialmente fraudulentas.

**Critério de aceite:** os modelos deverão produzir previsões para avaliação e comparação.

### RF-008 — Treinamento e comparação de modelos
O sistema deverá permitir o treinamento e a avaliação dos algoritmos KNN e LightGBM.

**Critério de aceite:** deverão ser apresentados resultados comparativos utilizando métricas adequadas para dados desbalanceados.

### RF-009 — Avaliação dos modelos
O sistema deverá disponibilizar métricas de desempenho dos modelos.

**Critério de aceite:** a avaliação deverá contemplar Precision, Recall, F1-score, PR-AUC, ROC-AUC e matriz de confusão.

### RF-010 — Estimativa de exposição financeira
O sistema deverá permitir estimar os valores financeiros associados às transações classificadas como fraudulentas.

**Critério de aceite:** a estimativa deverá apresentar suas premissas e ser identificada como exposição financeira estimada, considerando que o PaySim é sintético.

### RF-011 — Execução modular das previsões
O sistema deverá disponibilizar uma função Python modular para executar as previsões do modelo selecionado.

**Critério de aceite:** a função deverá receber os dados de entrada, executar o processamento necessário e retornar as classificações e informações previstas.

## 4. Requisitos Funcionais — Business Intelligence

### RF-012 — Visualização de indicadores
O sistema deverá disponibilizar dashboards para acompanhamento das transações e dos indicadores relacionados à fraude.

**Critério de aceite:** os painéis deverão apresentar informações organizadas e compreensíveis para análise gerencial.

### RF-013 — Análise por dimensões
O sistema deverá permitir a análise dos indicadores por tipo de transação, período e demais dimensões disponibilizadas na camada Gold BI.

**Critério de aceite:** os usuários deverão conseguir explorar os indicadores por meio dos filtros e agrupamentos disponíveis.

### RF-014 — Acompanhamento de indicadores financeiros
O sistema deverá apresentar métricas relacionadas ao volume de transações, valores movimentados e quantidade de operações fraudulentas identificadas.

**Critério de aceite:** os indicadores deverão utilizar as métricas disponibilizadas pela camada Gold BI, com cálculos consistentes.

## 5. Requisitos Funcionais — Engenharia de Inteligência Artificial

### RF-015 — Interação com agente de Inteligência Artificial
O sistema deverá disponibilizar um agente de IA para apoiar consultas e análises relacionadas aos dados do projeto.

**Critério de aceite:** o agente deverá receber perguntas dos usuários e responder utilizando as ferramentas e fontes de dados integradas.

### RF-016 — Consulta estruturada de dados
O agente deverá possuir integração com ferramenta de consulta SQL para recuperar informações estruturadas.

**Critério de aceite:** deverá ser possível realizar consultas controladas às informações disponíveis.

### RF-017 — Busca na base de conhecimento
O agente deverá disponibilizar recurso de busca lexical para localizar informações relevantes na base de conhecimento do projeto.

**Critério de aceite:** as consultas deverão retornar resultados relacionados ao conteúdo disponível na base documental.

### RF-018 — Integração com Machine Learning
O agente deverá permitir integração com os recursos de Machine Learning para apoiar consultas sobre classificações e resultados dos modelos.

**Critério de aceite:** deverá ser demonstrada a comunicação entre o agente e os recursos de ML disponibilizados pelo projeto.

## 6. Regras gerais de negócio

- As transações deverão ser classificadas conforme as regras e os modelos definidos pelo projeto.
- A classificação preditiva deverá ser diferenciada da classificação original presente no dataset.
- Os resultados dos modelos deverão ser acompanhados por métricas de desempenho.
- A análise deverá considerar o forte desbalanceamento entre transações legítimas e fraudulentas.
- Os indicadores financeiros deverão apresentar suas premissas de cálculo.
- Os dados do PaySim deverão ser tratados como dados sintéticos.
- A solução não deverá apresentar estimativas financeiras como prejuízos reais ou valores efetivamente recuperados.

## 7. Considerações finais

Os requisitos funcionais representam as funcionalidades previstas para a solução Cidade Inteligente.

A implementação ocorrerá de forma integrada entre as frentes de Engenharia de Dados, FinOps/Machine Learning, Business Intelligence e Engenharia de Inteligência Artificial.

Os requisitos poderão ser atualizados durante o desenvolvimento, conforme as validações técnicas e as necessidades de integração entre os componentes.

---

**Documento:** Requisitos Funcionais  
**Projeto:** BANK Inteligente — Auditoria e Prevenção de Fraudes  
**Equipe:** Grupo 5