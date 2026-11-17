"""Preparacao e validacao das features da Gold ML para LightGBM V2."""

import numpy as np
import pandas as pd

TARGET_COLUMN = "eh_fraude"

FEATURE_COLUMNS = [
    "valor",
    "eh_pagamento",
    "eh_deposito",
    "eh_debito",
    "eh_saque",
    "eh_transferencia",
    "destino_eh_comercio",
    "qtd_recebimentos_anterior",
    "hora_do_dia",
    "dia_semana",
]

BINARY_COLUMNS = [
    "eh_pagamento",
    "eh_deposito",
    "eh_debito",
    "eh_saque",
    "eh_transferencia",
    "destino_eh_comercio",
]


def validar_gold_ml(data: pd.DataFrame) -> None:
    """Valida os dados antes da preparacao das features."""

    if not isinstance(data, pd.DataFrame):
        raise TypeError("A entrada deve ser um DataFrame.")

    if data.empty:
        raise ValueError("A base esta vazia.")

    if data.columns.duplicated().any():
        raise ValueError("Existem colunas duplicadas.")

    obrigatorias = FEATURE_COLUMNS + [TARGET_COLUMN]
    ausentes = set(obrigatorias) - set(data.columns)

    if ausentes:
        raise ValueError(f"Colunas ausentes: {sorted(ausentes)}")

    for coluna in obrigatorias:
        valores = pd.to_numeric(data[coluna], errors="coerce")

        if valores.isna().any():
            raise ValueError(f"Valores ausentes ou invalidos: {coluna}")

        if not np.isfinite(valores.to_numpy(dtype=float)).all():
            raise ValueError(f"Valores nao finitos: {coluna}")

    if (data["valor"].astype(float) < 0).any():
        raise ValueError("Existem valores financeiros negativos.")

    for coluna in BINARY_COLUMNS + [TARGET_COLUMN]:
        if not data[coluna].isin([0, 1]).all():
            raise ValueError(f"{coluna} deve conter somente 0 ou 1.")

    tipos = data[
        ["eh_pagamento", "eh_deposito", "eh_debito",
         "eh_saque", "eh_transferencia"]
    ].sum(axis=1)

    if not tipos.eq(1).all():
        raise ValueError("Existem tipos de transacao inconsistentes.")

    recebimentos = data["qtd_recebimentos_anterior"]

    if (recebimentos < 0).any():
        raise ValueError("Quantidade de recebimentos negativa.")

    if not (recebimentos % 1 == 0).all():
        raise ValueError("Quantidade de recebimentos deve ser inteira.")

    if not data["hora_do_dia"].between(0, 23).all():
        raise ValueError("Hora do dia fora do intervalo 0-23.")

    if not data["dia_semana"].between(1, 7).all():
        raise ValueError("Dia da semana fora do intervalo 1-7.")


def preparar_features_gold_ml(
    data: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series]:
    """Separa as dez features do alvo de fraude."""

    validar_gold_ml(data)

    X = data[FEATURE_COLUMNS].copy()

    X["valor"] = X["valor"].astype("float64")

    for coluna in BINARY_COLUMNS:
        X[coluna] = X[coluna].astype("int8")

    X["qtd_recebimentos_anterior"] = (
        X["qtd_recebimentos_anterior"].astype("int64")
    )

    X["hora_do_dia"] = X["hora_do_dia"].astype("int8")
    X["dia_semana"] = X["dia_semana"].astype("int8")

    y = data[TARGET_COLUMN].astype("int8").rename(TARGET_COLUMN)

    if TARGET_COLUMN in X.columns:
        raise RuntimeError("Vazamento do alvo detectado.")

    return X, y


def resumo_gold_ml(X: pd.DataFrame, y: pd.Series) -> dict:
    """Resume a base preparada para treinamento."""

    if len(X) != len(y):
        raise ValueError("X e y possuem tamanhos diferentes.")

    total = len(y)
    fraudes = int(y.sum())

    return {
        "total_registros": total,
        "total_features": len(X.columns),
        "total_fraudes": fraudes,
        "total_normais": total - fraudes,
        "taxa_fraude": fraudes / total if total else 0.0,
        "features": list(X.columns),
    }
