
# ============================================================
# KNN V2 - EXECUTOR OPERACIONAL DE SCORING
# Projeto: Grupo 5 - Cidade Inteligente
#
# Funcionalidades:
# - Leitura incremental da Gold KNN no Databricks.
# - Inferência com classificador e scaler congelados.
# - Processamento em lotes Arrow.
# - Prévia sem gravação por padrão.
# - Persistência opcional com --write.
# - Staging e MERGE Delta.
# - Identificação por ID e SHA-256 do modelo.
#
# O target eh_fraude não é consultado na inferência.
# ============================================================

from __future__ import annotations

import argparse
import math
import uuid

from typing import Any, Iterator

import pandas as pd

from .databricks_loader import _connect

from .knn_v2_loader import (
    KNN_TABLE,
    KNN_INFERENCE_COLUMNS,
)

from .knn_v2_predictor import (
    load_knn_v2_artifacts,
    score_knn_v2_transactions,
    summarize_knn_v2,
)


# ============================================================
# 1. CONFIGURAÇÃO DAS TABELAS
# ============================================================

RESULT_TABLE = (
    "workspace.ml_experiments.knn_v2_scoring_resultados"
)

STAGING_TABLE = (
    "workspace.ml_experiments.knn_v2_scoring_staging"
)

MODEL_NAME = "KNN V2"


# ============================================================
# 2. DDL DAS TABELAS DELTA
# ============================================================

