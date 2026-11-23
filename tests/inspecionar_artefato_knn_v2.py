# ============================================================
# INSPECAO DO ARTEFATO KNN V2
# Identificar a estrutura real do objeto serializado.
# ============================================================

from pathlib import Path
import json
import joblib

# Localizar os artefatos dentro do projeto
RAIZ = Path(__file__).resolve().parents[1]
PASTA = RAIZ / "models" / "knn_v2"

ARQUIVO_MODELO = PASTA / "knn_v2_modelo_congelado.joblib"
ARQUIVO_METADATA = PASTA / "knn_v2_metadata_congelado.json"

print("=" * 60)
print("INSPECAO DO ARTEFATO KNN V2")
print("=" * 60)

# Carregar o objeto original sem modificá-lo
modelo = joblib.load(ARQUIVO_MODELO)

# Identificar a classe real do objeto
print("\n=== IDENTIDADE DO OBJETO ===")
print("Tipo:", type(modelo))
print("Classe:", type(modelo).__name__)
print("Modulo:", type(modelo).__module__)
print("Heranca:", type(modelo).__mro__)

# Verificar os métodos e atributos disponíveis
print("\n=== ATRIBUTOS DISPONIVEIS ===")

for atributo in [
    "fit",
    "predict",
    "predict_proba",
    "get_params",
    "n_features_in_",
    "classes_",
    "n_samples_fit_",
    "steps",
    "named_steps",
    "estimators_"
]:
    print(f"{atributo}: {hasattr(modelo, atributo)}")

# Mostrar os parâmetros, caso existam
if hasattr(modelo, "get_params"):
    print("\n=== PARAMETROS ===")
    print(modelo.get_params(deep=False))

# Verificar se o objeto é um dicionário
if isinstance(modelo, dict):
    print("\n=== CHAVES DO DICIONARIO ===")

    for chave, valor in modelo.items():
        print(chave, "->", type(valor))

# Verificar se é um Pipeline
if hasattr(modelo, "named_steps"):
    print("\n=== ETAPAS DO PIPELINE ===")

    for nome, etapa in modelo.named_steps.items():
        print(nome, "->", type(etapa))

# Carregar e exibir os metadados
with open(ARQUIVO_METADATA, "r", encoding="utf-8") as arquivo:
    metadata = json.load(arquivo)

print("\n=== METADADOS DO MODELO ===")
print(json.dumps(metadata, indent=2, ensure_ascii=False))

print("\nINSPECAO CONCLUIDA.")
