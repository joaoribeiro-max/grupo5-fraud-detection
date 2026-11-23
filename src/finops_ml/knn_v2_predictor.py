
# ============================================================
# KNN V2 - PREDICTOR
# Projeto: Grupo 5 - Cidade Inteligente
# Objetivo: carregar o modelo congelado e executar inferências.
# Não realiza treinamento nem reajuste do scaler.
# ============================================================

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler


# ============================================================
# 1. CONTRATO DO MODELO
# ============================================================

MODEL_FILENAME = "knn_v2_modelo_congelado.joblib"
METADATA_FILENAME = "knn_v2_metadata_congelado.json"

MODEL_NAME = "KNN V2"
DEFAULT_THRESHOLD = 0.47619047619047616

# SHA-256 oficial do artefato congelado no Google Colab.
EXPECTED_MODEL_SHA256 = (
    "43a6e622b1d9182e47ac0ab4ec813016c0195ab08d23bbab7ede09e4b3ba370a"
)

# Ordem exata das sete features utilizadas no treinamento.
MODEL_FEATURES: tuple[str, ...] = (
    "eh_transferencia",
    "eh_conta_nova",
    "freq_destino_24h_norm",
    "eh_rajada_destino",
    "valor_log_norm",
    "hora_sin",
    "hora_cos",
)

# Features binárias.
BINARY_FEATURES: tuple[str, ...] = (
    "eh_transferencia",
    "eh_conta_nova",
    "eh_rajada_destino",
)

# Features normalizadas pela engenharia de dados da Gold.
NORMALIZED_FEATURES: tuple[str, ...] = (
    "freq_destino_24h_norm",
    "valor_log_norm",
    "hora_sin",
    "hora_cos",
)


# ============================================================
# 2. ESTRUTURA DOS ARTEFATOS
# ============================================================

@dataclass(frozen=True)
class KNNV2Artifacts:
    """Representa os componentes congelados do KNN V2."""

    modelo: KNeighborsClassifier
    scaler: StandardScaler
    features: tuple[str, ...]
    threshold: float
    model_sha256: str
    metadata: dict[str, Any]


# ============================================================
# 3. UTILITÁRIOS
# ============================================================

def _sha256_file(path: Path) -> str:
    """Calcula o SHA-256 de um arquivo em blocos."""

    digest = hashlib.sha256()

    with path.open("rb") as arquivo:
        for bloco in iter(
            lambda: arquivo.read(1024 * 1024),
            b""
        ):
            digest.update(bloco)

    return digest.hexdigest()


def _validate_dataframe(transacoes: pd.DataFrame) -> None:
    """Valida a estrutura básica do DataFrame de entrada."""

    if not isinstance(transacoes, pd.DataFrame):
        raise TypeError(
            "A entrada deve ser um pandas.DataFrame."
        )

    if transacoes.empty:
        raise ValueError(
            "A base de transações está vazia."
        )

    if transacoes.columns.duplicated().any():
        raise ValueError(
            "A base possui nomes de colunas duplicados."
        )

    # Garantir rastreabilidade quando o identificador estiver presente.
    if "id_transacao" in transacoes.columns:

        if transacoes["id_transacao"].isna().any():
            raise ValueError(
                "Existem identificadores de transação nulos."
            )

        if transacoes["id_transacao"].duplicated().any():
            raise ValueError(
                "Existem identificadores de transação duplicados."
            )


# ============================================================
# 4. CARREGAMENTO DOS ARTEFATOS CONGELADOS
# ============================================================

