# Integração do LightGBM V2 — Grupo 5

Este pacote substitui o scoring antigo pelo Booster nativo do LightGBM V2 congelado.

## Estrutura entregue

```text
models/
  lightgbm_v2_modelo_congelado.txt
  lightgbm_v2_metadata_congelado.json
src/finops_ml/
  __init__.py
  fraud_scoring.py
  gold_ml_features.py
tests/
  test_lightgbm_v2_integration.py
requirements-lightgbm-v2.txt
```

## Como aplicar no seu repositório

1. Copie a pasta `models/` para a raiz do projeto.
2. Substitua os dois módulos em `src/finops_ml/` pelos arquivos entregues.
3. No terminal do VS Code, crie/ative seu ambiente virtual e instale as dependências:

   **Windows PowerShell**
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements-lightgbm-v2.txt
   $env:PYTHONPATH = "src"
   python -m pytest -q
   ```

   **Linux/macOS**
   ```bash
   python -m pip install -r requirements-lightgbm-v2.txt
   PYTHONPATH=src python -m pytest -q
   ```

## Uso básico

Com `src` no `PYTHONPATH`:

```python
from finops_ml.fraud_scoring import load_model_artifacts, score_transactions

modelo, config, metadata = load_model_artifacts()
resultado = score_transactions(modelo, transacoes, config)
```

`transacoes` precisa conter as 10 features do contrato V2. As cinco flags de tipo
podem ser derivadas da coluna `type`, e `amount` pode ser usado como alias de
`valor`. A flag `destino_eh_comercio` e as duas contagens de recebimentos precisam
ser fornecidas com a definição do pipeline Gold ML usado no treinamento; o código
não tenta inventar nem substituir essas informações.

## Atenção à Gold ML

O arquivo enviado originalmente tinha `qtd_recebimentos_anterior` e `dia_semana`.
O modelo congelado exige `qtd_recebimentos_destino_hist` e
`qtd_recebimentos_destino_24h`, e não utiliza `dia_semana`. O módulo atualizado
passa a exigir o contrato do modelo. Portanto, confirme que a tabela/view Gold ML
realmente entrega as duas contagens exigidas antes de executar o pipeline.

## Integridade e status do modelo

Ao carregar, o módulo confere SHA-256, lista e ordem de features, limiar, status de
congelamento e quantidade de árvores. O limiar vem dos metadados (`0.0834140673`).
Os metadados enviados ainda descrevem a avaliação no conjunto de teste como
reservada/pendente; o pacote não altera esse status nem afirma que o teste
independente foi concluído.
