# Projeto Integrador — Grupo 5
## Cidade Inteligente: Auditoria e Prevenção de Fraudes

![Status](https://img.shields.io/badge/Status-Em%20desenvolvimento-yellow)
![Python](https://img.shields.io/badge/Python-3.12-blue)
![Databricks](https://img.shields.io/badge/Databricks-Free%20Edition-red)
![Machine Learning](https://img.shields.io/badge/Machine%20Learning-Fraud%20Detection-purple)

## 1. Sobre o projeto

O Projeto Integrador do Grupo 5 tem como objetivo desenvolver uma solução inteligente voltada à auditoria e prevenção de fraudes em um cenário de Cidade Inteligente.

A proposta é utilizar Engenharia de Dados, Machine Learning, Inteligência Artificial e Business Intelligence para analisar transações financeiras, identificar possíveis comportamentos fraudulentos e fornecer informações que apoiem processos de auditoria e tomada de decisão.

O projeto utiliza como referência o dataset **PaySim**, um conjunto de dados sintético que simula operações financeiras de mobile money. Os resultados serão utilizados para demonstrar técnicas de detecção de fraudes em um cenário experimental.

## 2. Objetivos

- Desenvolver um fluxo de Engenharia de Dados para ingestão, organização e transformação dos dados.
- Realizar análise exploratória e preparação dos dados.
- Treinar e avaliar modelos de Machine Learning para classificação de possíveis fraudes.
- Estimar a exposição financeira associada às transações suspeitas, com premissas claramente documentadas.
- Integrar os resultados a um agente inteligente utilizando o Agent Development Kit (ADK).
- Desenvolver dashboards para acompanhamento de indicadores e resultados.
- Apresentar a solução como uma proposta de aplicação ao setor público.

## 3. Tecnologias utilizadas

| Tecnologia | Aplicação |
|---|---|
| Python | Processamento e desenvolvimento dos modelos |
| Pandas e NumPy | Manipulação e análise dos dados |
| Scikit-learn | Preparação e avaliação de modelos |
| LightGBM | Modelo de classificação |
| Databricks Free Edition | Ambiente de desenvolvimento e análise |
| Databricks AI/BI | Construção de dashboards |
| Git e GitHub | Versionamento e colaboração |
| Google Cloud Platform (GCP) | Arquitetura de referência proposta |
| Agent Development Kit (ADK) | Desenvolvimento do agente inteligente |
| VS Code | Desenvolvimento local |

## 4. Dataset

**PaySim — Synthetic Financial Dataset for Fraud Detection**

Fonte: [Kaggle — PaySim](https://www.kaggle.com/datasets/ealaxi/paysim1)

Características:
- Dados sintéticos de transações financeiras.
- Aproximadamente 6,36 milhões de registros.
- Variáveis relacionadas a operações, valores e saldos.
- Identificação de transações fraudulentas por meio da variável `isFraud`.

**Importante:** o PaySim é um dataset sintético. Portanto, os resultados representam experimentos realizados sobre dados simulados, não evidências de fraudes reais em operações da Prefeitura.

## 5. Arquitetura proposta

A solução será organizada conceitualmente em camadas:

- **Bronze:** ingestão e armazenamento dos dados originais.
- **Silver:** limpeza, padronização e tratamento dos dados.
- **Gold:** dados preparados para análises, indicadores e consumo pelos modelos.

Os resultados do processamento alimentarão os componentes de Machine Learning, o agente inteligente e os dashboards.

A arquitetura de referência considera serviços da Google Cloud Platform (GCP), enquanto o MVP será desenvolvido utilizando os recursos disponíveis no ambiente Databricks e ferramentas locais.

## 6. Modelos de Machine Learning

A frente de FinOps será responsável pelo desenvolvimento e avaliação de modelos para classificação de transações suspeitas.

Modelos previstos:
- K-Nearest Neighbors (KNN).
- LightGBM.

Métricas de avaliação previstas:
- Precision.
- Recall.
- F1-score.
- PR-AUC.
- ROC-AUC.
- Matriz de confusão.

Devido ao forte desbalanceamento entre transações legítimas e fraudulentas, a avaliação dará atenção especial à capacidade de identificar fraudes sem gerar um volume excessivo de falsos positivos.

## 7. Agente de Inteligência Artificial

Será desenvolvido um agente inteligente utilizando o Agent Development Kit (ADK).

A proposta contempla:
- Integração com o modelo de detecção de fraudes.
- Ferramenta de consulta SQL.
- Recuperação de informações por busca lexical.
- Function Calling para execução das ferramentas.
- Interface demonstrativa por meio do ADK Web.

## 8. Business Intelligence

Será desenvolvido um dashboard no Databricks AI/BI para apresentar indicadores relevantes, incluindo:

- Volume de transações analisadas.
- Quantidade de fraudes identificadas.
- Valores associados às transações fraudulentas.
- Indicadores de desempenho dos modelos.
- Estimativa de exposição financeira.

Os indicadores serão apresentados com distinção entre valores observados no dataset e estimativas produzidas pelo modelo.

## 9. Equipe e responsabilidades

| Integrante | Frente de atuação |
|---|---|
| João Batista | FinOps e Machine Learning |
| Rodrigo | Engenharia de Dados |
| Rafael | Engenharia de Inteligência Artificial |
| Raphael Aires | Business Intelligence |
| Ramon Carlos | TechSales |

As atividades serão desenvolvidas de forma colaborativa, com integração entre as diferentes frentes do projeto.

## 10. Estrutura do repositório

```text
grupo5-fraud-detection/
│
├── README.md
├── .gitignore
├── data/
│   ├── bronze/
│   ├── silver/
│   └── gold/
├── notebooks/
├── src/
│   ├── data_engineering/
│   ├── finops_ml/
│   └── ai_agent/
├── dashboard/
├── models/
├── reports/
└── docs/
    ├── arquitetura/
    ├── requisitos/
    └── reunioes/
```

A estrutura será ampliada conforme a evolução das entregas. Os dados originais não serão versionados no GitHub.

## 11. Organização e colaboração

O projeto utiliza Git e GitHub para controle de versão e colaboração entre os integrantes.

Boas práticas previstas:
- Cada integrante trabalha em sua própria branch.
- Alterações são registradas por commits.
- A integração das funcionalidades ocorre por Pull Requests.
- A branch `main` representa a versão principal do projeto.
- A documentação deve acompanhar a evolução das entregas.

## 12. Status do projeto

**Em desenvolvimento.**

As atividades estão sendo realizadas de forma incremental, respeitando as responsabilidades de cada frente e os requisitos definidos para o Projeto Integrador do Academy da IPNET.

---

**Grupo 5 — Projeto Integrador**  
Cidade Inteligente | Auditoria e Prevenção de Fraudes