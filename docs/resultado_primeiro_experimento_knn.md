# RELATÓRIO DE DESEMPENHO — KNN
## Projeto Integrador | Grupo 5 — Cidade Inteligente: Auditoria e Prevenção de Fraudes

**Responsável:** João Batista — FinOps/ML  
**Data:** 14/11/2026  
**Modelo:** K-Nearest Neighbors (KNN)  
**Status:** Primeiro experimento concluído — em avaliação

---

## 1. Objetivo

Desenvolver um primeiro modelo de Machine Learning utilizando KNN para identificar transações potencialmente fraudulentas no dataset PaySim.

O experimento busca estabelecer uma referência de desempenho para posterior comparação com o modelo LightGBM.

## 2. Preparação dos dados

Foi utilizada uma divisão temporal dos registros, respeitando a sequência dos eventos da simulação.

| Conjunto | Intervalo de step | Transações | Fraudes |
|---|---:|---:|---:|
| Treinamento | 1–520 | 6.082.007 | 5.781 |
| Validação | 521–631 | 191.147 | 1.180 |
| Teste | 632–743 | 89.466 | 1.252 |

O conjunto de teste permaneceu reservado para a avaliação final.

### Tratamentos e transformações

**Outliers**

Foi aplicado o método IQR à variável `amount`, com limite superior de R$ 502.605,22, calculado exclusivamente no treinamento.

A remoção indiscriminada foi descartada como estratégia principal, pois eliminaria 47,36% dos exemplos fraudulentos do treinamento.

Foi adotado o Capping para limitar valores extremos, preservando os registros.

**Binning**

Foram criadas cinco faixas de valores utilizando os percentis de 20%, 40%, 60% e 80% do treinamento.

**Feature Engineering**

Foi criada a variável `log_amount` por meio da transformação `np.log1p()`.

A assimetria passou de 1,1809 para -0,7375 após a transformação.

Também foi criada a variável binária `destino_eh_comercio`, a partir do prefixo do identificador do destinatário.

**Normalização**

Foi utilizado `StandardScaler` na variável `log_amount`, com ajuste exclusivamente no treinamento e aplicação posterior na validação e no teste.

**Codificação categórica**

Foi aplicado One-Hot Encoding para as variáveis `type` e `faixa_valor`.

### Features utilizadas

| Grupo | Variáveis |
|---|---|
| Financeira | `log_amount` |
| Comportamental | `destino_eh_comercio` |
| Tipo de transação | Cinco variáveis binárias |
| Faixa de valor | Cinco variáveis binárias |

Total: **12 features**.

A variável `step` foi utilizada exclusivamente para separação temporal, não como preditora neste primeiro experimento.

## 3. Configuração do modelo

O treinamento utilizou uma amostra controlada para reduzir o custo computacional do KNN.

| Parâmetro | Configuração |
|---|---|
| Algoritmo | KNN |
| Número de vizinhos | 5 |
| Ponderação | `distance` |
| Métrica de distância | Euclidiana |
| Busca | KDTree |
| Treinamento | 63.591 registros |
| Features | 12 |
| Proporção da amostra | 10 legítimas para 1 fraudulenta |

A amostra foi composta por:

- 57.810 transações legítimas.
- 5.781 transações fraudulentas.

Todas as fraudes do conjunto de treinamento foram preservadas na amostra.

A validação permaneceu com sua distribuição original, sem balanceamento artificial.

## 4. Resultado inicial na validação

Foi utilizado inicialmente o limiar de classificação de 0,50.

| Métrica | Resultado |
|---|---:|
| Precision | 0,0613 |
| Recall | 0,3492 |
| F1-score | 0,1044 |
| Average Precision (AP) | 0,0423 |
| ROC-AUC | 0,8325 |
| Tempo de previsão e avaliação | 16,39 segundos |

### Interpretação

