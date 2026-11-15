# COMPARATIVO DE DESEMPENHO — KNN vs LIGHTGBM

## Projeto Integrador | Grupo 5 — Cidade Inteligente: Auditoria e Prevenção de Fraudes

| Informação | Descrição |
|---|---|
| Projeto | Cidade Inteligente — Auditoria e Prevenção de Fraudes |
| Frente | FinOps / Machine Learning |
| Responsável | João Batista |
| Data | 15/11/2026 |
| Base de dados | PaySim — Synthetic Financial Dataset |
| Status | Comparação realizada na validação |

---

## 1. Objetivo

Este documento apresenta a comparação dos modelos K-Nearest Neighbors (KNN) e LightGBM, desenvolvidos para identificar padrões associados a transações financeiras fraudulentas.

O objetivo é avaliar o desempenho dos dois algoritmos, considerando o forte desbalanceamento das classes e a necessidade de equilibrar a identificação de fraudes com a quantidade de falsos positivos gerados.

Os experimentos foram realizados utilizando a mesma divisão temporal dos dados e o mesmo conjunto de validação.

## 2. Estratégia de preparação dos dados

Os dados foram separados temporalmente, respeitando a sequência dos eventos da simulação.

| Conjunto | Intervalo de step | Total de transações | Fraudes |
|---|---:|---:|---:|
| Treinamento | 1–520 | 6.082.007 | 5.781 |
| Validação | 521–631 | 191.147 | 1.180 |
| Teste | 632–743 | 89.466 | 1.252 |

O conjunto de validação foi utilizado para acompanhar o desempenho e selecionar os limiares de classificação.

O conjunto de teste permaneceu reservado para a avaliação final independente.

### 2.1 Estratégia utilizada no KNN

O KNN foi treinado utilizando uma amostra controlada para reduzir o custo computacional.

| Indicador | Resultado |
|---|---:|
| Total de registros | 63.591 |
| Transações legítimas | 57.810 |
| Transações fraudulentas | 5.781 |
| Proporção | 10 legítimas para 1 fraudulenta |
| Features | 12 |

O processamento contemplou:

- Tratamento de outliers por Capping.
- Transformação logarítmica da variável `amount`.
- Normalização com StandardScaler.
- One-Hot Encoding para tipo de transação.
- One-Hot Encoding para faixas de valores.
- Utilização de matrizes esparsas para otimizar o consumo de memória.

### 2.2 Estratégia utilizada no LightGBM

O LightGBM foi treinado utilizando todos os registros disponíveis no conjunto de treinamento.

Foram utilizadas quatro features:

- `amount`
- `type`
- `destino_eh_comercio`
- `faixa_valor`

O processamento contemplou Capping, Binning e representação categórica nativa do Pandas.

Foram avaliadas três estratégias para lidar com o desbalanceamento:

| Experimento | Peso da classe fraudulenta |
|---|---:|
| Sem ponderação | 1,00 |
| Peso intermediário | 32,42 |
| Peso integral | 1.051,07 |

A configuração sem ponderação apresentou os melhores resultados de Average Precision e ROC-AUC entre os três experimentos.

---

## 3. Configurações dos modelos

### 3.1 KNN

| Parâmetro | Configuração |
|---|---|
| Algoritmo | K-Nearest Neighbors |
| Número de vizinhos | 5 |
| Ponderação | Distance |
| Métrica | Euclidiana |
| Busca | KDTree |
| Features | 12 |
| Estratégia de treinamento | Amostragem 10:1 |

### 3.2 LightGBM

| Parâmetro | Configuração |
|---|---|
| Algoritmo | LightGBM |
| Objective | Binary |
| Número máximo de estimadores | 1.000 |
| Learning rate | 0,05 |
| Num leaves | 31 |
| Max depth | -1 |
| Min child samples | 100 |
| Colsample by tree | 0,8 |
| Reg_lambda | 1,0 |
| Random state | 42 |
| Estratégia principal | Sem ponderação |

O modelo LightGBM com peso integral apresentou excesso de falsos positivos. A configuração sem ponderação foi mantida como principal candidata para a comparação.

---

## 4. Resultados dos modelos na validação

Os dois modelos tiveram seus limiares selecionados utilizando a maximização do F1-score na validação.

### 4.1 Comparação geral

| Métrica | KNN | LightGBM sem ponderação |
|---|---:|---:|
| Limiar selecionado | 0,5998 | 0,0125 |
| Precision | 0,0727 | 0,2640 |
| Recall | 0,3203 | 0,2322 |
| F1-score | 0,1185 | 0,2471 |
| Average Precision | 0,0423 | 0,1082 |
| ROC-AUC | 0,8325 | 0,9172 |

### 4.2 Interpretação dos resultados

O KNN apresentou Recall de 32,03%, identificando 378 transações fraudulentas na validação.

Entretanto, sua Precision foi de 7,27%, indicando uma quantidade elevada de falsos positivos.

O LightGBM sem ponderação apresentou Precision de 26,40% e Recall de 23,22%, demonstrando maior precisão nos alertas, embora tenha identificado menos fraudes do que o KNN nesse ponto de operação.

O F1-score do LightGBM foi de 0,2471, enquanto o KNN apresentou 0,1185.

