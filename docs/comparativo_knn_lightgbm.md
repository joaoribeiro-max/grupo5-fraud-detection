# COMPARATIVO DE DESEMPENHO — KNN vs LIGHTGBM

## Projeto Integrador | Grupo 5 — Cidade Inteligente: Auditoria e Prevenção de Fraudes

| Informação | Descrição |
|---|---|
| Projeto | Cidade Inteligente — Auditoria e Prevenção de Fraudes |
| Frente | FinOps / Machine Learning |
| Responsável | João Batista |
| Data | 15/11/2026 |
| Base de dados | PaySim — Synthetic Financial Dataset |
| Status | Avaliação na validação e no conjunto de teste concluída |

---

## 1. Objetivo

Este documento apresenta a comparação dos modelos K-Nearest Neighbors (KNN) e LightGBM, desenvolvidos para identificar padrões associados a transações financeiras fraudulentas.

O objetivo é avaliar o desempenho dos dois algoritmos, considerando o forte desbalanceamento das classes e a necessidade de equilibrar a identificação de fraudes com a quantidade de falsos positivos gerados.

Os experimentos utilizaram uma divisão temporal dos dados. A validação foi utilizada para selecionar os limiares de classificação; após a definição das configurações, o conjunto de teste reservado foi utilizado para a avaliação final independente.

## 2. Estratégia de preparação dos dados

Os dados foram separados temporalmente, respeitando a sequência dos eventos da simulação.

| Conjunto | Intervalo de step | Total de transações | Fraudes | Taxa de fraude |
|---|---:|---:|---:|---:|
| Treinamento | 1–520 | 6.082.007 | 5.781 | 0,0951% |
| Validação | 521–631 | 191.147 | 1.180 | 0,6173% |
| Teste | 632–743 | 89.466 | 1.252 | 1,3994% |

O conjunto de validação foi utilizado para acompanhar o desempenho e selecionar os limiares de classificação. O conjunto de teste permaneceu reservado para a avaliação final independente.

A taxa de fraude aumenta entre os períodos de treinamento, validação e teste. Na análise exploratória também foi identificado um padrão temporal extremo no fim da simulação: entre os steps 719 e 743 foram observadas 296 transações, todas classificadas como fraudulentas. Esse comportamento específico do PaySim deve ser considerado na interpretação dos resultados de teste.

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

A configuração sem ponderação apresentou os melhores resultados de Average Precision e ROC-AUC entre os três experimentos e foi selecionada como candidata principal para a avaliação final.

---

## 3. Configurações dos modelos

### 3.1 KNN

| Parâmetro | Configuração |
|---|---|
| Algoritmo | K-Nearest Neighbors |
| Número de vizinhos | 5 |
| Ponderação | Distance |
| Métrica | Euclidiana (Minkowski, p=2) |
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

O modelo LightGBM com peso integral apresentou excesso de falsos positivos nos experimentos. A configuração sem ponderação foi mantida como principal candidata para a comparação final.

---

## 4. Resultados dos modelos na validação

Os limiares dos dois modelos foram selecionados utilizando a maximização do F1-score na validação. Os resultados desta seção são mantidos como histórico do processo de seleção, não como resultado final.

### 4.1 Comparação geral na validação

| Métrica | KNN | LightGBM sem ponderação |
|---|---:|---:|
| Limiar selecionado | 0,599825590743 | 0,012455002510 |
| Precision | 0,0727 | 0,2640 |
| Recall | 0,3203 | 0,2322 |
| F1-score | 0,1185 | 0,2471 |
| Average Precision | 0,0423 | 0,1082 |
| ROC-AUC | 0,8325 | 0,9172 |

### 4.2 Interpretação dos resultados na validação

O KNN apresentou Recall de 32,03%, identificando 378 transações fraudulentas na validação. Entretanto, sua Precision foi de 7,27%, indicando uma quantidade elevada de falsos positivos.

O LightGBM sem ponderação apresentou Precision de 26,40% e Recall de 23,22%, demonstrando maior precisão nos alertas, embora tenha identificado menos fraudes do que o KNN nesse ponto de operação.

O F1-score do LightGBM foi de 0,2471, enquanto o KNN apresentou 0,1185. O Average Precision também foi superior no LightGBM: 0,1082 contra 0,0423. O ROC-AUC foi de 0,9172 para o LightGBM e 0,8325 para o KNN.

### 4.3 Matrizes de confusão na validação

**KNN — limiar selecionado na validação**

| Resultado | Quantidade |
|---|---:|
| Verdadeiros positivos | 378 |
| Falsos positivos | 4.820 |
| Verdadeiros negativos | 185.147 |
| Falsos negativos | 802 |
| Total de alertas | 5.198 |

**LightGBM sem ponderação — limiar selecionado na validação**

| Resultado | Quantidade |
|---|---:|
| Verdadeiros positivos | 274 |
| Falsos positivos | 764 |
| Verdadeiros negativos | 189.203 |
| Falsos negativos | 906 |
| Total de alertas | 1.038 |

---

## 5. Avaliação final no conjunto de teste

