
"""MÃ³dulo de scoring antifraude â€” Grupo 5.

Modelo: LightGBM sem ponderaÃ§Ã£o.

A exposiÃ§Ã£o financeira Ã© a soma dos valores originais das transaÃ§Ãµes
sinalizadas. NÃ£o representa prejuÃ­zo real, perda evitada ou valor recuperado.

ATENÃ‡ÃƒO:
Os cortes de Binning abaixo foram transcritos dos valores exibidos
no notebook com duas casas decimais. Para reproduÃ§Ã£o exata, devemos
substituÃ­-los pelos valores completos salvos no treinamento.
"""
import json
import joblib
from pathlib import Path
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


# ParÃ¢metros do notebook 02_preparacao_e_modelagem.ipynb
LIMITE_SUPERIOR_AMOUNT = 502605.225

PONTOS_CORTE_AMOUNT = (
    9927.51,
    36577.72,
    122857.67,
    247054.06,
)

LIMIAR_LIGHTGBM = 0.012455002510276548

TIPOS_TRANSACAO = (
    "CASH_IN",
    "CASH_OUT",
    "DEBIT",
    "PAYMENT",
    "TRANSFER",
)

COLUNAS_MODELO = (
    "amount",
    "type",
    "destino_eh_comercio",
    "faixa_valor",
)


@dataclass(frozen=True)
class FraudScoringConfig:
    """ConfiguraÃ§Ãµes do prÃ©-processamento e classificaÃ§Ã£o."""

    amount_cap_upper: float = LIMITE_SUPERIOR_AMOUNT
    amount_bin_edges: tuple = PONTOS_CORTE_AMOUNT
    threshold: float = LIMIAR_LIGHTGBM

    def __post_init__(self):
        if not np.isfinite(self.amount_cap_upper):
            raise ValueError("Limite de Capping invÃ¡lido.")

        if self.amount_cap_upper <= 0:
            raise ValueError("Limite de Capping deve ser positivo.")

        if not 0 <= self.threshold <= 1:
            raise ValueError("O limiar deve estar entre 0 e 1.")

        if tuple(sorted(self.amount_bin_edges)) != self.amount_bin_edges:
            raise ValueError("Os cortes devem estar em ordem crescente.")

        if len(set(self.amount_bin_edges)) != len(self.amount_bin_edges):
            raise ValueError("Existem cortes repetidos no Binning.")