CREATE_RESULT_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {RESULT_TABLE} (
    id_transacao STRING NOT NULL,
    step INT NOT NULL,
    dia_absoluto BIGINT,
    fraud_score DOUBLE NOT NULL,
    fraud_alert BOOLEAN NOT NULL,
    status_analise STRING NOT NULL,
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
    nome_modelo STRING NOT NULL,
    sha256_modelo STRING NOT NULL,
    limiar DOUBLE NOT NULL
) USING DELTA
"""


# ============================================================
# 3. CONTRATO DE PERSISTÊNCIA
# ============================================================

STAGING_INSERT_COLUMNS = (
    "run_id",
    "id_transacao",
    "step",
    "dia_absoluto",
    "fraud_score",
    "fraud_alert",
    "status_analise",
    "nome_modelo",
    "sha256_modelo",
    "limiar",
)


# ============================================================
# 4. CONSULTA DE ORIGEM
# ============================================================

def build_source_query(
    start_step: int,
    end_step: int,
    *,
    exclude_scored: bool,
    model_sha256: str | None = None,
    limit: int | None = None,
) -> tuple[str, list[Any]]:
    """
    Monta a consulta da Gold KNN V2.

    Quando exclude_scored=True, ignora transações já
    registradas para o mesmo SHA-256.

    A inferência não consulta o target eh_fraude.
    """

    # Validar os tipos dos steps.
    if (
        not isinstance(start_step, int)
        or isinstance(start_step, bool)
        or not isinstance(end_step, int)
        or isinstance(end_step, bool)
    ):
        raise TypeError("Os steps devem ser inteiros.")

    # Validar o intervalo temporal.
    if start_step < 1 or end_step < start_step:
        raise ValueError("Intervalo temporal inválido.")

    # Validar o limite opcional.
    if limit is not None:
        if (
            not isinstance(limit, int)
            or isinstance(limit, bool)
            or limit < 1
        ):
            raise ValueError(
                "limit deve ser um inteiro positivo."
            )

    # Validar o filtro de registros já processados.
    if exclude_scored:
        if not model_sha256:
            raise ValueError(
                "model_sha256 é obrigatório ao excluir registros processados."
            )

    # Selecionar somente as colunas autorizadas.
    select_columns = ",\n        ".join(
        f"g.{column}"
        for column in KNN_INFERENCE_COLUMNS
    )

    query = f"""
        SELECT
            {select_columns}
        FROM {KNN_TABLE} AS g
        WHERE g.step BETWEEN ? AND ?
    """

    parameters: list[Any] = [
        start_step,
        end_step,
    ]

    # Excluir registros já gravados para o mesmo modelo.
    if exclude_scored:

        query += f"""
            AND NOT EXISTS (
                SELECT 1
                FROM {RESULT_TABLE} AS scored
                WHERE scored.id_transacao = g.id_transacao
                  AND scored.sha256_modelo = ?
            )
        """

        parameters.append(model_sha256)

    # Ordenar de forma determinística.
    query += """
        ORDER BY g.step, g.id_transacao
    """

    # LIMIT recebe somente inteiro previamente validado.
    if limit is not None:
        query += f" LIMIT {limit}"

    return query, parameters


# ============================================================
# 5. LEITURA DA GOLD EM LOTES
# ============================================================

def iter_knn_v2_batches(
    start_step: int,
    end_step: int,
    batch_size: int = 5_000,
    *,
    exclude_scored: bool = False,
    model_sha256: str | None = None,
    limit: int | None = None,
) -> Iterator[pd.DataFrame]:
    """
    Consulta a Gold KNN em lotes usando PyArrow.

    Retorna somente os campos necessários para a inferência.
    """

    # Validar tamanho do lote.
    if (
        not isinstance(batch_size, int)
        or isinstance(batch_size, bool)
        or not 1 <= batch_size <= 10_000
    ):
        raise ValueError(
            "batch_size deve estar entre 1 e 10000."
        )

    # Montar a consulta.
    query, parameters = build_source_query(
        start_step,
        end_step,
        exclude_scored=exclude_scored,
        model_sha256=model_sha256,
        limit=limit,
    )

    connection = None
    cursor = None

    try:
        # Reutilizar a conexão oficial do projeto.
        connection = _connect()
        cursor = connection.cursor()

        cursor.execute(
            query,
            parameters,
        )

        # Recuperar os lotes Arrow.
        while True:

            arrow_batch = cursor.fetchmany_arrow(
                batch_size
            )

            if (
                arrow_batch is None
                or arrow_batch.num_rows == 0
            ):
                break

            dataframe = arrow_batch.to_pandas()

            # Validar o contrato das colunas.
            if list(dataframe.columns) != KNN_INFERENCE_COLUMNS:
                raise RuntimeError(
                    "As colunas recebidas da Gold KNN divergem "
                    "do contrato de inferência. "
                    f"Esperado: {KNN_INFERENCE_COLUMNS}; "
                    f"recebido: {list(dataframe.columns)}"
                )

            # Validar identificadores.
            if dataframe["id_transacao"].isna().any():
                raise ValueError(
                    "Existem IDs de transação nulos."
                )

            if dataframe["id_transacao"].duplicated().any():
                raise ValueError(
                    "Existem IDs duplicados no lote."
                )

            yield dataframe

    finally:
        # Fechar os recursos mesmo se ocorrer uma falha.
        try:
            if cursor is not None:
                cursor.close()
        finally:
            if connection is not None:
                connection.close()


# ============================================================
# 6. CRIAÇÃO DAS TABELAS
# ============================================================

def ensure_result_tables(cursor) -> None:
    """Cria as tabelas Delta caso ainda não existam."""

    cursor.execute(CREATE_RESULT_TABLE_SQL)
    cursor.execute(CREATE_STAGING_TABLE_SQL)


# ============================================================
# 7. CONSTRUÇÃO DO INSERT MULTILINHA
# ============================================================

def build_multirow_insert_sql(
    row_count: int,
) -> str:
    """Monta INSERT com parâmetros vinculados."""

    if (
        not isinstance(row_count, int)
        or isinstance(row_count, bool)
        or row_count < 1
    ):
        raise ValueError(
            "row_count deve ser um inteiro positivo."
        )

    # Cada linha possui dez campos.
    placeholders = (
        "("
        + ", ".join(["?"] * len(STAGING_INSERT_COLUMNS))
        + ")"
    )

    values_clause = ",\n".join(
        [placeholders] * row_count
    )

    columns_clause = ", ".join(
        STAGING_INSERT_COLUMNS
    )

    return (
        f"INSERT INTO {STAGING_TABLE} "
        f"({columns_clause})\n"
        f"VALUES {values_clause}"
    )


# ============================================================
# 8. MERGE DA STAGING PARA A TABELA DEFINITIVA
# ============================================================

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
    nome_modelo,
    sha256_modelo,
    limiar,
    run_id,
    scored_at
)
VALUES (
    source.id_transacao,
    source.step,
    source.dia_absoluto,
    source.fraud_score,
    source.fraud_alert,
    source.status_analise,
    source.nome_modelo,
    source.sha256_modelo,
    source.limiar,
    source.run_id,
    current_timestamp()
)
"""

