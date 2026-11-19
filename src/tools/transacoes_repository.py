from __future__ import annotations

import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from databricks import sql
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

# Caminho fixo: nenhum identificador SQL vem do usuário ou do modelo.
TABLE_NAME = "workspace.gold_agente.ia_dados_transacoes"
PAGE_SIZE_DEFAULT = 50
PAGE_SIZE_MAX = 200

# Não retornamos identificadores de contas ao modelo por padrão.
RESULT_COLUMNS = (
    "id_transacao",
    "tipo_transacao",
    "valor",
    "eh_fraude",
    "flag_fraude_sistema",
    "dia_simulacao",
    "hora_do_dia",
    "turno",
    "dia_semana",
    "eh_final_de_semana",
)
CSV_COLUMNS = RESULT_COLUMNS
ALLOWED_TRANSACTION_TYPES = {
    "PIX", "TED", "TRANSFER", "CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT"
}


@dataclass(frozen=True)
class TransactionFilters:
    id_transacao: str | None = None
    tipo_transacao: str | None = None
    fraude_confirmada: bool | None = None
    alerta_sistema: bool | None = None
    dia_min: int | None = None
    dia_max: int | None = None
    valor_min: float | None = None
    valor_max: float | None = None


def sql_connection():
    """Abre conexão com o Warehouse usando credenciais do ambiente."""
    names = (
        "DATABRICKS_SERVER_HOSTNAME",
        "DATABRICKS_HTTP_PATH",
        "DATABRICKS_TOKEN",
    )
    missing = [name for name in names if not os.getenv(name)]
    if missing:
        raise RuntimeError("Configuração Databricks ausente: " + ", ".join(missing))
    return sql.connect(
        server_hostname=os.environ["DATABRICKS_SERVER_HOSTNAME"],
        http_path=os.environ["DATABRICKS_HTTP_PATH"],
        access_token=os.environ["DATABRICKS_TOKEN"],
    )


def create_filters(
    id_transacao: str | None = None,
    tipo_transacao: str | None = None,
    fraude_confirmada: bool | None = None,
    alerta_sistema: bool | None = None,
    dia_min: int | None = None,
    dia_max: int | None = None,
    valor_min: float | None = None,
    valor_max: float | None = None,
) -> TransactionFilters:
    if id_transacao is not None:
        if not isinstance(id_transacao, str) or not id_transacao.strip() or len(id_transacao) > 128:
            raise ValueError("id_transacao deve ter entre 1 e 128 caracteres.")
        id_transacao = id_transacao.strip()

    if tipo_transacao is not None:
        if not isinstance(tipo_transacao, str):
            raise ValueError("tipo_transacao deve ser texto.")
        tipo_transacao = tipo_transacao.strip().upper()
        if tipo_transacao not in ALLOWED_TRANSACTION_TYPES:
            raise ValueError("tipo_transacao não está entre os tipos permitidos.")

    for name, value in (("fraude_confirmada", fraude_confirmada), ("alerta_sistema", alerta_sistema)):
        if value is not None and not isinstance(value, bool):
            raise ValueError(f"{name} deve ser verdadeiro ou falso.")

    for name, value in (("dia_min", dia_min), ("dia_max", dia_max)):
        if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
            raise ValueError(f"{name} deve ser um inteiro não negativo.")
    if dia_min is not None and dia_max is not None and dia_min > dia_max:
        raise ValueError("dia_min não pode ser maior que dia_max.")

    normalized_amounts: dict[str, float | None] = {}
    for name, value in (("valor_min", valor_min), ("valor_max", valor_max)):
        if value is None:
            normalized_amounts[name] = None
            continue
        if isinstance(value, bool):
            raise ValueError(f"{name} deve ser um número não negativo.")
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"{name} deve ser um número não negativo.") from None
        if not math.isfinite(number) or number < 0:
            raise ValueError(f"{name} deve ser um número finito não negativo.")
        normalized_amounts[name] = number
    if (
        normalized_amounts["valor_min"] is not None
        and normalized_amounts["valor_max"] is not None
        and normalized_amounts["valor_min"] > normalized_amounts["valor_max"]
    ):
        raise ValueError("valor_min não pode ser maior que valor_max.")

    return TransactionFilters(
        id_transacao=id_transacao,
        tipo_transacao=tipo_transacao,
        fraude_confirmada=fraude_confirmada,
        alerta_sistema=alerta_sistema,
        dia_min=dia_min,
        dia_max=dia_max,
        valor_min=normalized_amounts["valor_min"],
        valor_max=normalized_amounts["valor_max"],
    )


