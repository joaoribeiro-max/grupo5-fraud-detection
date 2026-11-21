# Relatório técnico final — LightGBM V2

**Projeto:** Cidade Inteligente — Auditoria e Prevenção de Fraudes (Grupo 5)
**Responsabilidade:** FinOps / Machine Learning
**Data de consolidação:** 21/11/2026
**Status:** treinamento congelado, avaliação independente concluída e scoring de todo o conjunto de teste persistido e auditado.

## 1. Resumo executivo

O LightGBM V2 foi treinado no Google Colab, congelado em 137 iterações e integrado ao projeto local no VS Code. O modelo foi carregado a partir do artefato nativo LightGBM, conectado à camada Gold ML do Databricks e utilizado para pontuar o conjunto de teste completo.

A avaliação independente abrangeu **89.466 transações**, com **1.252 fraudes** e **88.214 transações normais**. Com o limiar congelado de **0,08341406734582016**, o modelo gerou 798 alertas, dos quais 621 correspondiam a fraudes no rótulo de referência.

A execução operacional persistiu 89.466 resultados na tabela separada de scoring. A auditoria SQL encontrou 89.466 IDs únicos, zero duplicados, zero transações sem score, zero registros fora do teste e zero registros pendentes na staging da execução final.

> O dataset PaySim é sintético. Os resultados demonstram o comportamento do modelo sobre dados simulados e não constituem evidência de fraude real em operações de uma prefeitura. O valor sinalizado é a soma dos valores originais das transações alertadas; não representa perda confirmada, prejuízo, recuperação ou prevenção efetiva. A moeda/unidade monetária não foi confirmada na fonte, por isso os valores devem ser apresentados como unidades do dataset.

## 2. Artefato congelado e rastreabilidade

| Item | Valor |
|---|---|
| Modelo | LightGBM V2 |
| Formato | Booster nativo `.txt` |
| Versão usada no treinamento | LightGBM 4.7.0 |
| Iteração selecionada | 137 |
| Limiar congelado | 0,08341406734582016 |
| SHA-256 | `29f183255645bbcdef16c96ca802f02d121476548a18e224cad82298e488c076` |
| Arquivo | `models/lightgbm_v2_modelo_congelado.txt` |
| Metadados | `models/lightgbm_v2_metadata_congelado.json` |

O SHA-256 calculado sobre o arquivo de modelo corresponde ao hash registrado nos metadados. O artefato não foi retreinado nem alterado durante a integração e o scoring operacional.

## 3. Features do modelo

As dez features utilizadas, na ordem exata do contrato do modelo, são:

1. `valor`
2. `eh_pagamento`
3. `eh_deposito`
4. `eh_debito`
5. `eh_saque`
6. `eh_transferencia`
7. `destino_eh_comercio`
8. `qtd_recebimentos_destino_hist`
9. `qtd_recebimentos_destino_24h`
10. `hora_do_dia`

As colunas `id_transacao`, `step` e `dia_absoluto` servem para rastreabilidade e segmentação temporal, não entram no vetor de features. `eh_fraude` e `flag_fraude_sistema` não são selecionadas pela consulta de inferência.

### 3.1 Históricos temporais

Na definição SQL da Materialized View `workspace.gold_ml.gbm_transacoes`, as contagens são calculadas por conta de destino e ordenadas por `step`:

- `qtd_recebimentos_destino_hist`: `COUNT(*) OVER (PARTITION BY conta_destino ORDER BY step RANGE BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)`.
- `qtd_recebimentos_destino_24h`: `COUNT(*) OVER (PARTITION BY conta_destino ORDER BY step RANGE BETWEEN 24 PRECEDING AND 1 PRECEDING)`.

As janelas terminam em `1 PRECEDING`, portanto excluem o step atual e os steps futuros. Como o `step` representa hora, a janela de 24 considera as 24 unidades anteriores de step. Transações dentro do mesmo step não entram no histórico umas das outras; essa granularidade deve ser mantida e documentada na inferência.

## 4. Configuração do treinamento

