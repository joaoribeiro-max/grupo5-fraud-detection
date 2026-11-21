"""Scoring antifraude com o modelo LightGBM V2 congelado do Grupo 5.

O modelo recebe exatamente as 10 features registradas nos metadados, na mesma
ordem. O scoring usa Booster.predict() (probabilidade da classe positiva),
não predict_proba() / joblib.

A exposição financeira é a soma dos valores originais das transações alertadas.
Ela não representa prejuízo real, perda evitada ou valor recuperado.
"""

from __future__ import annotations

import hashlib
import json
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd


MODEL_FILENAME = "lightgbm_v2_modelo_congelado.txt"
METADATA_FILENAME = "lightgbm_v2_metadata_congelado.json"
DEFAULT_THRESHOLD = 0.08341406734582016

MODEL_FEATURES: tuple[str, ...] = (
    "valor",
    "eh_pagamento",
    "eh_deposito",
    "eh_debito",
    "eh_saque",
    "eh_transferencia",
    "destino_eh_comercio",
    "qtd_recebimentos_destino_hist",
    "qtd_recebimentos_destino_24h",
    "hora_do_dia",
)

BINARY_FEATURES: tuple[str, ...] = (
    "eh_pagamento",
    "eh_deposito",
    "eh_debito",
    "eh_saque",
    "eh_transferencia",
    "destino_eh_comercio",
)

COUNT_FEATURES: tuple[str, ...] = (
    "qtd_recebimentos_destino_hist",
    "qtd_recebimentos_destino_24h",
)

# Conversão opcional da coluna bruta `type` para as flags do contrato V2.
TRANSACTION_TYPE_TO_FLAG = {
    "PAYMENT": "eh_pagamento",
    "CASH_IN": "eh_deposito",
    "DEBIT": "eh_debito",
    "CASH_OUT": "eh_saque",
    "TRANSFER": "eh_transferencia",
}


@dataclass(frozen=True)
class FraudScoringConfig:
    """Configuração aplicada no scoring."""

    threshold: float = DEFAULT_THRESHOLD

    def __post_init__(self) -> None:
        if not np.isfinite(self.threshold) or not 0.0 <= self.threshold <= 1.0:
            raise ValueError("O limiar precisa ser um número entre 0 e 1.")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validar_dataframe(transacoes: pd.DataFrame) -> None:
    if not isinstance(transacoes, pd.DataFrame):
        raise TypeError("A entrada deve ser um pandas.DataFrame.")
    if transacoes.empty:
        raise ValueError("A base de transações está vazia.")
    if transacoes.columns.duplicated().any():
        raise ValueError("A base possui nomes de colunas duplicados.")