Após a seleção dos limiares na validação, os modelos foram avaliados no conjunto de teste reservado. Os limiares foram mantidos; não foram reajustados com base nos resultados do teste.

### 5.1 KNN no teste

O KNN foi avaliado com o limiar selecionado na validação, mantendo sua configuração e as 12 features utilizadas no treinamento.

**Limiar aplicado:** `0.5998255907428848`.

| Métrica | Resultado |
|---|---:|
| Precision | 0,1376 |
| Recall | 0,3187 |
| F1-score | 0,1922 |
| Average Precision | 0,0828 |
| ROC-AUC | 0,8226 |
| Verdadeiros positivos | 399 |
| Falsos positivos | 2.501 |
| Verdadeiros negativos | 85.713 |
| Falsos negativos | 853 |
| Total de alertas | 2.900 |

**Matriz de confusão — KNN no teste**

| Resultado real | Prevista legítima | Prevista fraudulenta |
|---|---:|---:|
| Legítima | 85.713 | 2.501 |
| Fraudulenta | 853 | 399 |

O KNN identificou 399 das 1.252 fraudes existentes no teste. Seu Recall foi superior ao do LightGBM, mas o modelo gerou 2.501 falsos positivos.

### 5.2 LightGBM sem ponderação no teste

O LightGBM sem ponderação foi avaliado com o limiar original selecionado na validação, sem recalibração ou otimização no conjunto de teste.

**Limiar aplicado:** `0.012455002510276548`.

| Métrica | Resultado |
|---|---:|
| Precision | 0,3431 |
| Recall | 0,2236 |
| F1-score | 0,2708 |
| Average Precision | 0,1671 |
| ROC-AUC | 0,9124 |
| Verdadeiros positivos | 280 |
| Falsos positivos | 536 |
| Verdadeiros negativos | 87.678 |
| Falsos negativos | 972 |
| Total de alertas | 816 |

**Matriz de confusão — LightGBM no teste**

| Resultado real | Prevista legítima | Prevista fraudulenta |
|---|---:|---:|
| Legítima | 87.678 | 536 |
| Fraudulenta | 972 | 280 |

O LightGBM identificou 280 das 1.252 fraudes existentes no teste. Apresentou maior Precision e F1-score, além de menor quantidade de falsos positivos, em comparação ao KNN.

### 5.3 Observação sobre o limiar e as probabilidades do LightGBM

Durante a avaliação, foi inicialmente utilizado o limiar arredondado `0,0125`. Esse valor ficou ligeiramente acima da maior probabilidade observada no teste (`0,012455002510276548`), resultando em zero alertas.

A avaliação foi corrigida com o valor original, sem arredondamento, recuperado da otimização realizada na validação. Como a regra de classificação utiliza `probabilidade >= limiar`, os registros com probabilidade igual ao limiar foram sinalizados.

No teste, a maior probabilidade produzida pelo LightGBM foi exatamente igual ao limiar aplicado. Assim, os 816 alertas correspondem aos registros que atingiram esse valor máximo. Esse comportamento, juntamente com a concentração das probabilidades em valores baixos, é uma limitação importante para interpretar a operação do modelo e deve ser investigado em etapas futuras. O limiar, entretanto, foi preservado conforme selecionado na validação.

---

## 6. Comparação final dos modelos no teste

| Métrica | KNN | LightGBM sem ponderação |
|---|---:|---:|
| Limiar aplicado | 0,599825590743 | 0,012455002510 |
| Precision | 0,1376 | **0,3431** |
| Recall | **0,3187** | 0,2236 |
| F1-score | 0,1922 | **0,2708** |
| Average Precision | 0,0828 | **0,1671** |
| ROC-AUC | 0,8226 | **0,9124** |
| Verdadeiros positivos | **399** | 280 |
| Falsos positivos | 2.501 | **536** |
| Verdadeiros negativos | 85.713 | **87.678** |
| Falsos negativos | **853** | 972 |
| Total de alertas | 2.900 | **816** |

### 6.1 Interpretação operacional no teste

Os modelos apresentaram comportamentos diferentes:

**KNN:**

- Identificou 399 fraudes.
- Gerou 2.501 falsos positivos.
- Produziu 2.900 alertas.
- Apresentou maior Recall: 31,87%.

**LightGBM sem ponderação:**

- Identificou 280 fraudes.
- Gerou 536 falsos positivos.
- Produziu 816 alertas.
- Apresentou maior Precision: 34,31%.
- Apresentou maior F1-score: 27,08%.

Na configuração avaliada, o LightGBM gerou 2.084 alertas a menos que o KNN, uma redução aproximada de 71,9%. Também produziu 1.965 falsos positivos a menos.

Por outro lado, o KNN identificou 119 fraudes adicionais e apresentou Recall 9,51 pontos percentuais superior.

Portanto, o LightGBM apresentou melhor equilíbrio entre Precision e Recall segundo o F1-score, enquanto o KNN priorizou maior cobertura de fraudes no ponto de operação selecionado.

---

## 7. Decisão técnica

