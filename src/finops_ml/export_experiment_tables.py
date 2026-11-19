
# ================================================================
# CONFIGURACAO DOS CONJUNTOS - LIGHTGBM V2
# ORIGEM: GOLD CORRIGIDA DO DATABRICKS
# ================================================================

EXPORT_CONFIG = {

    # ------------------------------------------------------------
    # TREINAMENTO: 100% das fraudes e aproximadamente 2% dos normais
    # Os pesos amostrais ja estao registrados na tabela Delta.
    # ------------------------------------------------------------
    "treino": {
        "table": (
            "workspace.ml_experiments."
            "gbm_v2_treino_amostra_gold_corrigida"
        ),
        "filename": "treino_gold_corrigida.parquet",
        "expected_rows": 127396,
    },

    # ------------------------------------------------------------
    # VALIDACAO: conjunto completo, sem amostragem.
    # Utilizado para acompanhar o desempenho e selecionar o limiar.
    # ------------------------------------------------------------
    "validacao": {
        "table": (
            "workspace.ml_experiments."
            "gbm_v2_validacao_gold_corrigida"
        ),
        "filename": "validacao_gold_corrigida.parquet",
        "expected_rows": 191147,
    },

    # ------------------------------------------------------------
    # TESTE: conjunto completo, reservado para avaliacao final.
    # Nao sera utilizado para escolher parametros ou limiar.
    # ------------------------------------------------------------
    "teste": {
        "table": (
            "workspace.ml_experiments."
            "gbm_v2_teste_gold_corrigida"
        ),
        "filename": "teste_gold_corrigida.parquet",
        "expected_rows": 89466,
    },
}
