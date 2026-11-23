
# ============================================================
# TESTES AUTOMATIZADOS - KNN V2
# Projeto: Grupo 5 - Detecção de Fraudes
# Objetivo: validar carregamento, features e inferência.
# ============================================================

import numpy as np
import pandas as pd
import pytest

from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler

from finops_ml.knn_v2_predictor import (
    MODEL_FEATURES,
    KNNV2Artifacts,
    load_knn_v2_artifacts,
    prepare_knn_v2_features,
    score_knn_v2_transactions,
)


# ============================================================
# 1. FIXTURES
# ============================================================

@pytest.fixture(scope="module")
def artifacts():
    """Carrega uma única vez os artefatos congelados do KNN V2."""

    return load_knn_v2_artifacts()


@pytest.fixture
def sample_transactions():
    """Cria transações artificiais para testar a inferência."""

    return pd.DataFrame({
        "id_transacao": ["TESTE-001", "TESTE-002", "TESTE-003"],
        "step": [632, 633, 634],
        "eh_transferencia": [1, 0, 1],
        "eh_conta_nova": [0, 1, 0],
        "freq_destino_24h_norm": [0.20, 0.80, 0.45],
        "eh_rajada_destino": [0, 1, 0],
        "valor_log_norm": [0.30, 0.90, 0.55],
        "hora_sin": [0.50, 0.70, 0.25],
        "hora_cos": [0.80, 0.30, 0.65],
    })


# ============================================================
# 2. TESTES DE CARREGAMENTO E INTEGRIDADE
# ============================================================

def test_load_knn_v2_artifacts(artifacts):
    """Confirma que o pacote congelado foi carregado corretamente."""

    assert isinstance(artifacts, KNNV2Artifacts)

    assert isinstance(
        artifacts.modelo,
        KNeighborsClassifier
    )

    assert isinstance(
        artifacts.scaler,
        StandardScaler
    )

    assert artifacts.features == MODEL_FEATURES

    assert artifacts.model_sha256 == (
        "43a6e622b1d9182e47ac0ab4ec813016c0195ab08d23bbab7ede09e4b3ba370a"
    )


def test_model_parameters_are_frozen(artifacts):
    """Confirma os hiperparâmetros registrados no Colab."""

    modelo = artifacts.modelo

    assert modelo.n_neighbors == 21
    assert modelo.weights == "uniform"
    assert modelo.algorithm == "kd_tree"
    assert modelo.metric == "minkowski"
    assert modelo.p == 2
    assert modelo.leaf_size == 40

    assert modelo.n_samples_fit_ == 294_831
    assert modelo.n_features_in_ == 7


def test_threshold_is_frozen(artifacts):
    """Confirma que o limiar da validação não foi alterado."""

    assert artifacts.threshold == pytest.approx(
        0.47619047619047616
    )


# ============================================================
# 3. TESTES DE PREPARAÇÃO DAS FEATURES
# ============================================================

def test_prepare_features_preserves_official_order(
    sample_transactions
):
    """Confirma que as sete features ficam na ordem congelada."""

    # Embaralhar as colunas para testar a seleção pela ordem oficial.
    entrada = sample_transactions[
        list(reversed(MODEL_FEATURES))
    ]

    resultado = prepare_knn_v2_features(entrada)

    assert tuple(resultado.columns) == MODEL_FEATURES

    assert resultado.shape == (3, 7)


def test_prepare_features_rejects_missing_column(
    sample_transactions
):
    """Rejeita entradas sem uma das sete features."""

    entrada = sample_transactions.drop(
        columns=["valor_log_norm"]
    )

    with pytest.raises(ValueError, match="Features ausentes"):
        prepare_knn_v2_features(entrada)


def test_prepare_features_rejects_invalid_binary_feature(
    sample_transactions
):
    """Rejeita valores diferentes de zero e um nas flags binárias."""

    entrada = sample_transactions.copy()

    entrada.loc[0, "eh_transferencia"] = 2

    with pytest.raises(ValueError, match="0 ou 1"):
        prepare_knn_v2_features(entrada)


def test_prepare_features_rejects_values_outside_range(
    sample_transactions
):
    """Rejeita features normalizadas fora do intervalo permitido."""

    entrada = sample_transactions.copy()

    entrada.loc[0, "freq_destino_24h_norm"] = 1.5

    with pytest.raises(ValueError, match="intervalo"):
        prepare_knn_v2_features(entrada)


def test_prepare_features_rejects_non_finite_values(
    sample_transactions
):
    """Rejeita valores NaN ou infinitos."""

    entrada = sample_transactions.copy()

    entrada.loc[0, "valor_log_norm"] = np.nan

    with pytest.raises(ValueError, match="não finitos"):
        prepare_knn_v2_features(entrada)


def test_prepare_features_rejects_empty_dataframe():
    """Rejeita uma entrada vazia."""

    entrada = pd.DataFrame(columns=MODEL_FEATURES)

    with pytest.raises(ValueError, match="vazia"):
        prepare_knn_v2_features(entrada)


def test_prepare_features_rejects_duplicate_ids(
    sample_transactions
):
    """Rejeita identificadores duplicados."""

    entrada = sample_transactions.copy()

    entrada.loc[1, "id_transacao"] = "TESTE-001"

    with pytest.raises(ValueError, match="duplicados"):
        prepare_knn_v2_features(entrada)


# ============================================================
# 4. TESTES DE INFERÊNCIA
# ============================================================

def test_score_knn_v2_generates_valid_predictions(
    artifacts,
    sample_transactions
):
    """Confirma que o KNN calcula scores e alertas."""

    resultado = score_knn_v2_transactions(
        sample_transactions,
        artifacts
    )

    # Conferir quantidade de registros.
    assert len(resultado) == len(sample_transactions)

    # Conferir a preservação dos identificadores.
    assert resultado["id_transacao"].tolist() == (
        sample_transactions["id_transacao"].tolist()
    )

    # Conferir os scores.
    assert resultado["fraud_score"].notna().all()

    assert resultado["fraud_score"].between(0, 1).all()

    # Conferir a geração dos alertas.
    assert resultado["fraud_alert"].notna().all()

    # Conferir o limiar aplicado.
    assert (
        resultado["limiar"] == artifacts.threshold
    ).all()

    # Conferir o nome do modelo.
    assert (
        resultado["nome_modelo"] == "KNN V2"
    ).all()

    # Conferir a identificação do artefato.
    assert (
        resultado["sha256_modelo"] == artifacts.model_sha256
    ).all()


def test_predictions_follow_frozen_threshold(
    artifacts,
    sample_transactions
):
    """Confirma que os alertas respeitam o limiar congelado."""

    resultado = score_knn_v2_transactions(
        sample_transactions,
        artifacts
    )

    alertas_esperados = (
        resultado["fraud_score"] >= artifacts.threshold
    )

    np.testing.assert_array_equal(
        resultado["fraud_alert"].to_numpy(),
        alertas_esperados.to_numpy()
    )


def test_inference_does_not_modify_original_input(
    artifacts,
    sample_transactions
):
    """Confirma que a inferência não altera a entrada original."""

    original = sample_transactions.copy(deep=True)

    score_knn_v2_transactions(
        sample_transactions,
        artifacts
    )

    pd.testing.assert_frame_equal(
        sample_transactions,
        original
    )


def test_inference_rejects_empty_dataframe(artifacts):
    """Confirma que o scoring rejeita uma entrada vazia."""

    entrada = pd.DataFrame(columns=MODEL_FEATURES)

    with pytest.raises(ValueError, match="vazia"):
        score_knn_v2_transactions(
            entrada,
            artifacts
        )