| Parâmetro | Valor |
|---|---:|
| objective | binary |
| metric | average_precision, binary_logloss |
| learning_rate | 0,03 |
| num_leaves | 31 |
| min_data_in_leaf | 100 |
| feature_fraction | 0,90 |
| bagging_fraction | 0,80 |
| bagging_freq | 1 |
| lambda_l1 | 0,1 |
| lambda_l2 | 1,0 |
| max_bin | 127 |
| seed | 42 |
| max_boost_round | 2.000 |
| early_stopping_rounds | 100 |
| melhor iteração | 137 |

### 4.1 Amostragem e pesos

O conjunto de treinamento preservou todas as fraudes e selecionou aproximadamente 2% das transações normais, com amostragem determinística por `xxhash64(id_transacao)`. O modelo recebeu peso 1,0 para fraudes e 50,0 para normais. Validação e teste foram utilizados com os pesos iguais a 1,0, refletindo as respectivas bases sem ponderação artificial.

## 5. Particionamento e auditoria dos dados

| Conjunto | Registros | Fraudes | Normais | Taxa de fraude | Steps | Dias absolutos |
|---|---:|---:|---:|---:|---|---|
| Treino | 127.396 | 5.781 | 121.615 | 4,5378% | 1–520 | 0–21 |
| Validação | 191.147 | 1.180 | 189.967 | 0,6173% | 521–631 | 21–26 |
| Teste | 89.466 | 1.252 | 88.214 | 1,3994% | 632–743 | 26–30 |

A auditoria encontrou zero IDs duplicados dentro de cada conjunto e zero IDs sobrepostos entre os pares treino/validação, treino/teste e validação/teste. Os intervalos de `step` são cronologicamente consecutivos e não se sobrepõem.

**Ressalva da partição diária:** a divisão foi realizada por `step`, não por dia completo. O dia absoluto 21 contém 526 registros de treino e 35.466 de validação; o dia absoluto 26 contém 222 registros de validação e 8.356 de teste. Portanto, não se deve descrever o desenho como GroupKFold ou holdout estrito por dia. A conclusão suportada é divisão cronológica por step, com IDs distintos e sem sobreposição de steps.

As taxas de fraude diferem entre os períodos. Isso pode refletir mudança temporal na prevalência e afeta a comparação direta de métricas como Average Precision entre períodos. A taxa de fraude no teste é maior do que na validação; esse comportamento deve ser acompanhado em monitoramento.

## 6. Seleção do limiar

O limiar 0,08341406734582016 foi selecionado exclusivamente no conjunto de validação pelo critério de maximização do F1. Na validação, as métricas registradas foram precisão 0,486739, recall 0,528814 e F1 0,506905. O limiar foi congelado antes da avaliação independente e não foi reajustado com base no conjunto de teste.

## 7. Avaliação independente no teste

| Métrica | Resultado |
|---|---:|
| Precision | 0,778195 (77,82%) |
| Recall | 0,496006 (49,60%) |
| F1-score | 0,605854 (60,59%) |
| Average Precision | 0,659264 |
| ROC-AUC | 0,970289 |
| Limiar | 0,08341406734582016 |

### 7.1 Matriz de confusão

| | Previsto alerta | Previsto sem alerta |
|---|---:|---:|
| Fraude real | TP = 621 | FN = 631 |
| Normal real | FP = 177 | TN = 88.037 |

O recall mostra que 621 das 1.252 fraudes foram identificadas pelo limiar congelado. As 631 restantes não foram sinalizadas. Dos 798 alertas, 621 eram fraudes e 177 eram falsos positivos.

O ROC-AUC elevado indica boa capacidade de ordenação/discriminação ao considerar diferentes limiares, mas não elimina o compromisso entre recall e volume de alertas no limiar escolhido.

## 8. Integração e scoring operacional

O executor `src/finops_ml/run_scoring.py`:

- carrega o Booster nativo e valida metadados/hash;
- consulta `workspace.gold_ml.gbm_transacoes` por intervalo de steps;
- seleciona os IDs, controles temporais e dez features, sem consultar o alvo;
- processa transações em lotes de até 5.000;
- grava os resultados em tabelas Delta separadas da Gold ML;
- utiliza INSERT multi-row em chunks de até 250 linhas, seguido de `MERGE`;
- exclui transações já pontuadas com o mesmo SHA-256 antes de nova inferência.

