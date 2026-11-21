"""Preparação e validação das features Gold ML para o LightGBM V2."""

from __future__ import annotations

import numpy as np
import pandas as pd


TARGET_COLUMN = "eh_fraude"

# Identificadores para rastreabilidade; não entram na matriz de treinamento.
IDENTIFIER_COLUMNS = ["id_transacao", "step"]

# Contrato idêntico ao arquivo .txt e aos metadados do modelo congelado.
FEATURE_COLUMNS = [
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
]

BINARY_COLUMNS = [
    "eh_pagamento",
    "eh_deposito",
    "eh_debito",
    "eh_saque",
    "eh_transferencia",
    "destino_eh_comercio",
]

COUNT_COLUMNS = [
    "qtd_recebimentos_destino_hist",
    "qtd_recebimentos_destino_24h",
]

REQUIRED_COLUMNS = FEATURE_COLUMNS + [TARGET_COLUMN]


def validar_gold_ml(data: pd.DataFrame) -> None:
    """Valida as colunas, tipos e domínios esperados pela Gold ML V2."""

    if not isinstance(data, pd.DataFrame):
        raise TypeError("A entrada deve ser um pandas.DataFrame.")
    if data.empty:
        raise ValueError("A base recebida está vazia.")
    if data.columns.duplicated().any():
        raise ValueError("Existem nomes de colunas duplicados.")

    missing = set(REQUIRED_COLUMNS) - set(data.columns)
    if missing:
        raise ValueError(
            "A Gold ML não atende ao contrato do LightGBM V2. "
            f"Colunas obrigatórias ausentes: {sorted(missing)}"
        )

    numeric_columns = FEATURE_COLUMNS + [TARGET_COLUMN]
    numeric_data: dict[str, pd.Series] = {}
    for column in numeric_columns:
        values = pd.to_numeric(data[column], errors="coerce")
        if values.isna().any():
            raise ValueError(f"A coluna '{column}' possui valores ausentes ou inválidos.")
        if not np.isfinite(values.to_numpy(dtype="float64")).all():
            raise ValueError(f"A coluna '{column}' possui valores não finitos.")
        numeric_data[column] = values

    if (numeric_data["valor"] < 0).any():
        raise ValueError("A feature 'valor' não pode conter valores negativos.")

    for column in BINARY_COLUMNS + [TARGET_COLUMN]:
        if not numeric_data[column].isin([0, 1]).all():
            raise ValueError(f"A coluna '{column}' deve conter somente 0 ou 1.")

    transaction_type_sum = data[
        ["eh_pagamento", "eh_deposito", "eh_debito", "eh_saque", "eh_transferencia"]
    ].apply(pd.to_numeric).sum(axis=1)
    if not transaction_type_sum.eq(1).all():
        raise ValueError("Cada transação deve possuir exatamente um tipo.")

    for column in COUNT_COLUMNS:
        values = numeric_data[column]
        if (values < 0).any():
            raise ValueError(f"A coluna '{column}' não pode conter valores negativos.")
        if not np.equal(values.to_numpy(dtype="float64") % 1, 0).all():
            raise ValueError(f"A coluna '{column}' deve conter números inteiros.")

    hour = numeric_data["hora_do_dia"]
    if not hour.between(0, 23).all():
        raise ValueError("A coluna 'hora_do_dia' deve estar entre 0 e 23.")
    if not np.equal(hour.to_numpy(dtype="float64") % 1, 0).all():
        raise ValueError("A coluna 'hora_do_dia' deve conter horas inteiras.")


def preparar_features_gold_ml(
    data: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series]:
    """Valida a Gold ML e separa X e y, sem incluir o alvo nas features."""

    validar_gold_ml(data)
    X = data.loc[:, FEATURE_COLUMNS].copy()

    X["valor"] = pd.to_numeric(X["valor"]).astype("float64")
    for column in BINARY_COLUMNS:
        X[column] = pd.to_numeric(X[column]).astype("int8")
    for column in COUNT_COLUMNS:
        X[column] = pd.to_numeric(X[column]).astype("int64")
    X["hora_do_dia"] = pd.to_numeric(X["hora_do_dia"]).astype("int8")

    y = pd.to_numeric(data[TARGET_COLUMN]).astype("int8").rename(TARGET_COLUMN)

    if list(X.columns) != FEATURE_COLUMNS:
        raise RuntimeError("A ordem das features não corresponde ao contrato congelado da V2.")
    if TARGET_COLUMN in X.columns:
        raise RuntimeError("Vazamento do alvo detectado em X.")

    return X, y


def resumo_gold_ml(X: pd.DataFrame, y: pd.Series) -> dict:
    """Produz um resumo da base preparada."""

    if len(X) != len(y):
        raise ValueError("X e y possuem quantidades diferentes de registros.")
    if list(X.columns) != FEATURE_COLUMNS:
        raise ValueError("X não respeita a ordem de features do LightGBM V2.")

    total = len(y)
    frauds = int(y.sum())
    return {
        "total_registros": total,
        "total_features": len(X.columns),
        "total_fraudes": frauds,
        "total_normais": total - frauds,
        "taxa_fraude": frauds / total if total else 0.0,
        "features": list(X.columns),
    }
