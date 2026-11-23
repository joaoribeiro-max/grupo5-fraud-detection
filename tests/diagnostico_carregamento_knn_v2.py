
# ============================================================
# DIAGNÓSTICO DE CARREGAMENTO DO KNN V2
# Verificar compatibilidade e capacidade de inferência local.
# ============================================================

from pathlib import Path
import hashlib
import json
import warnings

import numpy as np
import scipy
import sklearn
import joblib

from sklearn.neighbors import KNeighborsClassifier

# 1. Definir os caminhos dos artefatos
PASTA = Path("models/knn_v2")

ARQUIVO_MODELO = PASTA / "knn_v2_modelo_congelado.joblib"
ARQUIVO_METADATA = PASTA / "knn_v2_metadata_congelado.json"

# 2. Verificar se os arquivos existem
assert ARQUIVO_MODELO.exists(), "Modelo não encontrado."
assert ARQUIVO_METADATA.exists(), "Metadados não encontrados."

# 3. Calcular e validar o SHA-256
hash_atual = hashlib.sha256(
    ARQUIVO_MODELO.read_bytes()
).hexdigest()

hash_esperado = (
    "43a6e622b1d9182e47ac0ab4ec813016c0195ab08d23bbab7ede09e4b3ba370a"
)

assert hash_atual.lower() == hash_esperado.lower()

print("SHA-256 confirmado:", hash_atual)

# 4. Exibir as versões do ambiente
print("\n=== VERSÕES DO AMBIENTE ===")
print("NumPy:", np.__version__)
print("SciPy:", scipy.__version__)
print("Scikit-learn:", sklearn.__version__)
print("Joblib:", joblib.__version__)

# 5. Carregar os metadados
with open(ARQUIVO_METADATA, "r", encoding="utf-8") as arquivo:
    metadata = json.load(arquivo)

print("\n=== METADADOS DO MODELO ===")
print("Modelo:", metadata.get("modelo"))
print("Features:", metadata.get("features"))

# 6. Carregar o modelo congelado
# Utilizar somente o artefato de origem confiável do projeto.
print("\nCarregando modelo...")

with warnings.catch_warnings(record=True) as avisos:
    warnings.simplefilter("always")
    modelo = joblib.load(ARQUIVO_MODELO)

# Exibir eventuais avisos de compatibilidade
for aviso in avisos:
    print(
        "AVISO:",
        aviso.category.__name__,
        "-",
        str(aviso.message)
    )

# 7. Conferir a classe do modelo
assert isinstance(modelo, KNeighborsClassifier)

# 8. Validar os parâmetros congelados
assert modelo.n_features_in_ == 7
assert modelo.n_samples_fit_ == 294_831
assert np.array_equal(modelo.classes_, [0, 1])

assert modelo.n_neighbors == 21
assert modelo.weights == "uniform"
assert modelo.algorithm == "kd_tree"
assert modelo.p == 2

print("\n=== ESTRUTURA DO MODELO ===")
print("Tipo:", type(modelo).__name__)
print("Features:", modelo.n_features_in_)
print("Registros de treinamento:", modelo.n_samples_fit_)
print("Número de vizinhos:", modelo.n_neighbors)
print("Pesos:", modelo.weights)
print("Algoritmo:", modelo.algorithm)
print("Distância p:", modelo.p)

# 9. Executar um teste técnico de inferência
# Os zeros são apenas dados artificiais para testar a execução.
X_teste = np.zeros((2, 7), dtype=np.float32)

probabilidades = modelo.predict_proba(X_teste)

assert probabilidades.shape == (2, 2)
assert np.isfinite(probabilidades).all()

print("\n=== TESTE DE INFERÊNCIA ===")
print("Formato das probabilidades:", probabilidades.shape)
print("Predições tecnicamente executadas:")
print(probabilidades)

print("\nDIAGNÓSTICO CONCLUÍDO!")
