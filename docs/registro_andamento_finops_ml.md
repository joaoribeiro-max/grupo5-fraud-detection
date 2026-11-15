# REGISTRO DE ANDAMENTO FINOPS/ML
## Projeto Integrador | Grupo 5 BANK Inteligente: Auditoria e Prevenção de Fraudes

**Responsável:** João Batista FinOps/ML  
**Data:** 15/11/2026  
**Status geral:** Desenvolvimento dos modelos de Machine Learning

---

## 1. Onde estamos no projeto?

Após concluir a análise exploratória, investigar possíveis vazamentos de informação (Data Leakage) e preparar os dados, concluímos nosso primeiro experimento de Machine Learning utilizando o algoritmo K-Nearest Neighbors (KNN).

Neste momento, estamos iniciando a segunda parte da modelagem: o desenvolvimento e treinamento do LightGBM.

Nosso objetivo é comparar os dois algoritmos e identificar qual apresenta melhor capacidade de detecção de fraudes.

## 2. Atividades já realizadas

### Análise Exploratória e preparação

- Análise da distribuição das transações legítimas e fraudulentas.
- Investigação de valores extremos pelo método IQR.
- Análise dos saldos zerados.
- Investigação de possíveis Data Leakages.
- Diagnóstico de Missing Values.
- Verificação de registros duplicados.
- Seleção preliminar das variáveis para modelagem.
- Separação temporal dos dados em treinamento, validação e teste.

### Preparação para Machine Learning

Foram realizadas as seguintes transformações:

- Tratamento de outliers por Capping.
- Criação de cinco faixas de valores (Binning).
- Feature Engineering com transformação logarítmica (`log_amount`).
- Normalização com StandardScaler.
- One-Hot Encoding das variáveis categóricas.
- Preparação de matrizes esparsas para o KNN.

### Separação temporal

| Conjunto | Steps | Transações | Fraudes |
|---|---:|---:|---:|
| Treinamento | 1–520 | 6.082.007 | 5.781 |
| Validação | 521–631 | 191.147 | 1.180 |
| Teste | 632–743 | 89.466 | 1.252 |

O conjunto de teste permanece reservado para a avaliação final.

---

## 3. Primeiro experimento KNN

O primeiro modelo foi treinado utilizando uma amostra de 63.591 transações, composta por 57.810 legítimas e 5.781 fraudulentas.

Configuração utilizada:

- Número de vizinhos: 5.
- Ponderação: distância.
- Métrica: euclidiana.
- Algoritmo de busca: KDTree.
- Features: 12.

### Resultados na validação

| Métrica | Resultado |
|---|---:|
| Precision | 0,0613 |
| Recall | 0,3492 |
| F1-score | 0,1044 |
| Average Precision | 0,0423 |
| ROC-AUC | 0,8325 |

Foram avaliados seis limiares de classificação, entre 0,05 e 0,50.

O melhor F1-score entre os limiares testados foi obtido com 0,50.

**Conclusão do experimento:** o KNN apresentou capacidade de discriminação entre as classes, mas demonstrou limitações na Precision e quantidade elevada de falsos positivos. Foi mantido como modelo de referência, ainda sem aprovação definitiva.

---

## 4. Etapa atual Desenvolvimento do LightGBM

**Estamos iniciando esta etapa em 15/11/2026.**

O objetivo é desenvolver o segundo modelo de Machine Learning utilizando LightGBM.

A estratégia inicial será:

1. Verificar a instalação e a versão da biblioteca LightGBM.
2. Preparar as features para o algoritmo.
3. Aproveitar as transformações e características desenvolvidas na preparação dos dados.
4. Considerar o forte desbalanceamento das classes utilizando ponderação adequada.
5. Treinar o LightGBM com os registros completos do conjunto de treinamento.
6. Avaliar o modelo utilizando o mesmo conjunto de validação empregado no KNN.

Diferentemente do KNN, o LightGBM não depende de normalização das escalas numéricas.

A utilização da estrutura Gold ML desenvolvida pela Engenharia de Dados também será considerada na integração, evitando duplicidade de trabalho.

---

## 5. Comparação entre os modelos

Após o treinamento do LightGBM, serão comparados os resultados de KNN e LightGBM utilizando:

- Precision.
- Recall.
- F1-score.
- PR-AUC.
- ROC-AUC.
- Matriz de confusão.
- Quantidade de falsos positivos e falsos negativos.

Também serão avaliados diferentes limiares de classificação, considerando os impactos operacionais dos erros.

---

## 6. Próximas entregas da frente FinOps/ML

| Ordem | Entrega | Situação |
|---|---|---|
| 1 | Análise Exploratória | Concluída |
| 2 | Investigação de Data Leakage | Consolidada |
| 3 | Preparação inicial dos dados | Realizada |
| 4 | Primeiro experimento KNN | Concluído |
| 5 | Treinamento LightGBM | Próxima atividade |
| 6 | Comparação dos modelos | Pendente |
| 7 | Estimativa de exposição financeira | Pendente |
| 8 | Desenvolvimento de função Python modular | Pendente |
| 9 | Integração com o agente de IA | Pendente |

---

## 7. Organização dos arquivos

**Notebook principal da modelagem:**

`notebooks/02_preparacao_e_modelagem.ipynb`

**Relatório do primeiro experimento:**

`docs/resultado_primeiro_experimento_knn.md`

**Relatório de andamento:**

`docs/registro_andamento_finops_ml.md`

---

## 8. Objetivo final

Entregar uma solução de Machine Learning capaz de identificar padrões de fraude, comparar diferentes algoritmos, avaliar seu desempenho e estimar a exposição financeira associada às transações fraudulentas.

A solução deverá possuir uma função Python modular e estar preparada para integração com a frente de Engenharia de IA.

**Responsável pela frente:** João Batista FinOps/ML  
**Projeto Integrador:** Grupo 5 BANK Inteligente | Auditoria e Prevenção de Fraudes