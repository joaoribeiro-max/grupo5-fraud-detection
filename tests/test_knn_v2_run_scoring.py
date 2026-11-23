
# ============================================================
# TESTES AUTOMATIZADOS - KNN V2 RUN SCORING
# Testa consultas, staging, MERGE e idempotencia.
# Nenhuma conexao real ou gravacao no Databricks.
# ============================================================

import pandas as pd
import pytest

from finops_ml.knn_v2_run_scoring import (
    RESULT_TABLE,
    STAGING_TABLE,
    STAGING_INSERT_COLUMNS,
    build_source_query,
    build_multirow_insert_sql,
    build_staging_rows,
    insert_staging_rows_chunked,
    persist_scoring_batch,
)


# ============================================================
# 1. CURSOR SIMULADO
# ============================================================

class FakeCursor:
    """Simula um cursor SQL sem acessar o Databricks."""

    def __init__(self):
        self.calls = []

    def execute(self, statement, parameters=None):
        # Registrar os comandos para verificar sua construcao.
        self.calls.append((statement, parameters))


# ============================================================
# 2. BASE ARTIFICIAL PARA OS TESTES
# ============================================================

def sample_result(rows=1):
    """Cria resultados artificiais para testar a persistencia."""

    scores = [
        0.80,
        0.20,
        0.60,
        0.10,
        0.90,
    ]

    alertas = [
        True,
        False,
        True,
        False,
        True,
    ]

    dados = []

    for i in range(rows):

        score = scores[i % len(scores)]
        alerta = alertas[i % len(alertas)]

        dados.append({
            "id_transacao": f"tx-{i}",
            "step": 632,
            "dia_absoluto": 26,
            "fraud_score": score,
            "fraud_alert": alerta,
            "status_analise": (
                "ALERTA" if alerta else "SEM_ALERTA"
            ),
        })

    return pd.DataFrame(dados)


def make_rows(rows=1):
    """Gera linhas de staging utilizando o contrato oficial."""

    return build_staging_rows(
        sample_result(rows),
        run_id="run-test-1",
        model_sha256="a" * 64,
        threshold=0.47619047619047616,
    )


# ============================================================
# 3. TESTES DAS CONSULTAS DE ORIGEM
# ============================================================

def test_query_preview_does_not_require_existing_scores():

    # Montar consulta sem excluir registros processados.
    query, params = build_source_query(
        632,
        743,
        exclude_scored=False,
    )

    assert "NOT EXISTS" not in query
    assert "eh_fraude" not in query
    assert params == [632, 743]


def test_query_excludes_already_scored_records():

    # Montar consulta com filtro por hash do modelo.
    sha = "a" * 64

    query, params = build_source_query(
        632,
        743,
        exclude_scored=True,
        model_sha256=sha,
    )

    assert "NOT EXISTS" in query
    assert RESULT_TABLE in query
    assert "sha256_modelo" in query
    assert "eh_fraude" not in query

    assert params == [632, 743, sha]


def test_query_uses_limit_when_provided():

    query, params = build_source_query(
        632,
        743,
        exclude_scored=False,
        limit=5,
    )

    assert "LIMIT 5" in query
    assert params == [632, 743]


@pytest.mark.parametrize(
    "start,end,limit",
    [
        (0, 743, None),
        (632, 600, None),
        (632, 743, 0),
    ],
)
def test_query_rejects_invalid_parameters(start, end, limit):

    with pytest.raises(ValueError):
        build_source_query(
            start,
            end,
            exclude_scored=False,
            limit=limit,
        )


def test_query_requires_model_hash_when_excluding_scores():

    with pytest.raises(ValueError, match="model_sha256"):

        build_source_query(
            632,
            743,
            exclude_scored=True,
        )


# ============================================================
# 4. TESTES DO INSERT MULTILINHA
# ============================================================

def test_multirow_insert_has_expected_placeholders():

    # Criar comando para tres registros.
    statement = build_multirow_insert_sql(3)

    # Cada linha possui dez campos.
    assert statement.startswith(
        f"INSERT INTO {STAGING_TABLE}"
    )

    assert statement.count("?") == (
        3 * len(STAGING_INSERT_COLUMNS)
    )

    assert "run_id" in statement
    assert "sha256_modelo" in statement


@pytest.mark.parametrize(
    "count",
    [0, -1, 1.5, True],
)
def test_multirow_insert_rejects_invalid_count(count):

    with pytest.raises(ValueError):
        build_multirow_insert_sql(count)


