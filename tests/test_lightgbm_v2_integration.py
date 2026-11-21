from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from finops_ml.fraud_scoring import (  # noqa: E402
    MODEL_FEATURES,
    load_model_artifacts,
    preparar_features_lightgbm_v2,
    score_transactions,
    summarize_exposure,
)
from finops_ml.gold_ml_features import (  # noqa: E402
    FEATURE_COLUMNS,
    preparar_features_gold_ml,
)


def sample_features(n: int = 3) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "valor": [1250.0, 54000.0, 750.0][:n],
            "eh_pagamento": [1, 0, 0][:n],
            "eh_deposito": [0, 0, 1][:n],
            "eh_debito": [0, 0, 0][:n],
            "eh_saque": [0, 1, 0][:n],
            "eh_transferencia": [0, 0, 0][:n],
            "destino_eh_comercio": [0, 1, 0][:n],
            "qtd_recebimentos_destino_hist": [2, 18, 0][:n],
            "qtd_recebimentos_destino_24h": [1, 5, 0][:n],
            "hora_do_dia": [10, 2, 18][:n],
        }
    )


def test_contract_order_matches_model():
    features = preparar_features_lightgbm_v2(sample_features())
    assert tuple(features.columns) == MODEL_FEATURES
    assert FEATURE_COLUMNS == list(MODEL_FEATURES)


def test_load_and_score_frozen_model():
    model, config, metadata = load_model_artifacts(ROOT / "models")
    scored = score_transactions(model, sample_features(), config)

    assert len(scored) == 3
    assert scored["fraud_score"].between(0, 1).all()
    assert scored["fraud_alert"].dtype == bool
    assert config.threshold == metadata["congelamento"]["limiar_selecionado"]
    assert set(scored["status_analise"]).issubset({"ALERTA", "SEM_ALERTA"})

    summary = summarize_exposure(scored)
    assert summary["total_transacoes_analisadas"] == 3
    assert summary["total_alertas"] == int(scored["fraud_alert"].sum())


def test_type_column_can_create_transaction_flags():
    raw = sample_features().drop(
        columns=["eh_pagamento", "eh_deposito", "eh_debito", "eh_saque", "eh_transferencia"]
    )
    raw["type"] = ["PAYMENT", "CASH_OUT", "CASH_IN"]
    prepared = preparar_features_lightgbm_v2(raw)
    assert prepared[["eh_pagamento", "eh_saque", "eh_deposito"]].to_numpy().tolist() == [
        [1, 0, 0], [0, 1, 0], [0, 0, 1]
    ]


def test_missing_24h_feature_fails_instead_of_guessing():
    raw = sample_features().drop(columns=["qtd_recebimentos_destino_24h"])
    try:
        preparar_features_lightgbm_v2(raw)
    except ValueError as exc:
        assert "qtd_recebimentos_destino_24h" in str(exc)
    else:
        raise AssertionError("A preparação deveria rejeitar a feature ausente.")


def test_gold_training_preparation_uses_exact_contract():
    gold = sample_features()
    gold["eh_fraude"] = [0, 1, 0]
    X, y = preparar_features_gold_ml(gold)
    assert list(X.columns) == list(MODEL_FEATURES)
    assert y.tolist() == [0, 1, 0]
    assert np.isfinite(X.to_numpy(dtype="float64")).all()
