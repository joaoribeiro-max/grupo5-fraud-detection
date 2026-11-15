# REQUISITOS TÉCNICOS
## Grupo 5 — Cidade Inteligente: Auditoria e Prevenção de Fraudes

**Projeto:** Projeto Integrador  
**Cliente fictício:** Prefeitura de Cidade Conectada  
**Data de atualização:** 15/11/2026  
**Status:** Em desenvolvimento

---

## 1. Objetivo

Este documento apresenta os requisitos técnicos necessários para desenvolvimento, execução, integração e manutenção do protótipo Cidade Inteligente.

São descritas as tecnologias, ferramentas, linguagens, bibliotecas, estruturas de dados e condições técnicas necessárias para atender às funcionalidades previstas no projeto.

## 2. Arquitetura tecnológica

A solução utiliza uma arquitetura integrada, dividida em quatro componentes principais:

1. Engenharia de Dados.
2. Machine Learning e FinOps.
3. Business Intelligence.
4. Engenharia de Inteligência Artificial.

Os componentes deverão compartilhar dados e resultados por meio de interfaces e estruturas previamente definidas pela equipe.

## 3. Tecnologias e ferramentas

| Tecnologia | Aplicação no projeto |
|---|---|
| Databricks | Ambiente de processamento e desenvolvimento de dados |
| Delta Live Tables (DLT) | Construção e gerenciamento de pipelines |
| Unity Catalog | Organização e governança das tabelas |
| Python | Desenvolvimento dos processos de ML |
| SQL | Consulta, transformação e organização dos dados |
| VS Code | Ambiente local de desenvolvimento |
| Jupyter Notebook | Análise exploratória e experimentação |
| Git e GitHub | Versionamento e compartilhamento do código |
| Google ADK | Desenvolvimento do agente de Inteligência Artificial |
| Power BI | Desenvolvimento de visualizações e indicadores de negócio |

## 4. Requisitos técnicos — Engenharia de Dados

### RT-001 — Processamento de dados

A solução deverá utilizar Databricks para processar e organizar os dados financeiros.

### RT-002 — Arquitetura Medallion

Deverá ser implementada uma estrutura de dados organizada nas camadas:

- Bronze: dados de origem.
- Silver: dados tratados, padronizados e validados.
- Gold: dados refinados para consumo por Machine Learning e Business Intelligence.

### RT-003 — Armazenamento estruturado

As tabelas deverão utilizar formatos adequados ao processamento analítico, permitindo consultas e transformações eficientes.

### RT-004 — Controle de qualidade

A pipeline deverá possuir regras de validação para identificar dados inválidos, inconsistentes ou incompletos.

### RT-005 — Governança dos dados

A organização das tabelas e dos schemas deverá utilizar recursos do Unity Catalog.

## 5. Requisitos técnicos — Machine Learning e FinOps

### RT-006 — Linguagem de desenvolvimento

Os experimentos de Machine Learning deverão ser desenvolvidos utilizando Python.

### RT-007 — Bibliotecas de análise e preparação

O ambiente deverá disponibilizar bibliotecas como:

- Pandas: manipulação e análise de dados.
- NumPy: operações numéricas.
- Matplotlib: visualização de dados.
- Scikit-learn: pré-processamento, treinamento e avaliação dos modelos.
- SciPy: estruturas e operações com matrizes esparsas.
- LightGBM: treinamento do algoritmo baseado em Gradient Boosting.

### RT-008 — Modelos