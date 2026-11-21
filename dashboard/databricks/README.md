# Dashboard nativo Databricks — LightGBM V2

## Arquitetura adotada

O projeto utiliza exclusivamente o Databricks nesta entrega. As tabelas Delta, as SQL Views, as consultas, os indicadores e o dashboard ficam no workspace Databricks.

Fluxo:

1. `workspace.gold_ml.gbm_transacoes`: fonte Gold ML para inferência.
2. `workspace.ml_experiments.gbm_v2_scoring_resultados`: scores e alertas persistidos.
3. `workspace.ml_experiments`: SQL Views de consumo e avaliação.
4. Databricks AI/BI Dashboard: visualização nativa das views.

## 1. Criar as views no Databricks

1. Abra o SQL Editor do Databricks.
2. Selecione um SQL Warehouse no qual sua conta tenha permissão de uso.
3. Abra `sql/lightgbm_v2_databricks_views.sql`.
4. Execute o script completo.
5. Confira a criação:

```sql
SHOW VIEWS IN workspace.ml_experiments;
```

Views previstas:

- `vw_gbm_v2_dashboard_detalhado`
- `vw_gbm_v2_dashboard_resumo_step`
- `vw_gbm_v2_dashboard_alertas`
- `vw_gbm_v2_dashboard_avaliacao_teste`

As três primeiras são operacionais e não expõem o rótulo `eh_fraude`. A quarta é exclusivamente histórica, agrega os resultados contra os rótulos reais do conjunto de teste e não deve ser usada como fonte de inferência.

## 2. Criar o AI/BI Dashboard dentro do Databricks

A criação do dashboard é feita no próprio workspace Databricks:

1. No menu lateral, selecione **New > Dashboard**.
2. Dê o nome `Monitoramento Antifraude — LightGBM V2`.
3. Na guia **Data**, selecione **Add data** e escolha as views do Unity Catalog em `workspace.ml_experiments`.
4. Utilize `vw_gbm_v2_dashboard_resumo_step` para os indicadores agregados, `vw_gbm_v2_dashboard_alertas` para investigação e `vw_gbm_v2_dashboard_avaliacao_teste` para a avaliação histórica.
5. Crie as visualizações na tela do dashboard, organize por páginas e publique conforme as permissões do workspace.

Os datasets do dashboard devem consultar as views existentes. Não replique cálculos de negócio em camadas externas. As consultas dos datasets são somente leitura; criação e alteração das views devem continuar no SQL Editor ou em artefatos SQL versionados.

## 3. Organização sugerida das páginas

### Página 1 — Visão geral operacional

Fonte: `vw_gbm_v2_dashboard_resumo_step`.

Indicadores sugeridos:

- Total de transações analisadas: soma de `total_transacoes_analisadas`.
- Total de alertas: soma de `total_alertas`.
- Taxa de alertas: total de alertas dividido pelo total de transações.
- Exposição financeira sinalizada: soma de `exposicao_financeira_sinalizada`.
- Score médio: média ponderada pelo volume dos steps, se agregado em mais de um step.
- Linha temporal de transações e alertas por `step`.

Filtros sugeridos: `step`, `dia_absoluto`, `nome_modelo` e `sha256_modelo`.

### Página 2 — Investigação de alertas

Fonte: `vw_gbm_v2_dashboard_alertas`.

Tabela de investigação com `id_transacao`, `step`, `fraud_score`, `limiar`, `status_analise`, `valor_sinalizado`, `scored_at` e `run_id`. Adicione filtros por faixa de score, step e data de processamento.

### Página 3 — Avaliação histórica do modelo

Fonte: `vw_gbm_v2_dashboard_avaliacao_teste`.

Apresente TP, FP, TN, FN, precisão, recall e F1 do conjunto de teste. Deixe claro que essa página é uma avaliação histórica com rótulos conhecidos, não um painel de inferência em tempo real.

Average Precision (0,659264) e ROC-AUC (0,970289) foram calculadas na avaliação independente e estão registradas no relatório técnico/metadados do experimento. A view SQL atual calcula a matriz de confusão, precisão, recall e F1; não recalcula AP ou ROC-AUC.

## 4. Cuidados de interpretação

- O dataset PaySim é sintético; alertas não são fraudes reais confirmadas.
- `valor_sinalizado` soma valores originais das transações alertadas. A unidade/moeda não foi confirmada; não adicionar símbolo de moeda nem chamar de prejuízo, perda evitada ou valor recuperado.
- `fraud_score` é score do classificador e não deve ser apresentado como probabilidade perfeitamente calibrada sem estudo específico de calibração.
- Precision, recall e F1 dependem de rótulos confirmados e pertencem à página de avaliação histórica. A página operacional não deve assumir que alertas são fraude confirmada.
- A partição do experimento foi cronológica por `step`, não por dia completo; a ressalva está no relatório técnico.

## Referências oficiais Databricks

- [Criar e gerenciar dashboards AI/BI](https://docs.databricks.com/gcp/en/dashboards/tutorials/create-dashboard)
- [Criar e gerenciar datasets de dashboard](https://docs.databricks.com/gcp/en/dashboards/manage/data-modeling/datasets)
- [Databricks SQL](https://docs.databricks.com/gcp/en/sql)
