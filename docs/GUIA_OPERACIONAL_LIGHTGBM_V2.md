# Guia operacional — LightGBM V2

## 1. Pré-requisitos

- Python 3.12.x.
- Ambiente virtual do projeto ativado.
- Dependências instaladas, incluindo `lightgbm==4.7.0`, `pandas`, `numpy` e `databricks-sql-connector[pyarrow]` conforme o `requirements.txt`/requirements específico do projeto.
- Arquivos do modelo e metadados em `models/`.
- `.env` na raiz com `DATABRICKS_SERVER_HOSTNAME`, `DATABRICKS_HTTP_PATH` e `DATABRICKS_TOKEN`. Não versionar o `.env` nem colar credenciais no terminal/chat.
- Permissões de leitura na Gold ML e, para persistência, permissões de CREATE/WRITE/DELETE/MERGE no schema `workspace.ml_experiments`.

## 2. Modo prévia (não grava)

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m finops_ml.run_scoring --start-step 632 --end-step 743 --limit 100
```

Sem `--write`, a consulta não depende da tabela de resultados para excluir registros já processados e não persiste valores.

## 3. Teste pequeno com persistência

```powershell
.\.venv\Scripts\python.exe -m finops_ml.run_scoring --start-step 632 --end-step 632 --limit 100 --write --insert-chunk-size 250
```

Depois, consulte a tabela `workspace.ml_experiments.gbm_v2_scoring_resultados` e confira total, IDs únicos, alertas e exposição sinalizada. Teste também uma reexecução sequencial para verificar que o `NOT EXISTS` exclui o que já foi pontuado com o mesmo hash.

## 4. Processamento incremental de todo um intervalo

```powershell
.\.venv\Scripts\python.exe -m finops_ml.run_scoring --start-step 632 --end-step 743 --batch-size 5000 --insert-chunk-size 250 --write
```

O `--limit` limita a quantidade total de registros de uma execução; sem `--limit`, o executor percorre todos os registros pendentes no intervalo. Se usar `--limit`, uma nova execução pode buscar o próximo bloco de registros ainda não pontuados. Isso não significa duplicação: confirme a ausência de IDs em comum entre Run IDs distintos.

Execute apenas uma instância por vez. A prevenção de duplicidade foi validada em execuções sequenciais; execução concorrente simultânea não foi testada.

## 5. SQL de conferência por Run ID

```sql
SELECT
  COUNT(*) AS total_registros,
  COUNT(DISTINCT id_transacao) AS ids_unicos,
  SUM(CASE WHEN fraud_alert THEN 1 ELSE 0 END) AS total_alertas,
  SUM(valor_sinalizado) AS exposicao_sinalizada
FROM workspace.ml_experiments.gbm_v2_scoring_resultados
WHERE run_id = '<RUN_ID>';
```

Staging do Run ID:

```sql
SELECT COUNT(*) AS registros_staging
FROM workspace.ml_experiments.gbm_v2_scoring_staging
WHERE run_id = '<RUN_ID>';
```

## 6. Auditoria de cobertura do conjunto de teste

Executar apenas para o conjunto de teste histórico e com o hash congelado:

```sql
WITH origem AS (
  SELECT id_transacao, step
  FROM workspace.ml_experiments.gbm_v2_teste_gold_corrigida
),
resultados AS (
  SELECT id_transacao, step, fraud_alert, valor_sinalizado
  FROM workspace.ml_experiments.gbm_v2_scoring_resultados
  WHERE sha256_modelo = '29f183255645bbcdef16c96ca802f02d121476548a18e224cad82298e488c076'
    AND step BETWEEN 632 AND 743
)
SELECT
  (SELECT COUNT(*) FROM origem) AS total_origem,
  (SELECT COUNT(*) FROM resultados) AS total_processado,
  (SELECT COUNT(DISTINCT id_transacao) FROM resultados) AS ids_unicos,
  (SELECT COUNT(*) - COUNT(DISTINCT id_transacao) FROM resultados) AS duplicados,
  (SELECT COUNT(*) FROM origem o LEFT ANTI JOIN resultados r
    ON o.id_transacao = r.id_transacao AND o.step = r.step) AS sem_score,
  (SELECT COUNT(*) FROM resultados r LEFT ANTI JOIN origem o
    ON r.id_transacao = o.id_transacao AND r.step = o.step) AS fora_do_teste,
  (SELECT SUM(CASE WHEN fraud_alert THEN 1 ELSE 0 END) FROM resultados) AS total_alertas,
  (SELECT SUM(valor_sinalizado) FROM resultados) AS exposicao_sinalizada;
```

## 7. Recuperação após interrupção

1. Não inicie outra execução antes de confirmar que a anterior foi encerrada.
2. Identifique o Run ID no terminal.
3. Consulte `gbm_v2_scoring_staging` e `gbm_v2_scoring_resultados` para esse Run ID.
4. A staging é removida após cada MERGE; se houver falha, verifique se restaram linhas antes de limpá-las.
5. Reinicie com o mesmo SHA-256 e intervalo. A consulta de inferência exclui IDs já persistidos para esse hash.
6. Não apague staging de outro Run ID nem os resultados definitivos sem auditoria.

## 8. Arquivos e tabelas

- Executor: `src/finops_ml/run_scoring.py`.
- Scoring/model loader: `src/finops_ml/fraud_scoring.py`.
- Leitura Gold: `src/finops_ml/databricks_loader.py`.
- Resultados: `workspace.ml_experiments.gbm_v2_scoring_resultados`.
- Staging: `workspace.ml_experiments.gbm_v2_scoring_staging`.
- SQL Views nativas do Databricks: `sql/lightgbm_v2_databricks_views.sql`.
- Guia do dashboard nativo Databricks AI/BI: `dashboard/databricks/README.md`.

A tabela operacional não contém a variável alvo. Ela guarda score, alerta, valor sinalizado, identificador, step, hash do modelo, limiar, Run ID e timestamp. Precision/Recall/F1 exigem rótulo confirmado e pertencem à avaliação, não ao monitoramento online sem labels.


## 9. Camada de consumo e monitoramento nativa do Databricks

Toda a solução utiliza Databricks. As SQL Views são criadas no próprio Databricks SQL e alimentam um AI/BI Dashboard nativo do workspace.

Execute `sql/lightgbm_v2_databricks_views.sql` no SQL Editor, conectado a um SQL Warehouse. O script cria:

- `vw_gbm_v2_dashboard_detalhado`
- `vw_gbm_v2_dashboard_resumo_step`
- `vw_gbm_v2_dashboard_alertas`
- `vw_gbm_v2_dashboard_avaliacao_teste`

Depois siga `dashboard/databricks/README.md` para montar o dashboard no próprio Databricks. A view de avaliação é histórica e usa rótulos do conjunto de teste; as views operacionais não expõem `eh_fraude`.
