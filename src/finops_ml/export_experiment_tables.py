"""Exportacao dos conjuntos LightGBM V2 para Parquet."""

import os
from pathlib import Path

import pyarrow.parquet as pq
from databricks import sql
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "gbm_v2"

EXPORT_CONFIG = {
    "treino": {
        "table": "workspace.ml_experiments.gbm_v2_treino_amostra",
        "filename": "treino.parquet",
        "expected_rows": 127396,
    },
    "validacao": {
        "table": "workspace.ml_experiments.gbm_v2_validacao",
        "filename": "validacao.parquet",
        "expected_rows": 191147,
    },
    "teste": {
        "table": "workspace.ml_experiments.gbm_v2_teste",
        "filename": "teste.parquet",
        "expected_rows": 89466,
    },
}


def _connect():
    """Estabelece conexao com o Databricks."""

    keys = [
        "DATABRICKS_SERVER_HOSTNAME",
        "DATABRICKS_HTTP_PATH",
        "DATABRICKS_TOKEN",
    ]

    missing = [key for key in keys if not os.getenv(key)]

    if missing:
        raise RuntimeError(
            f"Credenciais ausentes no .env: {missing}"
        )

    return sql.connect(
        server_hostname=os.environ["DATABRICKS_SERVER_HOSTNAME"],
        http_path=os.environ["DATABRICKS_HTTP_PATH"],
        access_token=os.environ["DATABRICKS_TOKEN"],
    )


def export_table_to_parquet(
    dataset: str,
    batch_size: int = 2000,
) -> dict:
    """Exporta uma tabela em lotes Arrow para Parquet."""

    if dataset not in EXPORT_CONFIG:
        raise ValueError(f"Conjunto nao autorizado: {dataset}")

    if not isinstance(batch_size, int) or not 1 <= batch_size <= 10000:
        raise ValueError("Batch size deve estar entre 1 e 10000.")

    config = EXPORT_CONFIG[dataset]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_path = OUTPUT_DIR / config["filename"]
    partial_path = OUTPUT_DIR / f"{config['filename']}.partial"

    if output_path.exists():
        raise FileExistsError(
            f"O arquivo ja existe: {output_path}. "
            "Nao sera sobrescrito automaticamente."
        )

    partial_path.unlink(missing_ok=True)

    connection = None
    cursor = None
    writer = None

    total_rows = 0
    lotes = 0

    query = f"SELECT * FROM {config['table']}"

    try:
        connection = _connect()
        cursor = connection.cursor()

        print(
            f"Iniciando exportacao: {dataset}",
            flush=True,
        )

        cursor.execute(query)

        while True:
            arrow_batch = cursor.fetchmany_arrow(batch_size)

            if arrow_batch is None or arrow_batch.num_rows == 0:
                break

            if writer is None:
                writer = pq.ParquetWriter(
                    partial_path,
                    arrow_batch.schema,
                    compression="snappy",
                )

            writer.write_table(arrow_batch)

            total_rows += arrow_batch.num_rows
            lotes += 1

            print(
                f"{dataset} | Lote {lotes} | "
                f"Registros: {total_rows:,}",
                flush=True,
            )

        if writer is not None:
            writer.close()
            writer = None

        if total_rows != config["expected_rows"]:
            raise RuntimeError(
                f"Quantidade divergente em {dataset}: "
                f"esperado {config['expected_rows']}, "
                f"recebido {total_rows}."
            )

        if total_rows == 0:
            raise RuntimeError("Nenhum registro foi exportado.")

        # Publica o arquivo somente apos validar a quantidade.
        partial_path.replace(output_path)

        size_mb = output_path.stat().st_size / (1024 ** 2)

        resultado = {
            "conjunto": dataset,
            "registros": total_rows,
            "lotes": lotes,
            "arquivo": str(output_path),
            "tamanho_mb": round(size_mb, 2),
            "status": "APROVADO",
        }

        print(
            f"Exportacao concluida: {dataset} | "
            f"{total_rows:,} registros | {size_mb:.2f} MB",
            flush=True,
        )

        return resultado

    except Exception:
        partial_path.unlink(missing_ok=True)
        raise

    finally:
        if writer is not None:
            writer.close()

        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()


def export_all_experiment_tables(
    batch_size: int = 2000,
) -> list[dict]:
    """Exporta os tres conjuntos experimentais."""

    resultados = []

    for dataset in ("treino", "validacao", "teste"):
        resultado = export_table_to_parquet(
            dataset=dataset,
            batch_size=batch_size,
        )

        resultados.append(resultado)

    return resultados
