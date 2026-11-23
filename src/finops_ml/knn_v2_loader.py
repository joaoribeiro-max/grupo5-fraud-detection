
# ============================================================
# KNN V2 - DATABRICKS LOADER
# Projeto: Grupo 5 - Cidade Inteligente
# Origem: workspace.gold_ml.knn_transacoes
# Objetivo: carregar as features Gold para inferência.
# ============================================================

from __future__ import annotations

from typing import Iterator

import pandas as pd

# Reutilizar a conexão oficial já implementada no projeto.
from .databricks_loader import _connect


# ============================================================
# 1. CONTRATO DA GOLD KNN V2
# ============================================================

KNN_TABLE = "workspace.gold_ml.knn_transacoes"

# Sete features na ordem exata do modelo congelado.
KNN_FEATURES = [
    "eh_transferencia",
    "eh_conta_nova",
    "freq_destino_24h_norm",
    "eh_rajada_destino",
    "valor_log_norm",
    "hora_sin",
    "hora_cos",
]

# Colunas auxiliares necessárias para rastreabilidade.
# O target eh_fraude não será consultado na inferência.
KNN_INFERENCE_COLUMNS = [
    "id_transacao",
    "step",
    "dia_absoluto",
    *KNN_FEATURES,
]


# ============================================================
# 2. VALIDAÇÃO DO LOTE ARROW
# ============================================================

def _arrow_to_dataframe(
    arrow_batch,
) -> pd.DataFrame:
    """Converte o lote Arrow e valida o contrato das colunas."""

    if arrow_batch is None or arrow_batch.num_rows == 0:
        return pd.DataFrame(columns=KNN_INFERENCE_COLUMNS)

    dataframe = arrow_batch.to_pandas()

    if list(dataframe.columns) != KNN_INFERENCE_COLUMNS:
        raise RuntimeError(
            "As colunas retornadas pela Gold KNN não correspondem "
            "ao contrato de inferência. "
            f"Esperado: {KNN_INFERENCE_COLUMNS}; "
            f"Recebido: {list(dataframe.columns)}"
        )

    if dataframe["id_transacao"].isna().any():
        raise ValueError(
            "Existem identificadores de transação nulos."
        )

    if dataframe["id_transacao"].duplicated().any():
        raise ValueError(
            "Existem IDs duplicados no lote recebido."
        )

    return dataframe


# ============================================================
# 3. CONSULTA DA GOLD KNN V2 EM LOTES
# ============================================================

def iter_gold_knn_v2_batches(
    start_step: int,
    end_step: int,
    batch_size: int = 5_000,
) -> Iterator[pd.DataFrame]:
    """
    Consulta a Gold KNN em lotes utilizando PyArrow.

    Não seleciona eh_fraude nem flag_fraude_sistema.
    Preserva as features calculadas pela Engenharia de Dados.
    """

    # Validar os limites temporais.
    if not isinstance(start_step, int) or not isinstance(end_step, int):
        raise TypeError("Os steps devem ser inteiros.")

    if start_step < 1 or end_step < start_step:
        raise ValueError("Intervalo de steps inválido.")

    # Validar o tamanho dos lotes.
    if not isinstance(batch_size, int) or not 1 <= batch_size <= 10_000:
        raise ValueError(
            "O tamanho do lote deve estar entre 1 e 10000."
        )

    # Montar a consulta com colunas explícitas.
    # Não utilizar SELECT *.
    select_columns = ", ".join(
        KNN_INFERENCE_COLUMNS
    )

    query = f"""
        SELECT
            {select_columns}
        FROM {KNN_TABLE}
        WHERE step BETWEEN ? AND ?
        ORDER BY step, id_transacao
    """

    connection = None
    cursor = None

    try:
        # Reutilizar a conexão oficial do projeto.
        connection = _connect()
        cursor = connection.cursor()

        print(
            f"Consultando Gold KNN: steps {start_step} a {end_step}",
            flush=True,
        )

        cursor.execute(
            query,
            [start_step, end_step],
        )

        # Recuperar os registros em lotes Arrow.
        while True:

            arrow_batch = cursor.fetchmany_arrow(batch_size)

            if arrow_batch is None or arrow_batch.num_rows == 0:
                break

            dataframe = _arrow_to_dataframe(
                arrow_batch
            )

            yield dataframe

    finally:
        # Encerrar os recursos mesmo em caso de erro.
        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()


# ============================================================
# 4. CONSULTA DE UMA PEQUENA AMOSTRA
# ============================================================

def fetch_gold_knn_v2_sample(
    limit: int = 5,
) -> pd.DataFrame:
    """Busca uma pequena amostra da Gold KNN para diagnóstico."""

    if not isinstance(limit, int) or not 1 <= limit <= 1_000:
        raise ValueError(
            "O limite deve estar entre 1 e 1000."
        )

    select_columns = ", ".join(
        KNN_INFERENCE_COLUMNS
    )

    query = f"""
        SELECT
            {select_columns}
        FROM {KNN_TABLE}
        ORDER BY step, id_transacao
        LIMIT {limit}
    """

    connection = None
    cursor = None

    try:
        connection = _connect()
        cursor = connection.cursor()

        cursor.execute(query)

        return pd.DataFrame(
            cursor.fetchall(),
            columns=KNN_INFERENCE_COLUMNS,
        )

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()
