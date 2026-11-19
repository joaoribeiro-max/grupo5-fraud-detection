
"""Preparação e validação das features da Gold ML para LightGBM V2."""

import numpy as np
import pandas as pd


TARGET_COLUMN = "eh_fraude"

# Identificação da operação, não utilizada no treinamento.
IDENTIFIER_COLUMNS = ["id_transacao", "step"]

# Features selecionadas para o primeiro experimento da V2.
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

REQUIRED_COLUMNS = FEATURE_COLUMNS + [TARGET_COLUMN]


def validar_gold_ml(data: pd.DataFrame) -> None:
    """Valida os campos necessários antes do treinamento."""

    if not isinstance(data, pd.DataFrame):
        raise TypeError("A entrada deve ser um DataFrame.")

    if data.empty:
        raise ValueError("A base recebida está vazia.")

    if data.columns.duplicated().any():
        raise ValueError("Existem nomes de colunas duplicados.")

    ausentes = set(REQUIRED_COLUMNS) - set(data.columns)

    if ausentes:
        raise ValueError(
            f"Colunas obrigatórias ausentes: {sorted(ausentes)}"
        )

    for column in REQUIRED_COLUMNS:
        valores = pd.to_numeric(data[column], errors="coerce")

        if valores.isna().any():
            raise ValueError(
                f"A coluna {column} possui valores ausentes ou inválidos."
            )

        if not np.isfinite(valores.to_numpy(dtype=float)).all():
            raise ValueError(
                f"A coluna {column} possui valores não finitos."
            )

    if (pd.to_numeric(data["valor"]) < 0).any():
        raise ValueError("Existem valores financeiros negativos.")

    # Verificação das variáveis binárias.
    for column in BINARY_COLUMNS + [TARGET_COLUMN]:
        valores = pd.to_numeric(data[column])

        if not valores.isin([0, 1]).all():
            raise ValueError(
                f"A coluna {column} deve conter somente 0 ou 1."
            )

    # Cada transação deve possuir exatamente um tipo.
    soma_tipos = data[
        [
            "eh_pagamento",
            "eh_deposito",
            "eh_debito",
            "eh_saque",
            "eh_transferencia",
        ]
    ].apply(pd.to_numeric).sum(axis=1)

    if not soma_tipos.eq(1).all():
        raise ValueError(
            "Existem transações com tipos inválidos ou múltiplos."
        )

    recebimentos = pd.to_numeric(
        data["qtd_recebimentos_anterior"]
    )

    if (recebimentos < 0).any():
        raise ValueError(
            "qtd_recebimentos_anterior não pode ser negativo."
        )

    # Essas features são contagens e precisam ser inteiras.
    if not np.equal(recebimentos % 1, 0).all():
        raise ValueError(
            "qtd_recebimentos_anterior deve conter números inteiros."
        )

    hora = pd.to_numeric(data["hora_do_dia"])
    dia = pd.to_numeric(data["dia_semana"])

    if not hora.between(0, 23).all():
        raise ValueError("hora_do_dia deve estar entre 0 e 23.")

    if not dia.between(1, 7).all():
        raise ValueError("dia_semana deve estar entre 1 e 7.")


def preparar_features_gold_ml(
    data: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series]:
    """
    Valida a Gold ML e separa as features do alvo.

    Retorna:
        X: matriz numérica utilizada pelo LightGBM.
        y: rótulo histórico de fraude.
    """

    validar_gold_ml(data)

    X = data[FEATURE_COLUMNS].copy()

    # Tipagem numérica explícita.
    X["valor"] = pd.to_numeric(
        X["valor"]
    ).astype("float64")

    for column in BINARY_COLUMNS:
        X[column] = pd.to_numeric(
            X[column]
        ).astype("int8")

    X["qtd_recebimentos_anterior"] = pd.to_numeric(
        X["qtd_recebimentos_anterior"]
    ).astype("int64")

    X["hora_do_dia"] = pd.to_numeric(
        X["hora_do_dia"]
    ).astype("int8")

    X["dia_semana"] = pd.to_numeric(
        X["dia_semana"]
    ).astype("int8")

    # O alvo é separado e nunca entra em X.
    y = pd.to_numeric(
        data[TARGET_COLUMN]
    ).astype("int8").rename(TARGET_COLUMN)

    if list(X.columns) != FEATURE_COLUMNS:
        raise RuntimeError(
            "A ordem das features não corresponde ao contrato da V2."
        )

    if TARGET_COLUMN in X.columns:
        raise RuntimeError("Vazamento do alvo detectado em X.")

    return X, y


def resumo_gold_ml(
    X: pd.DataFrame,
    y: pd.Series,
) -> dict:
    """Produz um resumo da base preparada."""

    if len(X) != len(y):
        raise ValueError("X e y possuem quantidades diferentes de registros.")

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