Com base nos resultados observados no conjunto de teste, o **LightGBM sem ponderação foi selecionado como principal candidato técnico** para a continuidade do projeto.

A decisão considera:

- Maior Precision: 34,31% contra 13,76% do KNN.
- Maior F1-score: 27,08% contra 19,22%.
- Maior Average Precision: 16,71% contra 8,28%.
- Maior ROC-AUC: 91,24% contra 82,26%.
- Menor volume de falsos positivos: 536 contra 2.501.
- Menor quantidade de alertas: 816 contra 2.900.

O KNN será mantido como referência comparativa, especialmente por apresentar Recall superior e identificar mais fraudes no limiar escolhido.

| Modelo | Decisão |
|---|---|
| KNN | Manter como referência comparativa |
| LightGBM sem ponderação | Principal candidato técnico |
| LightGBM com peso intermediário | Manter como alternativa experimental |
| LightGBM com peso integral | Não recomendado nos resultados atuais |

A seleção do LightGBM não representa aprovação automática para uso operacional. A decisão de implantação dependerá de requisitos de negócio, capacidade de investigação dos alertas, custo dos falsos positivos, impacto das fraudes não identificadas e validações adicionais.

---

## 8. Limitações e cuidados metodológicos

A comparação deve ser interpretada considerando as seguintes limitações:

1. O KNN utilizou uma amostra de treinamento com proporção 10:1, enquanto o LightGBM sem ponderação utilizou todos os registros do treinamento.
2. Os modelos utilizaram quantidades diferentes de features: 12 para KNN e quatro para LightGBM. Portanto, a comparação representa os experimentos completos, não um teste isolado dos algoritmos sob condições idênticas.
3. Os limiares foram selecionados utilizando o conjunto de validação e mantidos na avaliação final do teste. Não foram reajustados com base nos resultados do teste.
4. As probabilidades dos modelos não devem ser interpretadas automaticamente como probabilidades reais calibradas de fraude.
5. A divisão temporal identificou mudanças na frequência de fraudes entre os períodos. A prevalência de fraude aumentou de 0,0951% no treinamento para 0,6173% na validação e 1,3994% no teste.
6. A análise exploratória identificou concentração extrema de fraudes no encerramento da simulação: entre os steps 719 e 743 foram observadas 296 transações, todas fraudulentas. Esse padrão pode influenciar a avaliação temporal e não deve ser generalizado para transações reais.
7. No LightGBM, a maior probabilidade observada no teste coincidiu com o limiar selecionado na validação. A concentração das pontuações exige investigação adicional sobre estabilidade, distribuição e calibração.
8. Os modelos utilizaram conjuntos de features diferentes e estratégias distintas de treinamento. A decisão deve considerar essa diferença ao interpretar a comparação.
9. O projeto utiliza o dataset sintético PaySim. Os valores financeiros apresentados representam transações simuladas e não devem ser interpretados como prejuízos reais, dinheiro recuperado ou perdas efetivamente evitadas.

---

## 9. Próximas atividades

Com a avaliação comparativa concluída, as próximas atividades da frente FinOps/ML são:

1. Registrar e versionar os resultados finais e as configurações dos modelos.
2. Consolidar a função Python modular para execução das previsões.
3. Definir e testar a metodologia de estimativa de exposição financeira, documentando suas premissas.
4. Investigar a estabilidade das probabilidades e a mudança temporal observada no LightGBM.
5. Preparar o contrato de entrada e saída para integração com a frente de Engenharia de IA.
6. Apoiar a preparação dos cenários de demonstração e a apresentação técnica dos resultados.

---

## 10. Conclusão

Os experimentos demonstraram que KNN e LightGBM apresentam comportamentos diferentes na identificação de transações fraudulentas.

Na avaliação final do conjunto de teste, o KNN apresentou maior Recall, identificando 399 fraudes, contra 280 do LightGBM. Entretanto, gerou 2.501 falsos positivos, enquanto o LightGBM gerou 536.

O LightGBM sem ponderação apresentou maior Precision, F1-score, Average Precision e ROC-AUC. Também produziu menor volume de alertas. Considerando o equilíbrio entre Precision e Recall, foi selecionado como principal candidato técnico para a continuidade do projeto.

Essa decisão deve ser interpretada dentro das limitações identificadas, especialmente a mudança temporal da prevalência de fraudes e a concentração das pontuações do LightGBM no teste. O modelo ainda requer investigação de estabilidade e validação de requisitos operacionais antes de qualquer recomendação de implantação.

**Observação:** o projeto utiliza o dataset sintético PaySim. Os valores financeiros apresentados nas análises representam transações simuladas e não devem ser interpretados como prejuízos reais, dinheiro recuperado ou perdas efetivamente evitadas.

---

**Responsável:** João Batista — FinOps/ML  
**Projeto:** Grupo 5 — Cidade Inteligente: Auditoria e Prevenção de Fraudes  
**Data:** 15/11/2026  
**Status:** Comparação na validação e avaliação final no teste concluídas — LightGBM sem ponderação selecionado como principal candidato técnico.