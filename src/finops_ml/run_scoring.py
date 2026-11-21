"""Executor incremental do scoring LightGBM V2 — Grupo 5.

Por padrão, apenas simula o processamento (dry-run). Para persistir resultados,
use --write. A inferência consulta exclusivamente as 10 features do modelo e
as colunas de rastreio; eh_fraude e flag_fraude_sistema não são lidas.

A persistência é feita em tabela separada, por staging + MERGE Delta. A chave
lógica é (id_transacao, sha256_modelo), permitindo reexecuções idempotentes e
histórico separado quando um novo artefato de modelo for aprovado.
"""

from __future__ import annotations

import argparse
import math
import uuid
from typing import Any

import numpy as np
import pandas as pd

from .databricks_loader import TABLE, _connect
from .fraud_scoring import (
    MODEL_FEATURES,
    load_model_artifacts,
    score_transactions,
    summarize_exposure,
)

RESULT_TABLE = "workspace.ml_experiments.gbm_v2_scoring_resultados"
STAGING_TABLE = "workspace.ml_experiments.gbm_v2_scoring_staging"

# A consulta de inferência não seleciona eh_fraude nem flag_fraude_sistema.
INFERENCE_COLUMNS = [
    "id_transacao",
    "step",
    "dia_absoluto",
    *MODEL_FEATURES,
]

CREATE_RESULT_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {RESULT_TABLE} (
    id_transacao STRING NOT NULL,
    step INT NOT NULL,
    dia_absoluto BIGINT,
    fraud_score DOUBLE NOT NULL,
    fraud_alert BOOLEAN NOT NULL,
    status_analise STRING NOT NULL,
    valor_sinalizado DOUBLE NOT NULL,
    nome_modelo STRING NOT NULL,
    sha256_modelo STRING NOT NULL,
    limiar DOUBLE NOT NULL,
    run_id STRING NOT NULL,
    scored_at TIMESTAMP NOT NULL
) USING DELTA
"""

CREATE_STAGING_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {STAGING_TABLE} (
    run_id STRING NOT NULL,
    id_transacao STRING NOT NULL,
    step INT NOT NULL,
    dia_absoluto BIGINT,
    fraud_score DOUBLE NOT NULL,
    fraud_alert BOOLEAN NOT NULL,
    status_analise STRING NOT NULL,
    valor_sinalizado DOUBLE NOT NULL,
    nome_modelo STRING NOT NULL,
    sha256_modelo STRING NOT NULL,
    limiar DOUBLE NOT NULL
) USING DELTA
"""

STAGING_INSERT_COLUMNS = (
    "run_id",
    "id_transacao",
    "step",
    "dia_absoluto",
    "fraud_score",
    "fraud_alert",
    "status_analise",
    "valor_sinalizado",
    "nome_modelo",
    "sha256_modelo",
    "limiar",
)


def build_multirow_insert_sql(row_count: int) -> str:
    """Monta um INSERT multi-row parametrizado para reduzir round-trips.

    Databricks SQL suporta múltiplas tuplas em uma cláusula VALUES.
    Cada linha possui 11 campos; os valores continuam parametrizados.
    """
    if not isinstance(row_count, int) or row_count < 1:
        raise ValueError("row_count deve ser um inteiro positivo.")

    row_placeholders = "(" + ", ".join(["?"] * len(STAGING_INSERT_COLUMNS)) + ")"
    values_clause = ",\n    ".join([row_placeholders] * row_count)
    columns_clause = ", ".join(STAGING_INSERT_COLUMNS)
    return (
        f"INSERT INTO {STAGING_TABLE} ({columns_clause})\n"
        f"VALUES {values_clause}"
    )

MERGE_RESULTS_SQL = f"""
MERGE INTO {RESULT_TABLE} AS target
USING (
    SELECT
        id_transacao,
        step,
        dia_absoluto,
        fraud_score,
        fraud_alert,
        status_analise,
        valor_sinalizado,
        nome_modelo,
        sha256_modelo,
        limiar,
        run_id
    FROM {STAGING_TABLE}
    WHERE run_id = ?
) AS source
ON target.id_transacao = source.id_transacao
AND target.sha256_modelo = source.sha256_modelo
WHEN MATCHED THEN UPDATE SET
    target.step = source.step,
    target.dia_absoluto = source.dia_absoluto,
    target.fraud_score = source.fraud_score,
    target.fraud_alert = source.fraud_alert,
    target.status_analise = source.status_analise,
    target.valor_sinalizado = source.valor_sinalizado,
    target.nome_modelo = source.nome_modelo,
    target.limiar = source.limiar,
    target.run_id = source.run_id,
    target.scored_at = current_timestamp()
WHEN NOT MATCHED THEN INSERT (
    id_transacao,
    step,
    dia_absoluto,
    fraud_score,
    fraud_alert,
    status_analise,
    valor_sinalizado,
    nome_modelo,
    sha256_modelo,
    limiar,
    run_id,
    scored_at
) VALUES (
    source.id_transacao,
    source.step,
    source.dia_absoluto,
    source.fraud_score,
    source.fraud_alert,
    source.status_analise,
    source.valor_sinalizado,
    source.nome_modelo,
    source.sha256_modelo,
    source.limiar,
    source.run_id,
    current_timestamp()
)
"""