O modelo apresentou ROC-AUC de 0,8325, indicando capacidade de distinguir transações legítimas e fraudulentas considerando diferentes limiares.

O Recall de 34,92% demonstra que o modelo conseguiu identificar aproximadamente 35% das fraudes presentes na validação.

A Precision de 6,13%, entretanto, indica uma quantidade elevada de falsos positivos.

O Average Precision de 0,0423 ficou aproximadamente 6,9 vezes acima da prevalência de fraudes na validação, que foi de 0,6173%.

Esses resultados indicam a existência de sinal preditivo, mas ainda há limitações na precisão dos alertas.

## 5. Comparação dos limiares de classificação

Foram testados seis limiares diferentes na validação.

| Limiar | Precision | Recall | F1-score | Verdadeiros positivos | Falsos positivos |
|---:|---:|---:|---:|---:|---:|
| 0,05 | 0,0281 | 0,7627 | 0,0543 | 900 | 31.084 |
| 0,10 | 0,0305 | 0,7305 | 0,0586 | 862 | 27.385 |
| 0,20 | 0,0370 | 0,6814 | 0,0702 | 804 | 20.928 |
| 0,30 | 0,0414 | 0,6424 | 0,0778 | 758 | 17.548 |
| 0,40 | 0,0456 | 0,6153 | 0,0850 | 726 | 15.180 |
| 0,50 | 0,0613 | 0,3492 | **0,1044** | 412 | 6.304 |

O limiar de 0,05 apresentou o maior Recall, mas também produziu uma quantidade muito elevada de falsos positivos.

O limiar de 0,50 apresentou o melhor F1-score entre os seis valores testados.

### Decisão sobre o limiar

O limiar de 0,50 será mantido como referência inicial para o KNN, sem aprovação operacional definitiva.

A escolha final deverá considerar o equilíbrio entre identificação de fraudes, falsos alertas e impacto financeiro dos erros.

## 6. Análise da curva Precision-Recall

Foi construída uma curva Precision-Recall para avaliar o comportamento do modelo em diferentes limiares.

A visualização demonstrou:

- Alta Precision em uma região inicial com poucas previsões positivas.
- Redução da Precision conforme o Recall aumenta.
- Dificuldade em manter uma quantidade controlada de falsos positivos quando se busca identificar mais fraudes.

A curva reforça que o modelo ainda precisa de melhorias para ser utilizado como solução de prevenção.

## 7. Principais conclusões

O primeiro experimento KNN foi concluído com sucesso técnico e estabeleceu uma referência quantitativa para a comparação com LightGBM.

Os resultados demonstraram capacidade de discriminação entre as classes, mas também evidenciaram limitações na Precision.

A amostragem 10:1 reduziu o custo computacional, preservando todas as fraudes do treinamento. Entretanto, essa alteração na distribuição original pode afetar a interpretação das probabilidades produzidas pelo modelo.

Por esse motivo, as probabilidades não devem ser consideradas automaticamente como probabilidades reais calibradas de fraude.

**Status do modelo:** baseline experimental concluído. Não aprovado como modelo definitivo.

## 8. Próximas atividades

1. Preparar o pipeline de treinamento do LightGBM.
2. Utilizar os mesmos conjuntos temporais de treinamento, validação e teste.
3. Comparar KNN e LightGBM com critérios equivalentes.
4. Avaliar Precision, Recall, F1-score, PR-AUC, ROC-AUC e matriz de confusão.
5. Investigar o impacto da amostragem e dos diferentes tratamentos de outliers.
6. Selecionar a configuração mais adequada com base na validação.
7. Realizar a avaliação final no conjunto de teste, preservado até essa etapa.
8. Desenvolver a função Python modular de previsão e estimativa de exposição financeira.

---

**Responsável pelo experimento:** João Batista — FinOps/ML  
**Projeto:** Grupo 5 — Cidade Inteligente | Auditoria e Prevenção de Fraudes