def preparar_features_lightgbm(
    transacoes: pd.DataFrame,
    config: FraudScoringConfig | None = None,
) -> pd.DataFrame:
    """Prepara as quatro features utilizadas pelo LightGBM.

    Entradas:
    - amount
    - type
    - destino_eh_comercio ou nameDest

    O amount original nÃ£o Ã© alterado.
    """

    if not isinstance(transacoes, pd.DataFrame):
        raise TypeError("A entrada deve ser um DataFrame.")

    if transacoes.empty:
        raise ValueError("O DataFrame estÃ¡ vazio.")

    config = config or FraudScoringConfig()

    ausentes = {"amount", "type"} - set(transacoes.columns)

    if ausentes:
        raise ValueError(
            f"Colunas obrigatÃ³rias ausentes: {sorted(ausentes)}"
        )

    amount = pd.to_numeric(
        transacoes["amount"],
        errors="coerce",
    )

    if amount.isna().any():
        raise ValueError("Existem valores invÃ¡lidos em amount.")

    if not np.isfinite(amount.to_numpy(dtype=float)).all():
        raise ValueError("amount possui valores nÃ£o finitos.")

    if (amount < 0).any():
        raise ValueError("amount nÃ£o pode ser negativo.")

    tipos = (
        transacoes["type"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    if tipos.isna().any():
        raise ValueError("Existem tipos de transaÃ§Ã£o ausentes.")

    desconhecidos = set(tipos) - set(TIPOS_TRANSACAO)

    if desconhecidos:
        raise ValueError(
            f"Tipos de transaÃ§Ã£o nÃ£o reconhecidos: {desconhecidos}"
        )

    # IdentificaÃ§Ã£o de destinatÃ¡rio comercial.
    if "destino_eh_comercio" in transacoes.columns:

        destino = pd.to_numeric(
            transacoes["destino_eh_comercio"],
            errors="coerce",
        )

    elif "nameDest" in transacoes.columns:

        destino = (
            transacoes["nameDest"]
            .astype("string")
            .str.startswith("M", na=False)
            .astype("int8")
        )

    else:
        raise ValueError(
            "Informe destino_eh_comercio ou nameDest."
        )

    if destino.isna().any() or not destino.isin([0, 1]).all():
        raise ValueError(
            "destino_eh_comercio deve conter apenas 0 ou 1."
        )

    # Capping: utiliza o limite calculado no treinamento.
    amount_cap = amount.clip(
        upper=config.amount_cap_upper
    )

    # Binning: utiliza os cortes calculados no treinamento.
    limites = [
        -np.inf,
        *config.amount_bin_edges,
        np.inf,
    ]

    rotulos = [
        f"faixa_{i}"
        for i in range(1, len(limites))
    ]

    faixa_valor = pd.cut(
        amount_cap,
        bins=limites,
        labels=rotulos,
        include_lowest=True,
    )

    if faixa_valor.isna().any():
        raise ValueError("Falha na criaÃ§Ã£o de faixa_valor.")

    features = pd.DataFrame(
        {
            "amount": amount_cap.astype("float64"),

            "type": pd.Categorical(
                tipos,
                categories=TIPOS_TRANSACAO,
            ),

            "destino_eh_comercio": destino.astype("int8"),

            "faixa_valor": pd.Categorical(
                faixa_valor.astype("string"),
                categories=rotulos,
                ordered=True,
            ),
        },
        index=transacoes.index,
    )

    return features.loc[:, list(COLUNAS_MODELO)]


def score_transactions(
    modelo: Any,
    transacoes: pd.DataFrame,
    config: FraudScoringConfig | None = None,
) -> pd.DataFrame:
    """Classifica transaÃ§Ãµes utilizando o LightGBM treinado.

    Modelo esperado:
    experimentos_lgb["Sem ponderaÃ§Ã£o"]["modelo"]
    """

    if modelo is None or not callable(
        getattr(modelo, "predict_proba", None)
    ):
        raise TypeError(
            "O modelo deve possuir o mÃ©todo predict_proba."
        )

    config = config or FraudScoringConfig()

    features = preparar_features_lightgbm(
        transacoes,
        config,
    )

    # VerificaÃ§Ã£o do contrato de features.
    nomes_modelo = getattr(modelo, "feature_name_", None)

    if nomes_modelo is None:
        nomes_modelo = getattr(
            modelo,
            "feature_names_in_",
            None,
        )

    if nomes_modelo is not None:
        if list(nomes_modelo) != list(COLUNAS_MODELO):
            raise ValueError(
                "As features do modelo nÃ£o correspondem "
                "Ã s features preparadas."
            )

    probabilidades = np.asarray(
        modelo.predict_proba(features)
    )

    classes = np.asarray(
        getattr(modelo, "classes_", [0, 1])
    )

    indices_positivos = np.flatnonzero(classes == 1)

    if probabilidades.ndim != 2 or len(indices_positivos) != 1:
        raise ValueError(
            "NÃ£o foi possÃ­vel identificar a classe positiva."
        )

    scores = probabilidades[:, int(indices_positivos[0])]

    if len(scores) != len(transacoes):
        raise ValueError("Quantidade de previsÃµes incompatÃ­vel.")

    if not np.isfinite(scores).all():
        raise ValueError("O modelo retornou scores nÃ£o finitos.")

    resultado = transacoes.copy()

    alertas = scores >= config.threshold

    # Utilizamos o valor original, nÃ£o o valor apÃ³s Capping.
    valores_originais = pd.to_numeric(
        resultado["amount"],
        errors="raise",
    ).astype(float)

    resultado["fraud_score"] = scores

    resultado["fraud_alert"] = alertas

    resultado["status_analise"] = np.where(
        alertas,
        "ALERTA",
        "SEM_ALERTA",
    )

    resultado["valor_sinalizado"] = np.where(
        alertas,
        valores_originais,
        0.0,
    )

    return resultado


def summarize_exposure(
    resultado: pd.DataFrame,
) -> dict[str, int | float]:
    """Resume alertas e exposiÃ§Ã£o financeira sinalizada."""

    colunas = {
        "fraud_alert",
        "valor_sinalizado",
        "fraud_score",
    }

    ausentes = colunas - set(resultado.columns)

    if ausentes:
        raise ValueError(
            f"Colunas ausentes: {sorted(ausentes)}"
        )

    total = int(len(resultado))

    alertas = int(
        resultado["fraud_alert"].astype(bool).sum()
    )

    exposicao = float(
        resultado["valor_sinalizado"].sum()
    )

    score_medio = (
        float(resultado["fraud_score"].mean())
        if total
        else 0.0
    )

    return {
        "total_transacoes_analisadas": total,
        "total_alertas": alertas,
        "taxa_alertas": (
            alertas / total if total else 0.0
        ),
        "exposicao_financeira_sinalizada": exposicao,
        "score_medio_modelo": score_medio,
    }

def load_model_artifacts(
    models_dir: str | Path | None = None,
):
    """Carrega o modelo LightGBM e suas configuraÃ§Ãµes salvas."""

    if models_dir is None:
        raiz_projeto = Path(__file__).resolve().parents[2]
        models_dir = raiz_projeto / "models"

    models_dir = Path(models_dir)

    caminho_modelo = (
        models_dir / "lightgbm_fraud_detector.joblib"
    )

    caminho_metadados = (
        models_dir / "lightgbm_fraud_detector_metadata.json"
    )

    if not caminho_modelo.exists():
        raise FileNotFoundError(
            f"Modelo nÃ£o encontrado: {caminho_modelo}"
        )

    if not caminho_metadados.exists():
        raise FileNotFoundError(
            f"Metadados nÃ£o encontrados: {caminho_metadados}"
        )

    metadata = json.loads(
        caminho_metadados.read_text(encoding="utf-8")
    )

    # Validar as features registradas.
    features_metadata = metadata.get("features", [])

    if list(features_metadata) != list(COLUNAS_MODELO):
        raise ValueError(
            "As features dos metadados nÃ£o correspondem "
            "ao contrato do mÃ³dulo."
        )

    # Recuperar os parÃ¢metros com precisÃ£o total.
    config = FraudScoringConfig(
        amount_cap_upper=float(
            metadata["limite_superior_capping"]
        ),
        amount_bin_edges=tuple(
            float(valor)
            for valor in metadata["pontos_corte_binning"]
        ),
        threshold=float(
            metadata["limiar_validacao"]
        ),
    )

    # Carregar o modelo treinado.
    modelo = joblib.load(caminho_modelo)

    features_modelo = getattr(
        modelo,
        "feature_name_",
        None,
    )

    if features_modelo is not None:
        if list(features_modelo) != list(COLUNAS_MODELO):
            raise ValueError(
                "O modelo salvo possui features incompatÃ­veis."
            )

    print("Modelo LightGBM carregado.")
    print("Limiar:", config.threshold)
    print("Capping:", config.amount_cap_upper)
    print("Features:", list(COLUNAS_MODELO))

    return modelo, config, metadata
