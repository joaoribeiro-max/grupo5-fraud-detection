
"""
Ferramenta de Machine Learning para o agente Google ADK.

Grupo 5 — Cidade Inteligente
Responsável pelo modelo: FinOps / Machine Learning

A ferramenta recebe os atributos de uma transação,
executa o LightGBM e retorna o resultado estruturado
para o agente de Inteligência Artificial.
"""

from functools import lru_cache
from typing import Any

import pandas as pd

from src.finops_ml.fraud_scoring import (
    load_model_artifacts,
    score_transactions,
)


# ============================================================
# 1. CARREGAMENTO DO MODELO
# ============================================================

@lru_cache(maxsize=1)
def carregar_recursos_ml():
    """
    Carrega o modelo e suas configurações uma única vez
    por processo do agente.
    """

    modelo, config, metadata = load_model_artifacts()

    return modelo, config, metadata


# ============================================================
# 2. FERRAMENTA DE ANÁLISE DE TRANSAÇÃO
# ============================================================

def analisar_transacao(
    amount: float,
    tipo_transacao: str,
    destino_eh_comercio: bool,
) -> dict[str, Any]:
    """
    Analisa uma transação financeira utilizando o LightGBM.

    Args:
        amount: Valor financeiro original da transação.
        tipo_transacao: Tipo da operação.
            Exemplos: TRANSFER, CASH_OUT, PAYMENT.
        destino_eh_comercio: True se o destinatário
            for comercial; False caso contrário.

    Returns:
        Dicionário com o score, decisão do modelo,
        limiar aplicado e valor financeiro sinalizado.
    """

    # Validar os dados recebidos
    if isinstance(amount, bool) or not isinstance(
        amount, (int, float)
    ):
        return {
            "status": "erro",
            "mensagem": "O valor da transação deve ser numérico.",
        }

    if amount < 0 or not pd.notna(amount):
        return {
            "status": "erro",
            "mensagem": "O valor da transação é inválido.",
        }

    if not isinstance(tipo_transacao, str) or not tipo_transacao.strip():
        return {
            "status": "erro",
            "mensagem": "Informe um tipo de transação válido.",
        }

    if not isinstance(destino_eh_comercio, bool):
        return {
            "status": "erro",
            "mensagem": "destino_eh_comercio deve ser booleano.",
        }

    try:

        # Recuperar o modelo e os parâmetros oficiais
        modelo, config, metadata = carregar_recursos_ml()

        # Montar a entrada no formato esperado pelo modelo
        transacao = pd.DataFrame(
            {
                "amount": [float(amount)],
                "type": [tipo_transacao],
                "destino_eh_comercio": [
                    int(destino_eh_comercio)
                ],
            }
        )

        # Executar o scoring
        resultado = score_transactions(
            modelo=modelo,
            transacoes=transacao,
            config=config,
        )

        registro = resultado.iloc[0]

        alerta = bool(registro["fraud_alert"])
        score = float(registro["fraud_score"])

        # Retornar informações estruturadas para o ADK
        return {
            "status": "sucesso",
            "modelo": metadata.get("modelo", "LightGBM"),
            "experimento": metadata.get(
                "experimento",
                "Sem ponderação",
            ),
            "analise": {
                "tipo_transacao": tipo_transacao.upper(),
                "valor_transacao": float(amount),
                "fraud_score": score,
                "limiar_aplicado": float(config.threshold),
                "alerta_fraude": alerta,
                "status_analise": (
                    "ALERTA"
                    if alerta
                    else "SEM_ALERTA"
                ),
                "exposicao_financeira_sinalizada": (
                    float(amount)
                    if alerta
                    else 0.0
                ),
            },
            "ressalvas": [
                "O score não representa uma probabilidade calibrada.",
                "Um alerta indica uma transação que merece investigação.",
                "A exposição sinalizada não representa prejuízo confirmado.",
                "O modelo foi desenvolvido com dados sintéticos PaySim.",
            ],
        }

    except Exception as erro:

        return {
            "status": "erro",
            "mensagem": (
                "Não foi possível executar a análise da transação."
            ),
            "detalhe_tecnico": str(erro),
        }
