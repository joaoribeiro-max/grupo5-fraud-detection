
"""Conector de leitura da camada Gold ML no Databricks."""

import os
from pathlib import Path
from typing import Iterator

import pandas as pd
from databricks import sql
from dotenv import load_dotenv


# Localização da raiz do projeto
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

# Fonte oficial de dados preparada pela Engenharia de Dados
TABLE = "workspace.gold_ml.gbm_transacoes"

# Contrato de dados da Gold ML
COLUMNS = [
    "id_transacao",
    "step",
    "eh_pagamento",
    "eh_deposito",
    "eh_debito",
    "eh_saque",
    "eh_transferencia",
    "valor",
    "destino_eh_comercio",
    "qtd_recebimentos_anterior",
    "hora_do_dia",
    "eh_madrugada",
    "eh_manha",
    "eh_tarde",
    "eh_noite",
    "dia_semana",
    "eh_final_de_semana",
    "flag_fraude_sistema",
    "eh_fraude",
]


def _connect():
    """Estabelece conexão com o SQL Warehouse."""

    keys = [
        "DATABRICKS_SERVER_HOSTNAME",
        "DATABRICKS_HTTP_PATH",
        "DATABRICKS_TOKEN",
    ]

    missing = [key for key in keys if not os.getenv(key)]

    if missing:
        raise RuntimeError(
            f"Credenciais ausentes no .env: {missing}"
        )

    return sql.connect(
        server_hostname=os.environ["DATABRICKS_SERVER_HOSTNAME"],
        http_path=os.environ["DATABRICKS_HTTP_PATH"],
        access_token=os.environ["DATABRICKS_TOKEN"],
    )


def _select_columns() -> str:
    """Retorna as colunas autorizadas para leitura."""
    return ", ".join(COLUMNS)


def fetch_gold_ml_sample(limit: int = 5) -> pd.DataFrame:
    """Busca uma amostra da tabela Gold ML."""

    if not isinstance(limit, int) or not 1 <= limit <= 1000:
        raise ValueError("O limite deve estar entre 1 e 1000.")

    query = f"""
        SELECT {_select_columns()}
        FROM {TABLE}
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
            columns=COLUMNS,
        )

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


def iter_gold_ml_batches(
    start_step: int,
    end_step: int,
    batch_size: int = 100_000,
) -> Iterator[pd.DataFrame]:
    """
    Lê a Gold ML em lotes, respeitando o intervalo temporal.
    Evita carregar toda a tabela na memória de uma só vez.
    """

    if not isinstance(start_step, int) or not isinstance(end_step, int):
        raise TypeError("Os steps devem ser inteiros.")

    if start_step < 1 or end_step < start_step:
        raise ValueError("Intervalo temporal inválido.")

    if not 1 <= batch_size <= 500_000:
        raise ValueError("Batch size deve estar entre 1 e 500000.")

    query = f"""
        SELECT {_select_columns()}
        FROM {TABLE}
        WHERE step BETWEEN {start_step} AND {end_step}
    """

    connection = None
    cursor = None

    try:
        connection = _connect()
        cursor = connection.cursor()
        cursor.execute(query)

        while True:
            rows = cursor.fetchmany(batch_size)

            if not rows:
                break

            yield pd.DataFrame(rows, columns=COLUMNS)

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()

def iter_gold_ml_training_sample(
    batch_size: int = 10_000,
    normal_sample_pct: int = 2,
) -> Iterator[pd.DataFrame]:
    """
    Extrai o treino preservando todas as fraudes e amostrando
    deterministicamente uma parcela das transações normais.

    sample_weight corrige a probabilidade de seleção:
    1 para fraudes e 100/pct para transações normais.
    """

    if not 1 <= normal_sample_pct <= 100:
        raise ValueError("Percentual deve estar entre 1 e 100.")

    if not 1 <= batch_size <= 50_000:
        raise ValueError("Batch size deve estar entre 1 e 50000.")

    peso_normal = 100.0 / normal_sample_pct

    query = f"""
        SELECT
            {_select_columns()},
            CASE
                WHEN eh_fraude = 1 THEN 1.0
                ELSE {peso_normal}
            END AS sample_weight
        FROM {TABLE}
        WHERE step BETWEEN 1 AND 520
          AND (
              eh_fraude = 1
              OR (
                  eh_fraude = 0
                  AND pmod(xxhash64(id_transacao), 100)
                      < {normal_sample_pct}
              )
          )
    """

    connection = None
    cursor = None

    try:
        connection = _connect()
        cursor = connection.cursor()
        cursor.execute(query)

        columns = COLUMNS + ["sample_weight"]

        while True:
            rows = cursor.fetchmany(batch_size)

            if not rows:
                break

            yield pd.DataFrame(rows, columns=columns)

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()