def load_knn_v2_artifacts(
    models_dir: str | Path | None = None,
) -> KNNV2Artifacts:
    """
    Carrega o classificador KNN V2 e o StandardScaler congelados.

    Valida hash, features, hiperparâmetros, limiar e estrutura.
    Não executa treinamento.
    """

    # Localizar a pasta models/knn_v2 na raiz do projeto.
    if models_dir is None:
        project_root = Path(__file__).resolve().parents[2]
        models_dir = project_root / "models" / "knn_v2"

    models_dir = Path(models_dir)

    model_path = models_dir / MODEL_FILENAME
    metadata_path = models_dir / METADATA_FILENAME

    # Verificar existência dos arquivos.
    if not model_path.is_file():
        raise FileNotFoundError(
            f"Modelo KNN V2 não encontrado: {model_path}"
        )

    if not metadata_path.is_file():
        raise FileNotFoundError(
            f"Metadados KNN V2 não encontrados: {metadata_path}"
        )

    # Validar a integridade do modelo.
    actual_hash = _sha256_file(model_path)

    if actual_hash.lower() != EXPECTED_MODEL_SHA256.lower():
        raise ValueError(
            "Falha na integridade do KNN V2: "
            "SHA-256 diferente do artefato congelado."
        )

    # Carregar metadados.
    metadata = json.loads(
        metadata_path.read_text(encoding="utf-8")
    )

    metadata_hash = metadata.get("sha256_modelo")

    if str(metadata_hash).lower() != actual_hash.lower():
        raise ValueError(
            "SHA-256 do modelo diverge dos metadados."
        )

    # Validar o contrato das features.
    if tuple(metadata.get("features", [])) != MODEL_FEATURES:
        raise ValueError(
            "As features dos metadados não correspondem "
            "ao contrato congelado do KNN V2."
        )

    # Validar os hiperparâmetros registrados.
    expected_parameters = {
        "n_neighbors": 21,
        "weights": "uniform",
        "algorithm": "kd_tree",
        "metric": "minkowski",
        "p": 2,
        "leaf_size": 40,
    }

    metadata_parameters = metadata.get(
        "hiperparametros", {}
    )

    if metadata_parameters != expected_parameters:
        raise ValueError(
            "Os hiperparâmetros dos metadados "
            "não correspondem à configuração congelada."
        )

    # Validar o limiar registrado.
    threshold = float(metadata.get("limiar", -1))

    if not np.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError(
            "Limiar inválido nos metadados do KNN V2."
        )

    if not np.isclose(
        threshold,
        DEFAULT_THRESHOLD,
        rtol=0,
        atol=1e-12,
    ):
        raise ValueError(
            "O limiar diverge do valor congelado na validação."
        )

    # Carregar somente artefatos de origem confiável.
    # O Joblib não deve ser utilizado com arquivos desconhecidos.
    import joblib

    pacote = joblib.load(model_path)

    if not isinstance(pacote, dict):
        raise TypeError(
            "O artefato KNN V2 deveria ser um dicionário."
        )

    required_keys = {
        "modelo",
        "scaler",
        "features",
        "target",
        "limiar",
        "hiperparametros",
    }

    missing_keys = required_keys - set(pacote.keys())

    if missing_keys:
        raise ValueError(
            f"Chaves ausentes no artefato: {sorted(missing_keys)}"
        )

    # Recuperar os dois objetos treinados no Colab.
    modelo = pacote["modelo"]
    scaler = pacote["scaler"]

    if not isinstance(modelo, KNeighborsClassifier):
        raise TypeError(
            "O classificador interno não é um KNeighborsClassifier."
        )

    if not isinstance(scaler, StandardScaler):
        raise TypeError(
            "O scaler interno não é um StandardScaler."
        )

    # Conferir o contrato armazenado dentro do próprio artefato.
    if tuple(pacote["features"]) != MODEL_FEATURES:
        raise ValueError(
            "As features do pacote congelado estão incompatíveis."
        )

    if pacote["target"] != "eh_fraude":
        raise ValueError(
            "O target registrado no pacote não corresponde a eh_fraude."
        )

    if not np.isclose(
        float(pacote["limiar"]),
        threshold,
        rtol=0,
        atol=1e-12,
    ):
        raise ValueError(
            "O limiar do pacote diverge dos metadados."
        )

    # Confirmar os parâmetros efetivos do classificador.
    for nome, esperado in expected_parameters.items():

        obtido = modelo.get_params(deep=False).get(nome)

        if obtido != esperado:
            raise ValueError(
                f"Parâmetro incompatível: {nome}. "
                f"Esperado: {esperado}; recebido: {obtido}."
            )

    # Confirmar o tamanho da estrutura treinada.
    if modelo.n_features_in_ != len(MODEL_FEATURES):
        raise ValueError(
            "Quantidade de features incompatível no classificador."
        )

    if scaler.n_features_in_ != len(MODEL_FEATURES):
        raise ValueError(
            "Quantidade de features incompatível no StandardScaler."
        )

    expected_samples = int(
        metadata.get("treino_registros_amostra", 294831)
    )

    if modelo.n_samples_fit_ != expected_samples:
        raise ValueError(
            "Quantidade de registros treinados incompatível."
        )

    if not np.array_equal(
        modelo.classes_,
        np.array([0, 1])
    ):
        raise ValueError(
            "As classes do modelo não correspondem a [0, 1]."
        )

    return KNNV2Artifacts(
        modelo=modelo,
        scaler=scaler,
        features=MODEL_FEATURES,
        threshold=threshold,
        model_sha256=actual_hash,
        metadata=metadata,
    )


# ============================================================
# 5. PREPARAÇÃO E VALIDAÇÃO DAS FEATURES
# ============================================================