def preparar_features_lightgbm_v2(transacoes: pd.DataFrame) -> pd.DataFrame:
    """Prepara e valida as 10 features exigidas pelo LightGBM V2.

    A entrada pode conter `valor` ou, por compatibilidade com dados brutos,
    `amount`. As cinco flags de tipo podem ser fornecidas diretamente ou
    derivadas da coluna `type` (PAYMENT/CASH_IN/DEBIT/CASH_OUT/TRANSFER).

    Não são inferidas as contagens históricas/de 24h nem a flag comercial:
    elas precisam vir da Gold ML com a mesma definição usada no treinamento.
    """

    _validar_dataframe(transacoes)
    data = transacoes.copy()

    if "valor" not in data.columns and "amount" in data.columns:
        data["valor"] = data["amount"]

    # Completa somente as flags ausentes, caso a coluna type esteja disponível.
    missing_type_flags = [
        flag for flag in TRANSACTION_TYPE_TO_FLAG.values()
        if flag not in data.columns
    ]
    if missing_type_flags:
        if "type" not in data.columns:
            raise ValueError(
                "Flags de tipo ausentes e coluna 'type' não fornecida: "
                f"{missing_type_flags}"
            )

        transaction_types = (
            data["type"].astype("string").str.strip().str.upper()
        )
        if transaction_types.isna().any():
            raise ValueError("A coluna 'type' possui valores ausentes.")
        unknown_types = sorted(set(transaction_types) - set(TRANSACTION_TYPE_TO_FLAG))
        if unknown_types:
            raise ValueError(f"Tipos de transação não reconhecidos: {unknown_types}")

        for transaction_type, flag in TRANSACTION_TYPE_TO_FLAG.items():
            if flag not in data.columns:
                data[flag] = transaction_types.eq(transaction_type).astype("int8")

    missing = [column for column in MODEL_FEATURES if column not in data.columns]
    if missing:
        raise ValueError(
            "A entrada não atende ao contrato do LightGBM V2. "
            f"Colunas ausentes: {missing}. Não substitua as contagens "
            "históricas/de 24h por outras métricas sem confirmar a definição "
            "usada no treinamento."
        )

    features = data.loc[:, list(MODEL_FEATURES)].copy()

    for column in MODEL_FEATURES:
        features[column] = pd.to_numeric(features[column], errors="coerce")
        values = features[column].to_numpy(dtype="float64")
        if not np.isfinite(values).all():
            raise ValueError(f"A feature '{column}' possui valores ausentes, inválidos ou não finitos.")

    if (features["valor"] < 0).any():
        raise ValueError("A feature 'valor' não pode conter valores negativos.")

    for column in BINARY_FEATURES:
        if not features[column].isin([0, 1]).all():
            raise ValueError(f"A feature '{column}' deve conter apenas 0 ou 1.")
        features[column] = features[column].astype("int8")

    sum_transaction_types = features[
        [
            "eh_pagamento",
            "eh_deposito",
            "eh_debito",
            "eh_saque",
            "eh_transferencia",
        ]
    ].sum(axis=1)
    if not sum_transaction_types.eq(1).all():
        raise ValueError("Cada transação deve possuir exatamente um tipo.")

    for column in COUNT_FEATURES:
        values = features[column]
        if (values < 0).any():
            raise ValueError(f"A feature '{column}' não pode ser negativa.")
        if not np.equal(values.to_numpy(dtype="float64") % 1, 0).all():
            raise ValueError(f"A feature '{column}' deve conter números inteiros.")
        features[column] = values.astype("int64")

    hour = features["hora_do_dia"]
    if not hour.between(0, 23).all():
        raise ValueError("A feature 'hora_do_dia' deve estar entre 0 e 23.")
    if not np.equal(hour.to_numpy(dtype="float64") % 1, 0).all():
        raise ValueError("A feature 'hora_do_dia' deve conter horas inteiras.")
    features["hora_do_dia"] = hour.astype("int8")
    features["valor"] = features["valor"].astype("float64")

    if tuple(features.columns) != MODEL_FEATURES:
        raise RuntimeError("A ordem das features não corresponde ao contrato congelado.")

    return features


def score_transactions(
    modelo: Any,
    transacoes: pd.DataFrame,
    config: FraudScoringConfig | None = None,
) -> pd.DataFrame:
    """Calcula o score e gera alertas usando o Booster LightGBM V2."""

    if modelo is None or not callable(getattr(modelo, "predict", None)):
        raise TypeError("O modelo precisa disponibilizar o método predict().")

    config = config or FraudScoringConfig()
    features = preparar_features_lightgbm_v2(transacoes)

    model_feature_names = getattr(modelo, "feature_name", None)
    if callable(model_feature_names):
        model_feature_names = model_feature_names()
    if model_feature_names and list(model_feature_names) != list(MODEL_FEATURES):
        raise ValueError(
            "As features do Booster não correspondem ao contrato do LightGBM V2."
        )

    scores = np.asarray(modelo.predict(features), dtype="float64").reshape(-1)
    if len(scores) != len(transacoes):
        raise ValueError("A quantidade de scores não corresponde à quantidade de transações.")
    if not np.isfinite(scores).all():
        raise ValueError("O Booster retornou scores não finitos.")
    if ((scores < 0) | (scores > 1)).any():
        raise ValueError("O Booster retornou scores fora do intervalo [0, 1].")

    # O valor usado para exposição é o valor original, sem transformação/capping.
    original_value_column = "valor" if "valor" in transacoes.columns else "amount"
    if original_value_column not in transacoes.columns:
        raise ValueError("A entrada precisa conter 'valor' ou 'amount'.")
    original_values = pd.to_numeric(
        transacoes[original_value_column], errors="coerce"
    ).to_numpy(dtype="float64")
    if not np.isfinite(original_values).all() or (original_values < 0).any():
        raise ValueError("Os valores originais das transações são inválidos.")

    alerts = scores >= config.threshold
    result = transacoes.copy()
    result["fraud_score"] = scores
    result["fraud_alert"] = alerts
    result["status_analise"] = np.where(alerts, "ALERTA", "SEM_ALERTA")
    result["valor_sinalizado"] = np.where(alerts, original_values, 0.0)
    return result