DELETE_STAGING_SQL = f"DELETE FROM {STAGING_TABLE} WHERE run_id = ?"


def build_source_query(
    start_step: int,
    end_step: int,
    *,
    exclude_scored: bool,
    limit: int | None = None,
) -> tuple[str, list[Any]]:
    """Monta a consulta de inferência, sem ler rótulos do alvo."""

    if not isinstance(start_step, int) or not isinstance(end_step, int):
        raise TypeError("start_step e end_step devem ser inteiros.")
    if start_step < 1 or end_step < start_step:
        raise ValueError("Intervalo de steps inválido.")
    if limit is not None and (not isinstance(limit, int) or limit < 1):
        raise ValueError("limit deve ser um inteiro positivo.")

    select_columns = ",\n        ".join(f"g.{column}" for column in INFERENCE_COLUMNS)
    query = f"""
        SELECT
            {select_columns}
        FROM {TABLE} AS g
        WHERE g.step BETWEEN ? AND ?
    """
    parameters: list[Any] = [start_step, end_step]

    if exclude_scored:
        query += f"""
          AND NOT EXISTS (
              SELECT 1
              FROM {RESULT_TABLE} AS scored
              WHERE scored.id_transacao = g.id_transacao
                AND scored.sha256_modelo = ?
          )
        """

    query += " ORDER BY g.step, g.id_transacao"
    if limit is not None:
        # limit já foi validado como int positivo; não é texto livre.
        query += f" LIMIT {limit}"

    return query, parameters


def iter_gold_scoring_batches(
    start_step: int,
    end_step: int,
    batch_size: int,
    *,
    exclude_scored: bool,
    model_sha256: str | None = None,
    limit: int | None = None,
):
    """Lê lotes de inferência do Databricks sem selecionar eh_fraude."""

    if not isinstance(batch_size, int) or not 1 <= batch_size <= 10_000:
        raise ValueError("batch_size deve estar entre 1 e 10000.")
    if exclude_scored and not model_sha256:
        raise ValueError("model_sha256 é obrigatório ao excluir scores existentes.")

    query, parameters = build_source_query(
        start_step,
        end_step,
        exclude_scored=exclude_scored,
        limit=limit,
    )
    if exclude_scored:
        parameters.append(model_sha256)

    connection = None
    cursor = None
    try:
        connection = _connect()
        cursor = connection.cursor()
        cursor.execute(query, parameters)

        while True:
            arrow_batch = cursor.fetchmany_arrow(batch_size)
            if arrow_batch is None or arrow_batch.num_rows == 0:
                break

            dataframe = arrow_batch.to_pandas()
            if list(dataframe.columns) != INFERENCE_COLUMNS:
                raise RuntimeError(
                    "As colunas retornadas pela Gold ML não correspondem "
                    "ao contrato de inferência V2. "
                    f"Esperado: {INFERENCE_COLUMNS}; recebido: {list(dataframe.columns)}"
                )
            yield dataframe
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