DELETE_STAGING_SQL = (
    f"DELETE FROM {STAGING_TABLE} WHERE run_id = ?"
)


# ============================================================
# 9. CONVERSÃO DOS RESULTADOS PARA STAGING
# ============================================================

def build_staging_rows(
    resultado: pd.DataFrame,
    *,
    run_id: str,
    model_sha256: str,
    threshold: float,
) -> list[tuple[Any, ...]]:
    """Converte as previsões em linhas para persistência."""

    if not isinstance(resultado, pd.DataFrame):
        raise TypeError(
            "resultado deve ser um pandas.DataFrame."
        )

    required = {
        "id_transacao",
        "step",
        "dia_absoluto",
        "fraud_score",
        "fraud_alert",
        "status_analise",
    }

    missing = required - set(resultado.columns)

    if missing:
        raise ValueError(
            f"Colunas ausentes no resultado: {sorted(missing)}"
        )

    # Validar identificadores.
    if resultado["id_transacao"].isna().any():
        raise ValueError(
            "Existem IDs nulos no resultado."
        )

    if resultado["id_transacao"].duplicated().any():
        raise ValueError(
            "Existem IDs duplicados no resultado."
        )

    if resultado["id_transacao"].astype(str).str.strip().eq("").any():
        raise ValueError(
            "Existem IDs vazios no resultado."
        )

    # Validar identificador da execução.
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("run_id deve ser uma string não vazia.")

    # Validar SHA-256.
    if (
        not isinstance(model_sha256, str)
        or len(model_sha256) != 64
        or any(
            caractere not in "0123456789abcdefABCDEF"
            for caractere in model_sha256
        )
    ):
        raise ValueError("SHA-256 do modelo inválido.")

    # Validar limiar.
    threshold_value = float(threshold)

    if (
        not math.isfinite(threshold_value)
        or not 0 <= threshold_value <= 1
    ):
        raise ValueError("Limiar inválido.")

    rows: list[tuple[Any, ...]] = []

    selected_columns = resultado[
        [
            "id_transacao",
            "step",
            "dia_absoluto",
            "fraud_score",
            "fraud_alert",
            "status_analise",
        ]
    ]

    for row in selected_columns.itertuples(
        index=False,
        name=None,
    ):

        transaction_id, step, day, score, alert, status = row

        # Validar campos obrigatórios.
        if (
            pd.isna(step)
            or pd.isna(score)
            or pd.isna(alert)
            or pd.isna(status)
        ):
            raise ValueError(
                "O lote possui campos obrigatórios nulos."
            )

        # Validar step.
        step_value = float(step)

        if (
            not math.isfinite(step_value)
            or not step_value.is_integer()
            or step_value < 1
        ):
            raise ValueError(
                "Step inválido para persistência."
            )

        # Validar score.
        score_value = float(score)

        if (
            not math.isfinite(score_value)
            or not 0 <= score_value <= 1
        ):
            raise ValueError(
                "Score inválido para persistência."
            )

        # Validar flag de alerta.
        if isinstance(alert, bool):
            alert_value = alert

        elif type(alert).__name__ == "bool_":
            alert_value = bool(alert)

        elif isinstance(alert, int) and alert in (0, 1):
            alert_value = bool(alert)

        else:
            raise ValueError(
                "Flag de alerta deve ser booleana ou 0/1."
            )

        # Verificar consistência entre score e limiar.
        if alert_value != (score_value >= threshold_value):
            raise ValueError(
                "O alerta diverge do limiar congelado."
            )

        # Validar o status da análise.
        status_value = str(status)

        status_esperado = (
            "ALERTA" if alert_value else "SEM_ALERTA"
        )

        if status_value != status_esperado:
            raise ValueError(
                "O status da análise diverge do alerta."
            )

        # Tratar dia absoluto opcional.
        if pd.isna(day):
            day_value = None

        else:
            day_number = float(day)

            if (
                not math.isfinite(day_number)
                or not day_number.is_integer()
            ):
                raise ValueError(
                    "Dia absoluto inválido."
                )

            day_value = int(day_number)

        # Converter os valores para tipos nativos do Python.
        rows.append(
            (
                run_id,
                str(transaction_id).strip(),
                int(step_value),
                day_value,
                score_value,
                alert_value,
                status_value,
                MODEL_NAME,
                model_sha256.lower(),
                threshold_value,
            )
        )

    return rows


