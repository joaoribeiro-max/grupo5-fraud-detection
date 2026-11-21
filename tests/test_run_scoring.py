import pandas as pd
import pytest

from finops_ml.fraud_scoring import MODEL_FEATURES
from finops_ml.run_scoring import (
    INFERENCE_COLUMNS,
    RESULT_TABLE,
    STAGING_INSERT_COLUMNS,
    build_multirow_insert_sql,
    build_source_query,
    build_staging_rows,
    insert_staging_rows_chunked,
)


def test_inference_columns_include_features_but_not_target():
    assert INFERENCE_COLUMNS == ["id_transacao", "step", "dia_absoluto", *MODEL_FEATURES]
    assert "eh_fraude" not in INFERENCE_COLUMNS
    assert "flag_fraude_sistema" not in INFERENCE_COLUMNS


def test_build_source_query_excludes_previously_scored_model_rows():
    query, params = build_source_query(632, 743, exclude_scored=True, limit=100)
    assert "NOT EXISTS" in query
    assert RESULT_TABLE in query
    assert "eh_fraude" not in query
    assert "flag_fraude_sistema" not in query
    assert "LIMIT 100" in query
    assert params == [632, 743]


def test_build_source_query_preview_does_not_require_results_table():
    query, params = build_source_query(1, 10, exclude_scored=False, limit=None)
    assert RESULT_TABLE not in query
    assert "NOT EXISTS" not in query
    assert params == [1, 10]


@pytest.mark.parametrize("start,end,limit", [(0, 10, None), (10, 9, None), (1, 10, 0)])
def test_build_source_query_rejects_invalid_ranges(start, end, limit):
    with pytest.raises(ValueError):
        build_source_query(start, end, exclude_scored=False, limit=limit)


def sample_result(rows=1):
    return pd.DataFrame(
        {
            "id_transacao": [f"tx-{i}" for i in range(rows)],
            "step": [632] * rows,
            "dia_absoluto": [26] * rows,
            "fraud_score": [0.25] * rows,
            "fraud_alert": [True] * rows,
            "status_analise": ["ALERTA"] * rows,
            "valor_sinalizado": [123.45] * rows,
        }
    )


def make_rows(rows=1):
    return build_staging_rows(
        sample_result(rows),
        run_id="run-1",
        model_name="LightGBM V2",
        model_sha256="a" * 64,
        threshold=0.08341406734582016,
    )


def test_build_staging_rows_maps_result_fields():
    assert make_rows(1) == [
        (
            "run-1", "tx-0", 632, 26, 0.25, True, "ALERTA", 123.45,
            "LightGBM V2", "a" * 64, 0.08341406734582016,
        )
    ]


def test_build_staging_rows_rejects_duplicate_transaction_ids():
    result = sample_result(2)
    result.loc[1, "id_transacao"] = "tx-0"
    with pytest.raises(ValueError, match="duplicados"):
        build_staging_rows(
            result, run_id="run-1", model_name="LightGBM V2",
            model_sha256="a" * 64, threshold=0.08341406734582016,
        )


def test_multirow_insert_sql_has_one_tuple_per_row_and_explicit_columns():
    statement = build_multirow_insert_sql(3)
    assert statement.startswith("INSERT INTO ")
    assert ", ".join(STAGING_INSERT_COLUMNS) in statement
    assert statement.count("?") == 3 * len(STAGING_INSERT_COLUMNS)
    assert statement.count("(") >= 4  # coluna + três linhas


@pytest.mark.parametrize("count", [0, -1, 1.5])
def test_multirow_insert_rejects_invalid_row_count(count):
    with pytest.raises(ValueError):
        build_multirow_insert_sql(count)


class FakeCursor:
    def __init__(self):
        self.calls = []

    def execute(self, statement, parameters=None):
        self.calls.append((statement, parameters))


def test_insert_staging_rows_uses_one_execute_per_chunk_not_executemany():
    cursor = FakeCursor()
    rows = make_rows(5)

    inserted = insert_staging_rows_chunked(cursor, rows, insert_chunk_size=2)

    assert inserted == 5
    assert len(cursor.calls) == 3
    assert [len(params) for _, params in cursor.calls] == [22, 22, 11]
    assert all(statement.count("?") == len(params) for statement, params in cursor.calls)


@pytest.mark.parametrize("chunk_size", [0, 501, -3])
def test_insert_staging_rows_rejects_invalid_chunk_size(chunk_size):
    cursor = FakeCursor()
    with pytest.raises(ValueError):
        insert_staging_rows_chunked(cursor, make_rows(1), insert_chunk_size=chunk_size)
