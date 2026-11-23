-- ============================================================================
-- Grupo 5 | KNN V2 | Views nativas para o dashboard Databricks
--
-- Execute este script no Databricks SQL Editor, conectado a um SQL Warehouse.
-- As tres primeiras views sao operacionais e NAO expoem o rotulo eh_fraude.
-- A quarta view e exclusivamente historica: avalia o conjunto de teste (steps
-- 632 a 743) relacionando os resultados persistidos aos rotulos da Gold KNN.
--
-- Tabela operacional:
--   workspace.ml_experiments.knn_v2_scoring_resultados
-- Fonte dos rotulos para avaliacao:
--   workspace.gold_ml.knn_transacoes
--
-- Observacao sobre o esquema KNN V2:
-- A tabela de resultados nao possui valor_sinalizado nem scored_at. Por isso,
-- essas colunas nao sao referenciadas nas views KNN. Nao se deve interpretar o
-- fraud_score como probabilidade calibrada: ele representa a fracao de votos
-- positivos entre os vizinhos do KNN.
-- ============================================================================


-- ============================================================================
-- 1. VISAO DETALHADA
-- Uma linha por transacao/modelo persistida, sem o rotulo real de fraude.
-- ============================================================================

CREATE OR REPLACE VIEW workspace.ml_experiments.vw_knn_v2_dashboard_detalhado AS
SELECT
    id_transacao,
    step,
    dia_absoluto,
    fraud_score,
    fraud_alert,
    status_analise,
    nome_modelo,
    sha256_modelo,
    limiar,
    run_id,
    CASE
        WHEN fraud_score >= 0.50 THEN 'Muito alto (>= 0,50)'
        WHEN fraud_score >= limiar THEN 'Alerta (limiar a 0,50)'
        WHEN fraud_score >= 0.05 THEN 'Atencao (0,05 ao limiar)'
        ELSE 'Baixo (< 0,05)'
    END AS faixa_score
FROM workspace.ml_experiments.knn_v2_scoring_resultados;


-- ============================================================================
-- 2. RESUMO POR STEP
-- Metricas operacionais para os graficos temporais e indicadores do dashboard.
-- ============================================================================

CREATE OR REPLACE VIEW workspace.ml_experiments.vw_knn_v2_dashboard_resumo_step AS
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
    AVG(fraud_score) AS score_medio,
    AVG(CASE WHEN fraud_alert THEN fraud_score END) AS score_medio_alertas,
    MAX(fraud_score) AS score_maximo,
    COUNT(DISTINCT run_id) AS quantidade_runs
FROM workspace.ml_experiments.knn_v2_scoring_resultados
GROUP BY
    nome_modelo,
    sha256_modelo,
    limiar,
    dia_absoluto,
    step;


-- ============================================================================
-- 3. ALERTAS
-- Somente transacoes classificadas como ALERTA pelo limiar congelado do modelo.
-- Nao inclui eh_fraude: alerta nao significa fraude confirmada.
-- ============================================================================

CREATE OR REPLACE VIEW workspace.ml_experiments.vw_knn_v2_dashboard_alertas AS
SELECT
    id_transacao,
    step,
    dia_absoluto,
    fraud_score,
    limiar,
    status_analise,
    nome_modelo,
    sha256_modelo,
    run_id
FROM workspace.ml_experiments.knn_v2_scoring_resultados
WHERE fraud_alert = TRUE;


-- ============================================================================
-- 4. AVALIACAO HISTORICA DO CONJUNTO DE TESTE
-- O eh_fraude e lido da Gold KNN somente nesta view de avaliacao.
-- Nao utilizar esta view para inferencia nem como monitoramento online.
-- O SHA-256 fixa a avaliacao ao artefato KNN V2 efetivamente congelado.
-- Os steps 632-743 correspondem ao conjunto de teste temporal do experimento.
-- ============================================================================

CREATE OR REPLACE VIEW workspace.ml_experiments.vw_knn_v2_dashboard_avaliacao_teste AS
WITH confusao AS (
    SELECT
        r.nome_modelo,
        r.sha256_modelo,
        r.limiar,
        COUNT(*) AS total_avaliado,
        SUM(CASE WHEN t.eh_fraude = 1 THEN 1 ELSE 0 END) AS fraudes_reais,
        SUM(CASE WHEN t.eh_fraude = 0 THEN 1 ELSE 0 END) AS normais_reais,
        SUM(CASE WHEN t.eh_fraude = 1 AND r.fraud_alert THEN 1 ELSE 0 END)
            AS verdadeiros_positivos,
        SUM(CASE WHEN t.eh_fraude = 0 AND r.fraud_alert THEN 1 ELSE 0 END)
            AS falsos_positivos,
        SUM(CASE WHEN t.eh_fraude = 0 AND NOT r.fraud_alert THEN 1 ELSE 0 END)
            AS verdadeiros_negativos,
        SUM(CASE WHEN t.eh_fraude = 1 AND NOT r.fraud_alert THEN 1 ELSE 0 END)
            AS falsos_negativos,
        SUM(CASE WHEN r.fraud_alert THEN 1 ELSE 0 END) AS total_alertas
    FROM workspace.ml_experiments.knn_v2_scoring_resultados AS r
    INNER JOIN workspace.gold_ml.knn_transacoes AS t
        ON r.id_transacao = t.id_transacao
       AND r.step = t.step
    WHERE r.sha256_modelo =
        '43a6e622b1d9182e47ac0ab4ec813016c0195ab08d23bbab7ede09e4b3ba370a'
      AND r.step BETWEEN 632 AND 743
    GROUP BY
        r.nome_modelo,
        r.sha256_modelo,
        r.limiar
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
        / NULLIF(
            2 * verdadeiros_positivos + falsos_positivos + falsos_negativos,
            0
        ) AS f1_teste
FROM confusao;


-- ============================================================================
-- 5. VALIDACAO DA CRIACAO DAS VIEWS
-- Execute depois que os quatro CREATE OR REPLACE VIEW terminarem com sucesso.
-- ============================================================================

-- SHOW VIEWS IN workspace.ml_experiments;
-- SELECT * FROM workspace.ml_experiments.vw_knn_v2_dashboard_resumo_step LIMIT 20;
-- SELECT * FROM workspace.ml_experiments.vw_knn_v2_dashboard_alertas LIMIT 20;
-- SELECT * FROM workspace.ml_experiments.vw_knn_v2_dashboard_avaliacao_teste;
