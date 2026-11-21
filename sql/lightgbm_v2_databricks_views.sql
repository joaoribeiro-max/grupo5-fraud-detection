-- Grupo 5 | LightGBM V2 | Views nativas do Databricks
-- Execute este script no Databricks SQL Editor, conectado a um SQL Warehouse.
-- As views operacionais não expõem eh_fraude nem flag_fraude_sistema.
-- A view de avaliação é histórica e exclusiva do conjunto de teste.

CREATE OR REPLACE VIEW workspace.ml_experiments.vw_gbm_v2_dashboard_detalhado AS
SELECT
    id_transacao,
    step,
    dia_absoluto,
    fraud_score,
    fraud_alert,
    status_analise,
    valor_sinalizado,
    nome_modelo,
    sha256_modelo,
    limiar,
    run_id,
    scored_at,
    CASE
        WHEN fraud_score >= 0.50 THEN 'Muito alto (>= 0,50)'
        WHEN fraud_score >= limiar THEN 'Alerta (limiar a 0,50)'
        WHEN fraud_score >= 0.05 THEN 'Atenção (0,05 ao limiar)'
        ELSE 'Baixo (< 0,05)'
    END AS faixa_score
FROM workspace.ml_experiments.gbm_v2_scoring_resultados;


CREATE OR REPLACE VIEW workspace.ml_experiments.vw_gbm_v2_dashboard_resumo_step AS
SELECT
    nome_modelo,
    sha256_modelo,
    limiar,
    dia_absoluto,
    step,
    COUNT(*) AS total_transacoes_analisadas,
    COUNT(DISTINCT id_transacao) AS transacoes_unicas,
    SUM(CASE WHEN fraud_alert THEN 1 ELSE 0 END) AS total_alertas,
    SUM(CASE WHEN NOT fraud_alert THEN 1 ELSE 0 END) AS total_sem_alerta,
    CAST(SUM(CASE WHEN fraud_alert THEN 1 ELSE 0 END) AS DOUBLE)
        / NULLIF(COUNT(*), 0) AS taxa_alertas,
    SUM(valor_sinalizado) AS exposicao_financeira_sinalizada,
    AVG(fraud_score) AS score_medio,
    AVG(CASE WHEN fraud_alert THEN fraud_score END) AS score_medio_alertas,
    MAX(fraud_score) AS score_maximo,
    MIN(scored_at) AS primeiro_scoring_at,
    MAX(scored_at) AS ultimo_scoring_at,
    COUNT(DISTINCT run_id) AS quantidade_runs
FROM workspace.ml_experiments.gbm_v2_scoring_resultados
GROUP BY
    nome_modelo, sha256_modelo, limiar, dia_absoluto, step;


CREATE OR REPLACE VIEW workspace.ml_experiments.vw_gbm_v2_dashboard_alertas AS
SELECT
    id_transacao,
    step,
    dia_absoluto,
    fraud_score,
    limiar,
    status_analise,
    valor_sinalizado,
    nome_modelo,
    sha256_modelo,
    run_id,
    scored_at
FROM workspace.ml_experiments.gbm_v2_scoring_resultados
WHERE fraud_alert = TRUE;


-- VIEW DE AVALIAÇÃO HISTÓRICA. NÃO UTILIZAR PARA INFERÊNCIA OPERACIONAL.
-- O rótulo eh_fraude só entra nesta view agregada para medir o conjunto de teste.
CREATE OR REPLACE VIEW workspace.ml_experiments.vw_gbm_v2_dashboard_avaliacao_teste AS
WITH confusao AS (
    SELECT
        r.nome_modelo,
        r.sha256_modelo,
        r.limiar,
        COUNT(*) AS total_avaliado,
        SUM(CASE WHEN t.eh_fraude = 1 THEN 1 ELSE 0 END) AS fraudes_reais,
        SUM(CASE WHEN t.eh_fraude = 0 THEN 1 ELSE 0 END) AS normais_reais,
        SUM(CASE WHEN t.eh_fraude = 1 AND r.fraud_alert THEN 1 ELSE 0 END) AS verdadeiros_positivos,
        SUM(CASE WHEN t.eh_fraude = 0 AND r.fraud_alert THEN 1 ELSE 0 END) AS falsos_positivos,
        SUM(CASE WHEN t.eh_fraude = 0 AND NOT r.fraud_alert THEN 1 ELSE 0 END) AS verdadeiros_negativos,
        SUM(CASE WHEN t.eh_fraude = 1 AND NOT r.fraud_alert THEN 1 ELSE 0 END) AS falsos_negativos,
        SUM(CASE WHEN r.fraud_alert THEN 1 ELSE 0 END) AS total_alertas
    FROM workspace.ml_experiments.gbm_v2_scoring_resultados r
    INNER JOIN workspace.ml_experiments.gbm_v2_teste_gold_corrigida t
        ON r.id_transacao = t.id_transacao
       AND r.step = t.step
    WHERE r.sha256_modelo = '29f183255645bbcdef16c96ca802f02d121476548a18e224cad82298e488c076'
      AND r.step BETWEEN 632 AND 743
    GROUP BY r.nome_modelo, r.sha256_modelo, r.limiar
)
SELECT
    nome_modelo,
    sha256_modelo,
    limiar,
    total_avaliado,
    fraudes_reais,
    normais_reais,
    total_alertas,
    verdadeiros_positivos,
    falsos_positivos,
    verdadeiros_negativos,
    falsos_negativos,
    CAST(verdadeiros_positivos AS DOUBLE)
        / NULLIF(total_alertas, 0) AS precision_teste,
    CAST(verdadeiros_positivos AS DOUBLE)
        / NULLIF(fraudes_reais, 0) AS recall_teste,
    2.0 * CAST(verdadeiros_positivos AS DOUBLE)
        / NULLIF((2 * verdadeiros_positivos + falsos_positivos + falsos_negativos), 0) AS f1_teste
FROM confusao;


-- Verificação rápida das views após a criação:
-- SHOW VIEWS IN workspace.ml_experiments;
-- SELECT * FROM workspace.ml_experiments.vw_gbm_v2_dashboard_resumo_step LIMIT 20;
-- SELECT * FROM workspace.ml_experiments.vw_gbm_v2_dashboard_alertas LIMIT 20;
-- SELECT * FROM workspace.ml_experiments.vw_gbm_v2_dashboard_avaliacao_teste;