Tabelas operacionais:

- `workspace.ml_experiments.gbm_v2_scoring_resultados`
- `workspace.ml_experiments.gbm_v2_scoring_staging`

A chave lógica implementada no `MERGE` é `(id_transacao, sha256_modelo)`. As execuções foram sequenciais. Concorrência de múltiplos executores simultâneos não foi testada; portanto, deve-se executar uma única instância por vez.

### 8.1 Resultado operacional consolidado

A tabela de resultados foi comparada ao conjunto independente de teste, filtrando o SHA-256 congelado e os steps 632–743:

| Indicador | Resultado auditado |
|---|---:|
| Registros na origem | 89.466 |
| Registros processados | 89.466 |
| IDs únicos | 89.466 |
| Duplicados | 0 |
| Sem score | 0 |
| Fora do teste | 0 |
| Alertas operacionais | 798 |
| Registros pendentes na staging da execução final | 0 |
| Exposição financeira sinalizada | 2.190.234.127,68 unidades do dataset |

O número de alertas operacionais (798) coincide com o número de alertas da avaliação independente. Essa coincidência, junto à cobertura integral e ao hash conferido, é evidência de consistência entre avaliação e scoring. A exposição é calculada somando o `valor` original das transações sinalizadas; não é prejuízo confirmado nem valor recuperado.

## 9. Testes automatizados

O conjunto de testes validado no ambiente local do projeto teve 21 testes aprovados:

- 16 testes relacionados ao executor otimizado (contrato de inferência, query de origem, validação dos intervalos, preparação de linhas e INSERT multi-row em chunks);
- 5 testes do contrato LightGBM V2 (ordem das features, carregamento e scoring do modelo congelado, flags de tipo, rejeição de histórico 24h ausente e preparação da Gold ML).

O usuário executou os testes com Python 3.12.10, LightGBM 4.7.0 e pytest 9.2.0. A execução local registrada foi `21 passed`.

## 10. Limitações e próximos passos

1. O modelo foi validado em dados sintéticos PaySim; generalização para dados reais precisa de validação específica.
2. A partição temporal é por step, não por dia completo; a ressalva deve permanecer na documentação.
3. As taxas de fraude variam entre os períodos; monitorar prevalência e distribuição dos scores.
4. As métricas de precisão/recall/F1 só podem ser recalculadas quando houver rótulos confirmados; a tabela de inferência operacional não carrega `eh_fraude`.
5. A concorrência entre múltiplos processos de scoring ainda não foi testada.
6. Para volumes muito maiores, avaliar carga de Parquet em armazenamento acessível pelo Databricks e `COPY INTO` em vez de INSERT multi-row.
7. O KNN permanece como fase posterior; a comparação entre algoritmos deve utilizar a mesma partição e o mesmo protocolo de avaliação.

## 11. Conclusão

O experimento LightGBM V2 está encerrado quanto a treinamento, congelamento, avaliação independente e scoring integral do conjunto de teste. A integração e persistência dos resultados foram executadas e auditadas. A solução está pronta para a etapa de apresentação/monitoramento do MVP, mantendo as limitações metodológicas e operacionais acima explícitas.


## 12. Consumo, monitoramento e apresentação no Databricks

A arquitetura de consumo desta entrega permanece integralmente no Databricks. As tabelas Delta de scoring são expostas por SQL Views no schema `workspace.ml_experiments`; essas views serão utilizadas por um dashboard nativo Databricks AI/BI no mesmo workspace.

O pacote contém o script `sql/lightgbm_v2_databricks_views.sql` para criar as views e `dashboard/databricks/README.md` com a organização sugerida do dashboard. A inclusão desses arquivos no repositório não cria automaticamente as views nem o dashboard remoto: a execução SQL e a criação/publicação do dashboard ainda precisam ser realizadas no workspace Databricks.