def prepare_knn_v2_features(
    transacoes: pd.DataFrame,
) -> pd.DataFrame:
    """
    Seleciona, organiza e valida as sete features da Gold KNN.

    As transformações da Gold são preservadas.
    Não aplica nova normalização nesta etapa.
    """

    _validate_dataframe(transacoes)

    # Verificar colunas exigidas.
    missing = [
        column
        for column in MODEL_FEATURES
        if column not in transacoes.columns
    ]

    if missing:
        raise ValueError(
            "Features ausentes para o KNN V2: "
            f"{missing}"
        )

    # Selecionar somente as sete features oficiais.
    # O target eh_fraude não participa da inferência.
    features = transacoes.loc[
        :, list(MODEL_FEATURES)
    ].copy()

    # Converter todas as features para valores numéricos.
    for column in MODEL_FEATURES:

        features[column] = pd.to_numeric(
            features[column],
            errors="coerce"
        )

        values = features[column].to_numpy(
            dtype=np.float64
        )

        if not np.isfinite(values).all():
            raise ValueError(
                f"A feature '{column}' possui valores "
                "nulos, inválidos ou não finitos."
            )

    # Validar as features binárias.
    for column in BINARY_FEATURES:

        if not features[column].isin([0, 1]).all():
            raise ValueError(
                f"A feature '{column}' deve conter somente 0 ou 1."
            )

        features[column] = features[column].astype("int8")

    # Validar os intervalos das features normalizadas.
    for column in NORMALIZED_FEATURES:

        if not features[column].between(0, 1).all():
            raise ValueError(
                f"A feature '{column}' deve estar no intervalo [0, 1]."
            )

        features[column] = features[column].astype("float64")

    # Garantir a ordem congelada.
    if tuple(features.columns) != MODEL_FEATURES:
        raise RuntimeError(
            "A ordem das features diverge do contrato KNN V2."
        )

    return features


# ============================================================
# 6. SCORING E GERAÇÃO DE ALERTAS
# ============================================================

def score_knn_v2_transactions(
    transacoes: pd.DataFrame,
    artifacts: KNNV2Artifacts,
) -> pd.DataFrame:
    """
    Calcula o score de votação dos vizinhos e gera alertas.

    Reutiliza o scaler e o classificador congelados.
    """

    if not isinstance(artifacts, KNNV2Artifacts):
        raise TypeError(
            "Informe os artefatos carregados por "
            "load_knn_v2_artifacts()."
        )

    # Preparar as sete features na ordem oficial.
    features = prepare_knn_v2_features(transacoes)

    # Converter para NumPy, preservando a ordem das features.
    X = features.to_numpy(dtype=np.float64)

    # Aplicar exclusivamente o scaler ajustado no treinamento.
    X_scaled = artifacts.scaler.transform(X)

    # Verificar a transformação.
    if not np.isfinite(X_scaled).all():
        raise ValueError(
            "O scaler retornou valores não finitos."
        )

    # Executar a votação do KNN.
    probabilities = artifacts.modelo.predict_proba(X_scaled)

    # Localizar a coluna correspondente à classe fraude.
    fraud_class_index = list(
        artifacts.modelo.classes_
    ).index(1)

    scores = probabilities[:, fraud_class_index]

    # Validar scores.
    if len(scores) != len(transacoes):
        raise ValueError(
            "A quantidade de scores difere da quantidade de transações."
        )

    if not np.isfinite(scores).all():
        raise ValueError(
            "O KNN retornou scores não finitos."
        )

    if ((scores < 0) | (scores > 1)).any():
        raise ValueError(
            "O KNN retornou scores fora do intervalo [0, 1]."
        )

    # Aplicar o limiar congelado na validação.
    alerts = scores >= artifacts.threshold

    # Preservar os dados originais e anexar os resultados.
    resultado = transacoes.copy()

    resultado["fraud_score"] = scores
    resultado["fraud_alert"] = alerts
    resultado["status_analise"] = np.where(
        alerts,
        "ALERTA",
        "SEM_ALERTA",
    )

    resultado["limiar"] = artifacts.threshold
    resultado["nome_modelo"] = MODEL_NAME
    resultado["sha256_modelo"] = artifacts.model_sha256

    return resultado


# ============================================================
# 7. RESUMO OPERACIONAL
# ============================================================

def summarize_knn_v2(
    resultado: pd.DataFrame,
) -> dict[str, int | float]:
    """Resume os alertas e os scores produzidos pelo KNN V2."""

    required = {
        "fraud_score",
        "fraud_alert",
    }

    missing = required - set(resultado.columns)

    if missing:
        raise ValueError(
            f"Colunas ausentes no resultado: {sorted(missing)}"
        )

    total = int(len(resultado))

    alerts = int(
        resultado["fraud_alert"].astype(bool).sum()
    )

    mean_score = (
        float(resultado["fraud_score"].mean())
        if total
        else 0.0
    )

    return {
        "modelo": MODEL_NAME,
        "total_transacoes_analisadas": total,
        "total_alertas": alerts,
        "taxa_alertas": alerts / total if total else 0.0,
        "score_medio_modelo": mean_score,
    }