# ============================================================
# 10. INSERÇÃO EM LOTES NA STAGING
# ============================================================

def insert_staging_rows_chunked(
    cursor,
    rows: list[tuple[Any, ...]],
    insert_chunk_size: int = 250,
) -> int:
    """Insere várias linhas por comando SQL parametrizado."""

    if (
        not isinstance(insert_chunk_size, int)
        or isinstance(insert_chunk_size, bool)
        or not 1 <= insert_chunk_size <= 500
    ):
        raise ValueError(
            "insert_chunk_size deve estar entre 1 e 500."
        )

    total = len(rows)

    if total == 0:
        return 0

    expected_width = len(STAGING_INSERT_COLUMNS)

    for index, row in enumerate(rows):

        if len(row) != expected_width:
            raise ValueError(
                f"Linha {index} possui {len(row)} valores; "
                f"esperado: {expected_width}."
            )

    for start in range(0, total, insert_chunk_size):

        chunk = rows[
            start:start + insert_chunk_size
        ]

        statement = build_multirow_insert_sql(
            len(chunk)
        )

        parameters = [
            value
            for row in chunk
            for value in row
        ]

        cursor.execute(
            statement,
            parameters,
        )

    return total


# ============================================================
# 11. PERSISTÊNCIA COM MERGE DELTA
# ============================================================

def persist_scoring_batch(
    cursor,
    resultado: pd.DataFrame,
    *,
    run_id: str,
    model_sha256: str,
    threshold: float,
    insert_chunk_size: int = 250,
) -> int:
    """
    Persiste um lote por INSERT multi-row e MERGE Delta.

    Se o DataFrame estiver vazio, retorna zero sem executar SQL.

    A staging do run é limpa ao final da operação.
    """

    # Validar o tipo da entrada.
    if not isinstance(resultado, pd.DataFrame):
        raise TypeError(
            "resultado deve ser um pandas.DataFrame."
        )

    # CORREÇÃO PRINCIPAL:
    # Não tentar validar colunas nem persistir um lote vazio.
    if resultado.empty:
        return 0

    # Construir as linhas para inserção na staging.
    rows = build_staging_rows(
        resultado,
        run_id=run_id,
        model_sha256=model_sha256,
        threshold=threshold,
    )

    if not rows:
        return 0

    try:
        # Inserir registros na staging.
        insert_staging_rows_chunked(
            cursor,
            rows,
            insert_chunk_size=insert_chunk_size,
        )

        # Atualizar ou inserir na tabela definitiva.
        cursor.execute(
            MERGE_RESULTS_SQL,
            [run_id],
        )

    finally:
        # Limpar a staging mesmo em caso de falha.
        cursor.execute(
            DELETE_STAGING_SQL,
            [run_id],
        )

    return len(rows)