O Average Precision também foi superior no LightGBM, passando de 0,0423 no KNN para 0,1082.

O ROC-AUC apresentou resultado de 0,9172 para o LightGBM e 0,8325 para o KNN.

---

## 5. Análise das matrizes de confusão

### 5.1 KNN

Configuração: limiar 0,5998.

| Resultado | Quantidade |
|---|---:|
| Verdadeiros positivos | 378 |
| Falsos positivos | 4.820 |
| Verdadeiros negativos | 185.147 |
| Falsos negativos | 802 |
| Total de alertas | 5.198 |

O KNN conseguiu identificar uma quantidade maior de fraudes, mas produziu mais falsos positivos.

### 5.2 LightGBM sem ponderação

Configuração: limiar 0,0125.

| Resultado | Quantidade |
|---|---:|
| Verdadeiros positivos | 274 |
| Falsos positivos | 764 |
| Verdadeiros negativos | 189.203 |
| Falsos negativos | 906 |
| Total de alertas | 1.038 |

O LightGBM apresentou menor quantidade de alertas incorretos e maior Precision.

---

## 6. Comparação operacional

A comparação permite observar dois comportamentos diferentes.

**KNN:**

- Identificou 378 fraudes.
- Gerou 4.820 falsos positivos.
- Produziu 5.198 alertas.
- Apresentou maior Recall.

**LightGBM:**

- Identificou 274 fraudes.
- Gerou 764 falsos positivos.
- Produziu 1.038 alertas.
- Apresentou maior Precision.

Na configuração avaliada, o LightGBM gerou 4.160 alertas a menos que o KNN e apresentou F1-score aproximadamente 2,09 vezes superior.

Isso demonstra uma vantagem do LightGBM em relação ao equilíbrio entre Precision e Recall, além de uma redução significativa do volume de alertas incorretos.

Entretanto, o KNN identificou 104 fraudes adicionais na configuração selecionada.

A escolha operacional deverá considerar a capacidade de investigação da equipe, o custo dos falsos positivos e o impacto de não identificar determinadas fraudes.

---

## 7. Decisão técnica preliminar

Com base nos resultados observados na validação, o LightGBM sem ponderação foi selecionado como principal candidato para a próxima fase de avaliação.

O KNN será mantido como modelo de referência e comparação.

| Modelo | Decisão |
|---|---|
| KNN | Manter como referência comparativa |
| LightGBM sem ponderação | Principal candidato |
| LightGBM com peso intermediário | Alternativa experimental |
| LightGBM com peso integral | Não recomendado nos resultados atuais |

A escolha ainda não representa a aprovação definitiva de um modelo para utilização operacional.

---

## 8. Limitações e cuidados metodológicos

A comparação deve ser interpretada considerando algumas diferenças entre os experimentos.

1. O KNN utilizou uma amostra de treinamento com proporção 10:1, enquanto o LightGBM sem ponderação utilizou todos os registros do treinamento.

2. Os modelos utilizaram quantidades diferentes de features: 12 para KNN e quatro para LightGBM.

3. Os limiares foram selecionados utilizando o próprio conjunto de validação. Portanto, as métricas no limiar selecionado são resultados de otimização e não representam uma avaliação independente.

4. As probabilidades dos modelos não devem ser interpretadas automaticamente como probabilidades reais calibradas de fraude.

5. A divisão temporal identificou mudanças na frequência de fraudes entre os períodos, o que deverá ser considerado na interpretação dos resultados.

6. O conjunto de teste ainda não foi utilizado para a escolha definitiva dos parâmetros e limiares.

---

## 9. Próximas atividades

As próximas atividades da frente FinOps/ML são:

1. Consolidar as configurações candidatas dos dois modelos.
2. Revisar os resultados e os limiares selecionados na validação.
3. Congelar os modelos e suas configurações antes da avaliação final.
4. Executar a avaliação independente no conjunto de teste.
5. Comparar os resultados finais utilizando Precision, Recall, F1-score, PR-AUC, ROC-AUC e matriz de confusão.
6. Desenvolver a função Python modular para execução das previsões.
7. Definir a metodologia de estimativa de exposição financeira.
8. Preparar a integração dos resultados com a frente de Engenharia de IA.

---

## 10. Conclusão

Os experimentos demonstraram que KNN e LightGBM apresentam comportamentos diferentes na identificação de transações fraudulentas.

O KNN apresentou maior Recall no ponto de operação selecionado, enquanto o LightGBM apresentou maior Precision, Average Precision, ROC-AUC e F1-score.

Com base nos resultados da validação, o LightGBM sem ponderação foi escolhido como principal candidato para a avaliação final.

A decisão definitiva dependerá do desempenho observado no conjunto de teste, que permanece reservado para essa finalidade.

**Observação:** o projeto utiliza o dataset sintético PaySim. Os valores financeiros apresentados nas análises representam transações simuladas e não devem ser interpretados como prejuízos reais, dinheiro recuperado ou perdas efetivamente evitadas.

---

**Responsável:** João Batista — FinOps/ML  
**Projeto:** Grupo 5 — Cidade Inteligente: Auditoria e Prevenção de Fraudes  
**Data:** 15/11/2026  
**Status:** Comparação na validação concluída — avaliação final pendente