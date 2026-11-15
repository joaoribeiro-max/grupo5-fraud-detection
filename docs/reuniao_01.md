# REGISTRO DE ALINHAMENTO INICIAL — REUNIÃO 01
## Grupo 5 — Cidade Inteligente: Auditoria e Prevenção de Fraudes

**Projeto:** Projeto Integrador  
**Cliente fictício:** Prefeitura de Cidade Conectada  
**Data da reunião:** Não registrada na documentação disponível  
**Equipe:** Grupo 5  
**Tipo de registro:** Alinhamento inicial do projeto  
**Status:** Registro preliminar para validação da equipe

---

## 1. Objetivo do alinhamento

Registrar o contexto inicial do Projeto Integrador, a proposta de solução, a organização das frentes de trabalho e as principais necessidades de integração entre os integrantes do Grupo 5.

## 2. Contextualização do projeto

O Grupo 5 está desenvolvendo uma solução denominada Cidade Inteligente — Auditoria e Prevenção de Fraudes.

A proposta consiste em utilizar Engenharia de Dados, Machine Learning, Business Intelligence e Inteligência Artificial para analisar transações financeiras, identificar padrões associados a possíveis fraudes e disponibilizar informações para apoiar processos de auditoria.

O dataset PaySim foi definido como base para os experimentos, por conter transações financeiras sintéticas classificadas como legítimas e fraudulentas.

## 3. Organização das frentes de trabalho

A organização do projeto contempla as seguintes responsabilidades:

| Integrante | Frente | Responsabilidade |
|---|---|---|
| Rodrigo | Engenharia de Dados | Construção das pipelines e camadas de dados |
| João Batista | FinOps / ML | Preparação dos dados, treinamento e avaliação dos modelos |
| Rafael | Engenharia de IA | Desenvolvimento do agente utilizando Google ADK |
| Raphael Aires | Business Intelligence | Construção dos dashboards e indicadores |
| Ramon | TechSales | Proposta de valor e apresentação da solução |

A integração entre as frentes deverá ocorrer por meio do compartilhamento de dados, funcionalidades, resultados e documentação técnica.

## 4. Proposta de arquitetura

A solução considera uma arquitetura organizada em componentes:

**Engenharia de Dados**
- Camada Bronze: recepção dos dados originais.
- Camada Silver: limpeza, padronização e organização.
- Camada Gold: disponibilização de dados para Machine Learning e Business Intelligence.

**Machine Learning**
- Análise exploratória.
- Preparação dos dados.
- Desenvolvimento dos modelos KNN e LightGBM.
- Avaliação e comparação dos resultados.
- Estimativa de exposição financeira.

**Business Intelligence**
- Construção de dashboards.
- Indicadores de transações e fraudes.
- Análises financeiras e temporais.

**Engenharia de Inteligência Artificial**
- Desenvolvimento do agente com Google ADK.
- Integração com consultas SQL.
- Busca lexical BM25.
- Integração com recursos de Machine Learning.

## 5. Tecnologias previstas

| Tecnologia | Finalidade |
|---|---|
| Databricks | Processamento e organização de dados |
| Delta Live Tables | Construção das pipelines |
| Unity Catalog | Organização e governança |
| Python | Desenvolvimento dos modelos |
| SQL | Consultas e transformações |
| Scikit-learn | Preparação e treinamento de modelos |
| LightGBM | Modelo de classificação |
| Google ADK | Desenvolvimento do agente de IA |
| Power BI | Visualização de indicadores |
| GitHub | Versionamento e colaboração |

## 6. Principais necessidades de integração

Durante a organização do projeto, foram identificadas as seguintes necessidades de integração:

1. Disponibilização das tabelas tratadas pela Engenharia de Dados.
2. Alinhamento das features utilizadas pelos modelos de Machine Learning.
3. Disponibilização dos resultados dos modelos para a Engenharia de IA.
4. Alinhamento dos indicadores utilizados nos dashboards.
5. Integração das diferentes entregas para a demonstração final.
6. Manutenção da documentação e do código compartilhados no GitHub.

## 7. Plano geral de desenvolvimento

As atividades estão organizadas em uma sequência de desenvolvimento:

| Fase | Atividade |
|---|---|
| 1 | Organização e entendimento dos dados |
| 2 | Construção das camadas de dados |
| 3 | Preparação e análise exploratória |
| 4 | Desenvolvimento dos modelos de ML |
| 5 | Construção do agente de IA |
| 6 | Desenvolvimento dos dashboards |
| 7 | Integração dos componentes |
| 8 | Validação e apresentação da solução |

As fases podem ocorrer parcialmente em paralelo, conforme a disponibilidade das entregas entre as frentes.

## 8. Pontos que precisam de validação pelo grupo

Para transformar este registro em ata oficial da primeira reunião, precisam ser confirmados:

- Data e horário da reunião.
- Participantes efetivamente presentes.
- Pautas discutidas.
- Decisões formalmente aprovadas.
- Responsáveis e prazos acordados.
- Eventuais pendências identificadas na reunião.

## 9. Considerações finais

Este registro consolida o contexto inicial, a organização das frentes e a proposta técnica do Projeto Integrador.

A documentação busca facilitar o acompanhamento das atividades e a integração entre os integrantes, mantendo uma visão compartilhada dos objetivos e entregas.

O conteúdo deverá ser revisado e validado pela equipe antes de ser considerado a ata oficial da primeira reunião.

---

**Projeto:** Cidade Inteligente — Auditoria e Prevenção de Fraudes  
**Equipe:** Grupo 5  
**Documento:** Registro de Alinhamento Inicial — Reunião 01