# ============================================================
# 5. TESTES DA CONSTRUCAO DAS LINHAS
# ============================================================

def test_build_staging_rows_maps_fields_correctly():

    # Gerar uma linha de resultado.
    rows = make_rows(1)

    assert len(rows) == 1
    assert len(rows[0]) == 10

    linha = rows[0]

    assert linha[0] == "run-test-1"
    assert linha[1] == "tx-0"
    assert linha[2] == 632
    assert linha[3] == 26
    assert linha[4] == pytest.approx(0.80)
    assert linha[5] is True
    assert linha[6] == "ALERTA"
    assert linha[7] == "KNN V2"
    assert linha[8] == "a" * 64
    assert linha[9] == pytest.approx(
        0.47619047619047616
    )


def test_build_staging_rows_rejects_duplicate_ids():

    # Criar dois registros com o mesmo identificador.
    resultado = sample_result(2)

    resultado.loc[1, "id_transacao"] = "tx-0"

    with pytest.raises(ValueError, match="duplicados"):

        build_staging_rows(
            resultado,
            run_id="run-1",
            model_sha256="a" * 64,
            threshold=0.47619047619047616,
        )


def test_build_staging_rows_rejects_score_out_of_range():

    resultado = sample_result(1)

    resultado.loc[0, "fraud_score"] = 1.5

    with pytest.raises(ValueError, match="Score inválido"):

        build_staging_rows(
            resultado,
            run_id="run-1",
            model_sha256="a" * 64,
            threshold=0.47619047619047616,
        )


def test_build_staging_rows_rejects_alert_threshold_mismatch():

    resultado = sample_result(1)

    # Score 0.80 exige alerta verdadeiro.
    resultado.loc[0, "fraud_alert"] = False
    resultado.loc[0, "status_analise"] = "SEM_ALERTA"

    with pytest.raises(ValueError, match="limiar congelado"):

        build_staging_rows(
            resultado,
            run_id="run-1",
            model_sha256="a" * 64,
            threshold=0.47619047619047616,
        )


# ============================================================
# 6. TESTES DA INSERCAO EM LOTES
# ============================================================

def test_insert_staging_rows_uses_chunked_commands():

    cursor = FakeCursor()

    rows = make_rows(5)

    # Inserir cinco registros em grupos de dois.
    inserted = insert_staging_rows_chunked(
        cursor,
        rows,
        insert_chunk_size=2,
    )

    assert inserted == 5

    # Esperamos tres comandos SQL.
    assert len(cursor.calls) == 3

    tamanhos = [
        len(parameters)
        for _, parameters in cursor.calls
    ]

    # Cada linha possui dez parametros.
    assert tamanhos == [20, 20, 10]


@pytest.mark.parametrize(
    "chunk_size",
    [0, 501, -1],
)
def test_insert_rejects_invalid_chunk_size(chunk_size):

    cursor = FakeCursor()

    with pytest.raises(ValueError):

        insert_staging_rows_chunked(
            cursor,
            make_rows(1),
            insert_chunk_size=chunk_size,
        )


# ============================================================
# 7. TESTE DA PERSISTENCIA COM MERGE
# ============================================================

def test_persist_uses_insert_merge_and_cleanup():

    cursor = FakeCursor()

    # Executar a persistencia com cursor simulado.
    total = persist_scoring_batch(
        cursor,
        sample_result(2),
        run_id="run-test-1",
        model_sha256="a" * 64,
        threshold=0.47619047619047616,
        insert_chunk_size=250,
    )

    assert total == 2

    # Deve executar INSERT, MERGE e DELETE.
    assert len(cursor.calls) == 3

    insert_sql = cursor.calls[0][0]
    merge_sql = cursor.calls[1][0]
    delete_sql = cursor.calls[2][0]

    assert insert_sql.startswith("INSERT INTO")
    assert "MERGE INTO" in merge_sql
    assert delete_sql.startswith("DELETE FROM")

    assert cursor.calls[1][1] == ["run-test-1"]
    assert cursor.calls[2][1] == ["run-test-1"]


def test_persist_does_not_write_empty_batch():

    cursor = FakeCursor()

    resultado = sample_result(0)

    total = persist_scoring_batch(
        cursor,
        resultado,
        run_id="run-test-1",
        model_sha256="a" * 64,
        threshold=0.47619047619047616,
    )

    assert total == 0
    assert len(cursor.calls) == 0