def summarize_exposure(resultado: pd.DataFrame) -> dict[str, int | float]:
    """Resume alertas e exposição financeira sinalizada."""

    required = {"fraud_alert", "valor_sinalizado", "fraud_score"}
    missing = required - set(resultado.columns)
    if missing:
        raise ValueError(f"Colunas ausentes no resultado: {sorted(missing)}")

    total = int(len(resultado))
    alerts = int(resultado["fraud_alert"].astype(bool).sum())
    exposure = float(pd.to_numeric(resultado["valor_sinalizado"]).sum())
    mean_score = float(resultado["fraud_score"].mean()) if total else 0.0

    return {
        "total_transacoes_analisadas": total,
        "total_alertas": alerts,
        "taxa_alertas": alerts / total if total else 0.0,
        "exposicao_financeira_sinalizada": exposure,
        "score_medio_modelo": mean_score,
    }


def load_model_artifacts(
    models_dir: str | Path | None = None,
) -> tuple[lgb.Booster, FraudScoringConfig, dict[str, Any]]:
    """Carrega o Booster .txt e os metadados, validando hash e contrato."""

    if models_dir is None:
        project_root = Path(__file__).resolve().parents[2]
        models_dir = project_root / "models"
    models_dir = Path(models_dir)

    model_path = models_dir / MODEL_FILENAME
    metadata_path = models_dir / METADATA_FILENAME
    if not model_path.is_file():
        raise FileNotFoundError(f"Modelo não encontrado: {model_path}")
    if not metadata_path.is_file():
        raise FileNotFoundError(f"Metadados não encontrados: {metadata_path}")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata_features = metadata.get("features", [])
    if list(metadata_features) != list(MODEL_FEATURES):
        raise ValueError("A lista/ordem de features dos metadados é incompatível com o código.")

    freeze = metadata.get("congelamento", {})
    if freeze.get("status") != "CONGELADO":
        raise ValueError("Os metadados não identificam o modelo como CONGELADO.")
    if freeze.get("arquivo_modelo") != MODEL_FILENAME:
        raise ValueError("O nome do arquivo do modelo não corresponde aos metadados.")

    expected_hash = freeze.get("sha256_modelo")
    actual_hash = _sha256_file(model_path)
    if not expected_hash or actual_hash.lower() != str(expected_hash).lower():
        raise ValueError(
            "Falha na integridade do modelo: SHA-256 do arquivo diferente dos metadados."
        )

    threshold = float(freeze["limiar_selecionado"])
    selection_threshold = float(metadata["selecao_limiar"]["limiar_candidato"])
    if not np.isclose(threshold, selection_threshold, rtol=0, atol=1e-12):
        raise ValueError("O limiar congelado diverge do limiar selecionado na validação.")
    config = FraudScoringConfig(threshold=threshold)

    booster = lgb.Booster(model_file=str(model_path))
    if booster.feature_name() != list(MODEL_FEATURES):
        raise ValueError("O arquivo .txt do Booster contém features incompatíveis.")

    expected_iterations = int(freeze.get("melhor_iteracao", metadata.get("melhor_iteracao", 0)))
    if expected_iterations and booster.num_trees() != expected_iterations:
        raise ValueError(
            "A quantidade de árvores do modelo não corresponde à melhor iteração registrada."
        )

    expected_lgb_version = metadata.get("versao_lightgbm")
    if expected_lgb_version and lgb.__version__ != expected_lgb_version:
        warnings.warn(
            f"Metadados registram LightGBM {expected_lgb_version}, "
            f"mas o ambiente está usando {lgb.__version__}. "
            "Para reprodução, instale a versão registrada.",
            RuntimeWarning,
            stacklevel=2,
        )

    return booster, config, metadata


# Alias temporário para reduzir quebras em imports existentes no projeto.
preparar_features_lightgbm = preparar_features_lightgbm_v2
