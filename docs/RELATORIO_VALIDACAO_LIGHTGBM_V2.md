# Relatório da integração — LightGBM V2

## Verificações realizadas

- SHA-256 do modelo: `29f183255645bbcdef16c96ca802f02d121476548a18e224cad82298e488c076`.
- O hash calculado para o arquivo enviado corresponde ao hash `sha256_modelo` dos metadados.
- O arquivo nativo foi aberto como `lightgbm.Booster`.
- O Booster contém 137 árvores e 10 features, com nomes e ordem iguais aos metadados.
- O limiar carregado é `0.08341406734582016`.
- Testes de integração: **5 aprovados**.

## Problemas corrigidos nos módulos enviados

1. `fraud_scoring.py` antigo usava `joblib`, `predict_proba()`, quatro features antigas e limiar `0.012455...`; isso não é compatível com o arquivo `.txt` do modelo V2. Foi trocado para `lightgbm.Booster`, `predict()` e as 10 features do modelo congelado.
2. `gold_ml_features.py` antigo usava `qtd_recebimentos_anterior` e `dia_semana`. O contrato do modelo usa `qtd_recebimentos_destino_hist` e `qtd_recebimentos_destino_24h`, sem `dia_semana`. A validação e a ordem das features foram corrigidas.
3. O carregamento agora verifica o hash do modelo, a ordem das features, o limiar registrado, o status de congelamento e a quantidade de árvores.

## Aviso de ambiente

Os metadados registram LightGBM `4.7.0`. O ambiente onde os testes foram executados tinha `4.6.0`; ele conseguiu abrir e pontuar o Booster, e os cinco testes passaram, mas emitiu aviso de divergência. O arquivo `requirements-lightgbm-v2.txt` fixa `lightgbm==4.7.0` para alinhar o ambiente do VS Code ao treinamento.

## Ponto pendente fora destes quatro arquivos

É necessário confirmar que a origem da Gold ML (view/tabela/parquet/Dataform) realmente fornece `qtd_recebimentos_destino_hist` e `qtd_recebimentos_destino_24h` com as mesmas regras usadas no treino. Os módulos não fazem substituições aproximadas por `qtd_recebimentos_anterior`, pois isso poderia alterar o significado das features e invalidar o scoring.

Os metadados enviados classificam a avaliação do conjunto de teste como reservada/pendente. Esta integração não altera esse status nem equivale à validação independente de desempenho.