def _where_clause(filters: TransactionFilters) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []

    if filters.id_transacao is not None:
        clauses.append("id_transacao = ?")
        params.append(filters.id_transacao)
    if filters.tipo_transacao is not None:
        clauses.append("UPPER(tipo_transacao) = ?")
        params.append(filters.tipo_transacao)

    true_labels = ("1", "true", "sim", "fraude", "yes")
    false_labels = ("0", "false", "não", "nao", "não fraude", "nao fraude", "no fraud")
    for column, value in (
        ("eh_fraude", filters.fraude_confirmada),
        ("flag_fraude_sistema", filters.alerta_sistema),
    ):
        if value is None:
            continue
        labels = true_labels if value else false_labels
        markers = ", ".join("?" for _ in labels)
        clauses.append(f"LOWER(TRIM(CAST({column} AS STRING))) IN ({markers})")
        params.extend(labels)

    for column, operator, value in (
        ("dia_simulacao", ">=", filters.dia_min),
        ("dia_simulacao", "<=", filters.dia_max),
        ("valor", ">=", filters.valor_min),
        ("valor", "<=", filters.valor_max),
    ):
        if value is not None:
            clauses.append(f"{column} {operator} ?")
            params.append(value)

    return (" WHERE " + " AND ".join(clauses) if clauses else "", params)


def fetch_transaction_page(
    filters: TransactionFilters,
    cursor_id: str | None,
    page_size: int,
    include_total: bool = False,
) -> dict[str, Any]:
    if isinstance(page_size, bool) or not isinstance(page_size, int) or not 1 <= page_size <= PAGE_SIZE_MAX:
        raise ValueError(f"tamanho_pagina deve estar entre 1 e {PAGE_SIZE_MAX}.")
    if not isinstance(include_total, bool):
        raise ValueError("incluir_total deve ser verdadeiro ou falso.")
    if cursor_id is not None:
        if not isinstance(cursor_id, str) or not cursor_id.strip() or len(cursor_id) > 128:
            raise ValueError("cursor_id inválido.")
        cursor_id = cursor_id.strip()

    where, filter_params = _where_clause(filters)
    clauses = [where.removeprefix(" WHERE ")] if where else []
    parameters = list(filter_params)
    if cursor_id is not None:
        clauses.append("id_transacao > ?")
        parameters.append(cursor_id)
    final_where = " WHERE " + " AND ".join(clauses) if clauses else ""
    selected = ", ".join(RESULT_COLUMNS)
    query = (
        f"SELECT {selected} FROM {TABLE_NAME}{final_where} "
        "ORDER BY id_transacao ASC LIMIT ?"
    )
    parameters.append(page_size + 1)

    with sql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, parameters)
            names = [column[0] for column in cursor.description or []]
            fetched = cursor.fetchmany(page_size + 1)
            has_more = len(fetched) > page_size
            page_rows = fetched[:page_size]
            records = [dict(zip(names, row)) for row in page_rows]

            total = None
            if include_total:
                count_query = f"SELECT COUNT(*) FROM {TABLE_NAME}{where}"
                cursor.execute(count_query, filter_params)
                count_row = cursor.fetchone()
                total = int(count_row[0]) if count_row else 0

    next_cursor = records[-1]["id_transacao"] if has_more and records else None
    return {
        "total_registros": total,
        "dados": records,
        "tem_proxima_pagina": has_more,
        "proximo_cursor": next_cursor,
        "tamanho_pagina": page_size,
    }


def iter_export_rows(filters: TransactionFilters, limit: int) -> Iterator[dict[str, Any]]:
    where, params = _where_clause(filters)
    selected = ", ".join(CSV_COLUMNS)
    query = f"SELECT {selected} FROM {TABLE_NAME}{where} ORDER BY id_transacao ASC LIMIT ?"
    with sql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, [*params, limit + 1])
            names = [column[0] for column in cursor.description or []]
            while True:
                batch = cursor.fetchmany(500)
                if not batch:
                    break
                for row in batch:
                    yield dict(zip(names, row))