# ============================================================
# 12. EXECUÇÃO DO SCORING
# ============================================================

def run_knn_v2_scoring(
    *,
    start_step: int,
    end_step: int,
    batch_size: int = 5_000,
    limit: int | None = None,
    write: bool = False,
    insert_chunk_size: int = 250,
) -> dict[str, Any]:
    """
    Executa o scoring KNN V2 em lotes.

    Sem write=True:
        Executa somente uma prévia, sem persistência.

    Com write=True:
        Exclui registros previamente processados para o mesmo hash
        e persiste os resultados via staging + MERGE Delta.
    """

    # Validar os parâmetros temporais.
    if (
        not isinstance(start_step, int)
        or isinstance(start_step, bool)
        or not isinstance(end_step, int)
        or isinstance(end_step, bool)
    ):
        raise TypeError(
            "start_step e end_step devem ser inteiros."
        )

    if start_step < 1 or end_step < start_step:
        raise ValueError(
            "Intervalo temporal inválido."
        )

    # Validar tamanho do lote.
    if (
        not isinstance(batch_size, int)
        or isinstance(batch_size, bool)
        or not 1 <= batch_size <= 10_000
    ):
        raise ValueError(
            "batch_size deve estar entre 1 e 10000."
        )

    # Validar limite opcional.
    if limit is not None:
        if (
            not isinstance(limit, int)
            or isinstance(limit, bool)
            or limit < 1
        ):
            raise ValueError(
                "limit deve ser um inteiro positivo."
            )

    # Validar tamanho dos comandos de inserção.
    if (
        not isinstance(insert_chunk_size, int)
        or isinstance(insert_chunk_size, bool)
        or not 1 <= insert_chunk_size <= 500
    ):
        raise ValueError(
            "insert_chunk_size deve estar entre 1 e 500."
        )

    # Carregar modelo, scaler e metadados congelados.
    artifacts = load_knn_v2_artifacts()

    threshold = artifacts.threshold
    model_sha256 = artifacts.model_sha256

    run_id = str(uuid.uuid4())

    writer_connection = None
    writer_cursor = None

    # Criar as tabelas somente quando houver persistência solicitada.
    if write:

        writer_connection = _connect()

        try:
            writer_cursor = writer_connection.cursor()

            ensure_result_tables(
                writer_cursor
            )

        except Exception:
            try:
                if writer_cursor is not None:
                    writer_cursor.close()
            finally:
                writer_connection.close()

            raise

    # Inicializar os acumuladores.
    total = 0
    alerts = 0
    score_sum = 0.0

    preview_parts: list[pd.DataFrame] = []
    preview_rows = 0

    print("=" * 72)
    print("KNN V2 - EXECUTOR OPERACIONAL")

    print(
        "Modo:",
        "PERSISTÊNCIA" if write else "PRÉVIA (SEM GRAVAÇÃO)",
    )

    print("Tabela Gold:", KNN_TABLE)
    print("Modelo:", MODEL_NAME)
    print("SHA-256:", model_sha256)
    print("Limiar:", f"{threshold:.12f}")
    print(f"Intervalo de steps: {start_step} a {end_step}")
    print("Batch size:", batch_size)
    print("Run ID:", run_id)

    if write:
        print("Tabela de resultados:", RESULT_TABLE)
        print("Filtro de registros já processados: ATIVO")

    else:
        print("Nenhuma tabela de resultados será alterada.")

    print("=" * 72)

    try:
        # Ler os registros em lotes.
        batches = iter_knn_v2_batches(
            start_step,
            end_step,
            batch_size,
            exclude_scored=write,
            model_sha256=model_sha256 if write else None,
            limit=limit,
        )

        for batch_number, transacoes in enumerate(
            batches,
            start=1,
        ):

            if transacoes.empty:
                continue

            # Executar a inferência com o KNN congelado.
            scored = score_knn_v2_transactions(
                transacoes,
                artifacts,
            )

            # Calcular o resumo do lote.
            summary = summarize_knn_v2(scored)

            # Atualizar os acumuladores.
            total += int(
                summary["total_transacoes_analisadas"]
            )

            alerts += int(
                summary["total_alertas"]
            )

            score_sum += float(
                scored["fraud_score"].sum()
            )

            # Guardar somente uma pequena prévia em memória.
            if preview_rows < 10:

                preview = scored.head(
                    10 - preview_rows
                )[
                    [
                        "id_transacao",
                        "step",
                        "fraud_score",
                        "status_analise",
                    ]
                ]

                preview_parts.append(preview)
                preview_rows += len(preview)

            # Persistir somente quando write=True.
            if write and writer_cursor is not None:

                persist_scoring_batch(
                    writer_cursor,
                    scored,
                    run_id=run_id,
                    model_sha256=model_sha256,
                    threshold=threshold,
                    insert_chunk_size=insert_chunk_size,
                )

            # Mostrar o progresso.
            print(
                f"Lote {batch_number}: "
                f"{len(scored):,} transações | "
                f"alertas: {summary['total_alertas']:,} | "
                f"acumulado: {total:,}",
                flush=True,
            )

    finally:
        # Fechar os recursos de escrita.
        try:
            if writer_cursor is not None:
                writer_cursor.close()
        finally:
            if writer_connection is not None:
                writer_connection.close()

    # Calcular score médio.
    mean_score = (
        score_sum / total
        if total
        else 0.0
    )

    # Montar resumo da execução.
    summary_result = {
        "run_id": run_id,
        "modelo": MODEL_NAME,
        "total_transacoes_analisadas": total,
        "total_alertas": alerts,
        "taxa_alertas": alerts / total if total else 0.0,
        "score_medio_modelo": mean_score,
        "limiar": threshold,
        "persistido": bool(write),
        "tabela_resultados": RESULT_TABLE if write else None,
        "sha256_modelo": model_sha256,
    }

    # Exibir resumo operacional.
    print("\n========== RESUMO DO SCORING KNN V2 ==========")

    for key, value in summary_result.items():

        if isinstance(value, float):
            print(f"{key}: {value:,.8f}")

        else:
            print(f"{key}: {value}")

    # Exibir amostra de resultados.
    if preview_parts:

        print("\n========== AMOSTRA DE RESULTADOS ==========")

        print(
            pd.concat(
                preview_parts,
                ignore_index=True,
            ).to_string(index=False)
        )

    if total == 0:
        print(
            "Nenhuma transação pendente encontrada no intervalo informado."
        )

    return summary_result


# ============================================================
# 13. ARGUMENTOS DE LINHA DE COMANDO
# ============================================================

def parse_args() -> argparse.Namespace:
    """Define os argumentos da execução operacional."""

    parser = argparse.ArgumentParser(
        description="Executa o scoring incremental do KNN V2."
    )

    parser.add_argument(
        "--start-step",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--end-step",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=5_000,
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limita a quantidade de registros para testes.",
    )

    parser.add_argument(
        "--insert-chunk-size",
        type=int,
        default=250,
    )

    parser.add_argument(
        "--write",
        action="store_true",
        help="Autoriza a persistência nas tabelas Delta do KNN V2.",
    )

    return parser.parse_args()


# ============================================================
# 14. PONTO DE ENTRADA
# ============================================================

def main() -> int:
    """Executa o scoring a partir da linha de comando."""

    args = parse_args()

    run_knn_v2_scoring(
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
