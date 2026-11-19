from __future__ import annotations

import csv
import logging
import tempfile
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .transacoes_repository import CSV_COLUMNS, TransactionFilters, create_filters, iter_export_rows

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPORT_DIR = PROJECT_ROOT / "exports"
MAX_CSV_ROWS = 100_000


def _safe_cell(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    if len(value) > 512:
        raise ValueError("Um campo retornado excede o tamanho permitido para exportação.")
    normalized = value.lstrip()
    if normalized.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + value
    return value


def _write_csv(filters: TransactionFilters) -> dict[str, Any]:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"transacoes_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}_{uuid.uuid4().hex[:8]}.csv"
    final_path = EXPORT_DIR / filename
    temporary_path: Path | None = None
    exported = 0
    truncated = False

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            newline="",
            encoding="utf-8-sig",
            prefix=".transacoes_",
            suffix=".tmp",
            dir=EXPORT_DIR,
            delete=False,
        ) as file:
            temporary_path = Path(file.name)
            writer = csv.writer(file, lineterminator="\n")
            writer.writerow(CSV_COLUMNS)
            for row in iter_export_rows(filters, MAX_CSV_ROWS):
                if exported >= MAX_CSV_ROWS:
                    truncated = True
                    break
                writer.writerow([_safe_cell(row.get(column)) for column in CSV_COLUMNS])
                exported += 1

        temporary_path.replace(final_path)
        return {
            "status": "sucesso",
            "arquivo": str(final_path.resolve()),
            "nome_arquivo": filename,
            "linhas_exportadas": exported,
            "limite_linhas": MAX_CSV_ROWS,
            "exportacao_completa": not truncated,
            "aviso": "O CSV foi salvo na pasta exports/ do servidor do agent."
            if not truncated
            else "O CSV foi salvo em exports/ e limitado a 100.000 linhas; refine os filtros para exportar outro lote.",
        }
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise


def exportar_transacoes_csv(
    id_transacao: str | None = None,
    tipo_transacao: str | None = None,
    fraude_confirmada: bool | None = None,
    alerta_sistema: bool | None = None,
    dia_min: int | None = None,
    dia_max: int | None = None,
    valor_min: float | None = None,
    valor_max: float | None = None,
) -> dict[str, Any]:
    """Gera um CSV filtrado diretamente na pasta exports/ do projeto.

    O arquivo inclui IDs, tipo, valor, rótulos históricos e campos de tempo;
    não inclui números de conta. O limite é 100.000 linhas por arquivo.
    """
    try:
        filters = create_filters(
            id_transacao=id_transacao,
            tipo_transacao=tipo_transacao,
            fraude_confirmada=fraude_confirmada,
            alerta_sistema=alerta_sistema,
            dia_min=dia_min,
            dia_max=dia_max,
            valor_min=valor_min,
            valor_max=valor_max,
        )
        return _write_csv(filters)
    except ValueError as exc:
        return {"status": "erro_validacao", "mensagem": str(exc)}
    except Exception:
        logger.exception("Falha ao gravar CSV na pasta exports")
        return {
            "status": "erro_exportacao",
            "mensagem": "Não foi possível exportar os dados. Verifique os filtros e os logs do servidor.",
        }
