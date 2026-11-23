
# ============================================================
# TESTE DE INFERÊNCIA - KNN V2
# Utiliza o scaler e o classificador congelados no Colab.
# Não realiza novo treinamento.
# ============================================================

from pathlib import Path
import hashlib
import joblib
import json

import numpy as np
import pandas as pd

from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler

# 1. Localizar os artefatos
RAIZ = Path(__file__).resolve().parents[1]
PASTA = RAIZ / "models" / "knn_v2"

ARQUIVO_MODELO = PASTA / "knn_v2_modelo_congelado.joblib"
ARQUIVO_METADATA = PASTA / "knn_v2_metadata_congelado.json"

# 2. Conferir a integridade do arquivo
hash_atual = hashlib.sha256(
    ARQUIVO_MODELO.read_bytes()
).hexdigest()

hash_esperado = (
    "43a6e622b1d9182e47ac0ab4ec813016c0195ab08d23bbab7ede09e4b3ba370a"
)

assert hash_atual.lower() == hash_esperado.lower()

print("SHA-256 confirmado.")

# 3. Carregar o pacote congelado
artefato = joblib.load(ARQUIVO_MODELO)

# 4. Confirmar que o objeto externo é um dicionário
assert isinstance(artefato, dict)

chaves_esperadas = {
    "modelo",
    "scaler",
    "features",
    "target",
    "limiar",
    "hiperparametros"
}

assert chaves_esperadas.issubset(artefato.keys())

# 5. Separar o classificador e o scaler
modelo = artefato["modelo"]
scaler = artefato["scaler"]
features = artefato["features"]
limiar = float(artefato["limiar"])

# 6. Validar os tipos dos objetos internos
assert isinstance(modelo, KNeighborsClassifier)
assert isinstance(scaler, StandardScaler)

# 7. Validar as features
assert len(features) == 7
assert scaler.n_features_in_ == 7
assert modelo.n_features_in_ == 7
assert modelo.n_samples_fit_ == 294_831

# 8. Conferir os metadados
with open(ARQUIVO_METADATA, "r", encoding="utf-8") as arquivo:
    metadata = json.load(arquivo)

assert features == metadata["features"]
assert abs(limiar - metadata["limiar"]) < 1e-12

print("\n=== CONFIGURAÇÃO VALIDADA ===")
print("Classificador:", type(modelo).__name__)
print("Scaler:", type(scaler).__name__)
print("Features:", features)
print("Vizinhos:", modelo.n_neighbors)
print("Pesos:", modelo.weights)
print("Algoritmo:", modelo.algorithm)
print("Distância p:", modelo.p)
print("Limiar:", limiar)

# 9. Criar uma entrada artificial para testar a inferência
# Utilizar NumPy, pois o scaler foi ajustado com arrays NumPy.
X_exemplo = np.asarray(
    scaler.mean_,
    dtype=np.float64
).reshape(1, -1)

# 10. Aplicar a transformação usando o scaler congelado
X_transformado = scaler.transform(X_exemplo)

# 11. Executar a classificação com o modelo congelado
scores = modelo.predict_proba(X_transformado)

# 12. Extrair o score correspondente à classe fraude
indice_fraude = list(modelo.classes_).index(1)

score_fraude = float(scores[0, indice_fraude])

# 13. Aplicar o limiar congelado
alerta = int(score_fraude >= limiar)

# 14. Exibir o resultado técnico
print("\n=== RESULTADO DO TESTE ===")
print("Score de votação:", round(score_fraude, 6))
print("Limiar:", round(limiar, 6))
print("Alerta:", alerta)

print("\nINFERÊNCIA EXECUTADA COM SUCESSO!")
print("Scaler e classificador carregados.")
print("Nenhum novo treinamento realizado.")