def build_staging_rows(
    resultado: pd.DataFrame,
    *,
    run_id: str,
    model_name: str,
    model_sha256: str,
    threshold: float,
) -> list[tuple[Any, ...]]:
    """Converte resultados do scoring para os parâmetros de INSERT staging."""

    required = {
        "id_transacao", "step", "dia_absoluto", "fraud_score",
        "fraud_alert", "status_analise", "valor_sinalizado",
    }
    missing = required - set(resultado.columns)
    if missing:
        raise ValueError(f"Colunas ausentes para persistência: {sorted(missing)}")
    if resultado["id_transacao"].isna().any():
        raise ValueError("Existem id_transacao nulos no lote de scoring.")
    if resultado["id_transacao"].duplicated().any():
        raise ValueError("Existem id_transacao duplicados no lote de scoring.")

    rows: list[tuple[Any, ...]] = []
    for row in resultado[
        [
            "id_transacao", "step", "dia_absoluto", "fraud_score",
            "fraud_alert", "status_analise", "valor_sinalizado",
        ]
    ].itertuples(index=False, name=None):
        transaction_id, step, day, score, alert, status, exposure = row
        if pd.isna(step) or pd.isna(score) or pd.isna(exposure):
            raise ValueError("O lote contém step, score ou exposição nulos.")
        day_value = None if pd.isna(day) else int(day)
        score_value = float(score)
        exposure_value = float(exposure)
        if not math.isfinite(score_value) or not 0 <= score_value <= 1:
            raise ValueError("Score inválido para persistência.")
        if not math.isfinite(exposure_value) or exposure_value < 0:
            raise ValueError("Valor sinalizado inválido para persistência.")
        rows.append(
            (
                run_id,
                str(transaction_id),
                int(step),
                day_value,
                score_value,
                bool(alert),
                str(status),
                exposure_value,
                str(model_name),
                str(model_sha256),
                float(threshold),
            )
        )
    return rows


def ensure_result_tables(cursor) -> None:
    """Cria as tabelas Delta de resultados e staging, se necessário."""
    cursor.execute(CREATE_RESULT_TABLE_SQL)
    cursor.execute(CREATE_STAGING_TABLE_SQL)


def insert_staging_rows_chunked(
    cursor,
    rows: list[tuple[Any, ...]],
    *,
    insert_chunk_size: int = 250,
) -> int:
    """Insere várias linhas por comando SQL, com parâmetros vinculados.

    O executemany do conector pode produzir uma execução por linha.
    Aqui agrupamos até `insert_chunk_size` tuplas em um único INSERT ... VALUES.
    """
    if not isinstance(insert_chunk_size, int) or not 1 <= insert_chunk_size <= 500:
        raise ValueError("insert_chunk_size deve estar entre 1 e 500.")

    total = len(rows)
    if total == 0:
        return 0

    expected_width = len(STAGING_INSERT_COLUMNS)
    for index, row in enumerate(rows):
        if len(row) != expected_width:
            raise ValueError(
                f"Linha {index} possui {len(row)} valores; esperado: {expected_width}."
            )

    for start in range(0, total, insert_chunk_size):
        chunk = rows[start:start + insert_chunk_size]
        sql_statement = build_multirow_insert_sql(len(chunk))
        parameters = [value for row in chunk for value in row]
        cursor.execute(sql_statement, parameters)

    return total


def persist_scoring_batch(
    cursor,
    resultado: pd.DataFrame,
    *,
    run_id: str,
    model_name: str,
    model_sha256: str,
    threshold: float,
    insert_chunk_size: int = 250,
) -> int:
    """Persiste um lote via INSERT multi-row + MERGE Delta.

    A staging do run é sempre limpa em finally, inclusive se uma inserção
    ou o MERGE falhar, evitando deixar lotes parciais órfãos quando possível.
    """

    rows = build_staging_rows(
        resultado,
        run_id=run_id,
        model_name=model_name,
        model_sha256=model_sha256,
        threshold=threshold,
    )
    if not rows:
        return 0

    try:
        insert_staging_rows_chunked(
            cursor, rows, insert_chunk_size=insert_chunk_size
        )
        cursor.execute(MERGE_RESULTS_SQL, [run_id])
    finally:
        # Limpa inclusive staging parcial caso uma das inserções falhe.
        cursor.execute(DELETE_STAGING_SQL, [run_id])

    return len(rows)


