from __future__ import annotations

import logging
from typing import Any

from .transacoes_repository import (
    PAGE_SIZE_DEFAULT,
    create_filters,
    fetch_transaction_page,
)

logger = logging.getLogger(__name__)


def consultar_transacoes(
    id_transacao: str | None = None,
    tipo_transacao: str | None = None,
    fraude_confirmada: bool | None = None,
    alerta_sistema: bool | None = None,
    dia_min: int | None = None,
    dia_max: int | None = None,
    valor_min: float | None = None,
    valor_max: float | None = None,
    cursor_id: str | None = None,
    tamanho_pagina: int = PAGE_SIZE_DEFAULT,
    incluir_total: bool = False,
) -> dict[str, Any]:
    """Busca transações por filtros seguros e retorna uma página ordenada.

    Use cursor_id apenas com o proximo_cursor retornado pela chamada anterior.
    Os registros expostos não incluem números de contas.
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
        return {"status": "sucesso", **fetch_transaction_page(filters, cursor_id, tamanho_pagina, incluir_total)}
    except ValueError as exc:
        return {"status": "erro_validacao", "mensagem": str(exc)}
    except Exception:
        logger.exception("Falha inesperada em consultar_transacoes")
        return {
            "status": "erro_databricks",
            "mensagem": "Não foi possível consultar os dados. Verifique os filtros e tente novamente.",
        }

