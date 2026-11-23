# Operacionalização do LightGBM V2 — Grupo 5

## Executor

`src/finops_ml/run_scoring.py` executa o scoring incremental do LightGBM V2. A consulta de inferência lê `id_transacao`, `step`, `dia_absoluto` e as dez features do modelo; não seleciona `eh_fraude` nem `flag_fraude_sistema`.

Por padrão, roda em prévia sem persistência. Use `--write` para gravar em tabelas Delta separadas da Gold ML.

## Persistência em lotes

A gravação usa `INSERT INTO ... VALUES (...), (...), ...` parametrizado em grupos de até 250 linhas por comando (ajustável com `--insert-chunk-size`, entre 1 e 500). Isso evita o padrão anterior de `executemany` que gerou uma consulta de INSERT para cada transação no histórico do SQL Warehouse. A sintaxe de INSERT multi-row é suportada pelo Databricks SQL. Para volumes muito maiores, a recomendação de longo prazo é fazer upload de Parquet para um Unity Catalog Volume/cloud storage e usar `COPY INTO`.

Cada lote é transferido para staging, seguido de `MERGE` Delta para a tabela final. A chave lógica é `(id_transacao, sha256_modelo)`. A limpeza da staging daquele Run ID é tentada no bloco `finally`, inclusive quando ocorre falha durante a inserção ou o MERGE.

Tabelas usadas:

- `workspace.ml_experiments.gbm_v2_scoring_resultados`
- `workspace.ml_experiments.gbm_v2_scoring_staging`

## Prévia

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m finops_ml.run_scoring --start-step 632 --end-step 632 --limit 100
```

## Teste pequeno com gravação

Após revisar a prévia e confirmar permissões no schema:

```powershell
.\.venv\Scripts\python.exe -m finops_ml.run_scoring --start-step 632 --end-step 632 --limit 100 --write
```

## Processamento do intervalo de teste

Após validar o teste pequeno e a reexecução idempotente:

```powershell
.\.venv\Scripts\python.exe -m finops_ml.run_scoring --start-step 632 --end-step 743 --write --batch-size 5000 --insert-chunk-size 250
```

O executor ignora transações já persistidas para o mesmo SHA-256 do modelo. Uma nova versão aprovada, com hash diferente, produz um registro distinto por transação.

## Testes locais

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m pytest .\tests\test_run_scoring.py .\tests\test_lightgbm_v2_integration.py -v
```

## Observações operacionais

- Não execute novamente um processamento completo antes de confirmar que o processo anterior terminou.
- A primeira prévia não grava dados.
- A primeira gravação deve ser limitada e conferida por SQL.
- O script não altera a Gold ML e não retreina o modelo.
- A inferência não usa rótulos reais. A avaliação de métricas é separada.
- Se uma execução for interrompida, confira staging e resultados pelo `run_id` antes de limpar ou repetir.