def run_scoring(
    *,
    start_step: int,
    end_step: int,
    batch_size: int = 5_000,
    limit: int | None = None,
    write: bool = False,
    insert_chunk_size: int = 250,
) -> dict[str, Any]:
    """Executa scoring em lotes. Sem `write`, roda somente em modo prévia."""

    if not isinstance(batch_size, int) or not 1 <= batch_size <= 10_000:
        raise ValueError("batch_size deve estar entre 1 e 10000.")
    if start_step < 1 or end_step < start_step:
        raise ValueError("Intervalo de steps inválido.")
    if limit is not None and limit < 1:
        raise ValueError("limit deve ser positivo.")
    if not isinstance(insert_chunk_size, int) or not 1 <= insert_chunk_size <= 500:
        raise ValueError("insert_chunk_size deve estar entre 1 e 500.")

    modelo, config, metadata = load_model_artifacts()
    model_name = str(metadata.get("modelo", "LightGBM V2"))
    freeze = metadata["congelamento"]
    model_sha256 = str(freeze["sha256_modelo"])
    run_id = str(uuid.uuid4())

    writer_connection = None
    writer_cursor = None
    if write:
        writer_connection = _connect()
        writer_cursor = writer_connection.cursor()
        ensure_result_tables(writer_cursor)

    total = 0
    alerts = 0
    exposure = 0.0
    score_sum = 0.0
    preview_parts: list[pd.DataFrame] = []
    preview_rows = 0

    print("=" * 72)
    print("LIGHTGBM V2 — EXECUTOR DE SCORING")
    print("Modo:", "PERSISTÊNCIA" if write else "PRÉVIA (SEM GRAVAÇÃO)")
    print("Modelo:", model_name)
    print("SHA-256:", model_sha256)
    print("Limiar:", f"{config.threshold:.12f}")
    print(f"Intervalo de steps: {start_step} a {end_step}")
    print("Batch size:", batch_size)
    print("Run ID:", run_id)
    if not write:
        print("A prévia não consulta a tabela de resultados existentes.")
    print("=" * 72)

    try:
        batches = iter_gold_scoring_batches(
            start_step,
            end_step,
            batch_size,
            exclude_scored=write,
            model_sha256=model_sha256 if write else None,
            limit=limit,
        )

        for batch_number, transacoes in enumerate(batches, start=1):
            if transacoes.empty:
                continue

            scored = score_transactions(modelo, transacoes, config)
            summary = summarize_exposure(scored)

            total += int(summary["total_transacoes_analisadas"])
            alerts += int(summary["total_alertas"])
            exposure += float(summary["exposicao_financeira_sinalizada"])
            score_sum += float(scored["fraud_score"].sum())

            if preview_rows < 10:
                preview = scored.head(10 - preview_rows)[
                    ["id_transacao", "step", "fraud_score", "status_analise", "valor_sinalizado"]
                ]
                preview_parts.append(preview)
                preview_rows += len(preview)

            if write and writer_cursor is not None:
                persist_scoring_batch(
                    writer_cursor,
                    scored,
                    run_id=run_id,
                    model_name=model_name,
                    model_sha256=model_sha256,
                    threshold=config.threshold,
                    insert_chunk_size=insert_chunk_size,
                )

            print(
                f"Lote {batch_number}: {len(scored):,} transações | "
                f"alertas: {summary['total_alertas']:,} | "
                f"acumulado: {total:,}",
                flush=True,
            )
    finally:
        if writer_cursor is not None:
            writer_cursor.close()
        if writer_connection is not None:
            writer_connection.close()

    mean_score = score_sum / total if total else 0.0
    summary_result = {
        "run_id": run_id,
        "total_transacoes_analisadas": total,
        "total_alertas": alerts,
        "taxa_alertas": alerts / total if total else 0.0,
        "exposicao_financeira_sinalizada": exposure,
        "score_medio_modelo": mean_score,
        "persistido": bool(write),
        "tabela_resultados": RESULT_TABLE if write else None,
        "sha256_modelo": model_sha256,
    }

    print("\n========== RESUMO DO SCORING ==========")
    for key, value in summary_result.items():
        if isinstance(value, float):
            print(f"{key}: {value:,.8f}")
        else:
            print(f"{key}: {value}")

    if preview_parts:
        print("\n========== AMOSTRA DE RESULTADOS ==========")
        print(pd.concat(preview_parts, ignore_index=True).to_string(index=False))
    if total == 0:
        print("Nenhuma transação pendente encontrada no intervalo informado.")

    return summary_result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Executa o scoring incremental do LightGBM V2 sobre a Gold ML."
    )
    parser.add_argument("--start-step", type=int, required=True)
    parser.add_argument("--end-step", type=int, required=True)
    parser.add_argument("--batch-size", type=int, default=5_000)
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limita o total de registros (útil para o primeiro teste).",
    )
    parser.add_argument(
        "--insert-chunk-size",
        type=int,
        default=250,
        help="Quantidade de linhas por comando INSERT multi-row (1 a 500).",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Grava resultados nas tabelas Delta. Sem esta opção, apenas simula.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_scoring(
        start_step=args.start_step,
        end_step=args.end_step,
        batch_size=args.batch_size,
        limit=args.limit,
        write=args.write,
        insert_chunk_size=args.insert_chunk_size,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
