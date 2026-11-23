
# ============================================================
# VALIDACAO DE EQUIVALENCIA - KNN V2
# Projeto: Grupo 5 - Deteccao de Fraudes
#
# Objetivo:
# Comparar as previsoes originais do Google Colab com as
# inferencias executadas no VS Code.
#
# Populacao:
# Teste reservado - steps 632 a 743.
#
# O modelo, o scaler e o limiar permanecem congelados.
# ============================================================

from pathlib import Path
import json

import numpy as np
import pandas as pd

from finops_ml.knn_v2_loader import iter_gold_knn_v2_batches

from finops_ml.knn_v2_predictor import (
    load_knn_v2_artifacts,
    score_knn_v2_transactions,
)


# ============================================================
# 1. CONFIGURACOES
# ============================================================

# Identificar a raiz do projeto.
RAIZ_PROJETO = Path(__file__).resolve().parents[1]

# Localizar a pasta dos artefatos KNN V2.
PASTA_ARTEFATOS = RAIZ_PROJETO / "models" / "knn_v2"

# Arquivo de previsoes originais do Google Colab.
ARQUIVO_REFERENCIA = (
    PASTA_ARTEFATOS / "knn_v2_previsoes_teste_auditoria.csv"
)

# Pasta para armazenar os resultados da auditoria.
PASTA_RELATORIOS = RAIZ_PROJETO / "reports" / "knn_v2"

PASTA_RELATORIOS.mkdir(
    parents=True,
    exist_ok=True
)

# Arquivos de saida.
ARQUIVO_RELATORIO = (
    PASTA_RELATORIOS / "knn_v2_validacao_equivalencia_colab.csv"
)

ARQUIVO_RESUMO = (
    PASTA_RELATORIOS / "knn_v2_validacao_equivalencia_resumo.json"
)

# Intervalo temporal do teste reservado.
STEP_INICIAL = 632
STEP_FINAL = 743

# Tamanho dos lotes consultados no Databricks.
TAMANHO_LOTE = 5_000

# Quantidade esperada de registros no teste.
TOTAL_ESPERADO = 37_979

# Quantidade esperada de fraudes reais no teste.
FRAUDES_ESPERADAS = 1_252

# Tolerancia numerica para comparar os scores.
TOLERANCIA = 1e-12

# Limiar congelado na validacao.
LIMIAR_CONGELADO = 0.47619047619047616


# ============================================================
# 2. FUNCAO DE NORMALIZACAO DOS ALERTAS
# ============================================================

def normalizar_alertas(serie: pd.Series) -> pd.Series:
    """
    Converte os alertas do CSV para valores inteiros 0 ou 1.

    Aceita valores booleanos, numericos ou textos True/False.
    """

    # Tratar diretamente colunas booleanas.
    if pd.api.types.is_bool_dtype(serie):
        return serie.astype("int8")

    # Tentar converter os valores para numeros.
    numericos = pd.to_numeric(
        serie,
        errors="coerce"
    )

    # Validar os valores numericos.
    if not numericos.isna().any():

        if not numericos.isin([0, 1]).all():
            raise ValueError(
                "A coluna de alertas possui valores diferentes de 0 e 1."
            )

        return numericos.astype("int8")

    # Tratar representacoes textuais de booleanos.
    textos = (
        serie.astype("string")
        .str.strip()
        .str.lower()
    )

    mapa = {
        "true": 1,
        "false": 0,
        "1": 1,
        "0": 0,
    }

    resultado = textos.map(mapa)

    if resultado.isna().any():
        raise ValueError(
            "A coluna de alertas possui valores nao reconhecidos."
        )

    return resultado.astype("int8")


# ============================================================
# 3. CARREGAMENTO DAS PREVISOES DO GOOGLE COLAB
# ============================================================

def carregar_previsoes_colab() -> pd.DataFrame:
    """Carrega e valida as previsoes originais do Colab."""

    print("\n=== CARREGAMENTO DAS PREVISOES DO COLAB ===")

    if not ARQUIVO_REFERENCIA.is_file():
        raise FileNotFoundError(
            f"Arquivo nao encontrado: {ARQUIVO_REFERENCIA}"
        )

    # Preservar os identificadores como texto.
    df = pd.read_csv(
        ARQUIVO_REFERENCIA,
        dtype={
            "id_transacao": "string"
        }
    )

    # Nomes reais encontrados no CSV original.
    colunas_esperadas = [
        "id_transacao",
        "step",
        "knn_score",
        "knn_alerta",
        "eh_fraude_real",
    ]

    # Verificar se todas as colunas existem.
    ausentes = [
        coluna
        for coluna in colunas_esperadas
        if coluna not in df.columns
    ]

    if ausentes:
        raise ValueError(
            f"Colunas ausentes no CSV do Colab: {ausentes}"
        )

    # Selecionar somente as colunas necessarias.
    df = df[colunas_esperadas].copy()

    # Limpar espacos dos identificadores.
    df["id_transacao"] = (
        df["id_transacao"].str.strip()
    )

    # Validar identificadores.
    if df["id_transacao"].isna().any():
        raise ValueError(
            "O CSV do Colab possui IDs nulos."
        )

    if df["id_transacao"].duplicated().any():
        raise ValueError(
            "O CSV do Colab possui IDs duplicados."
        )

    # Converter step e classe real.
    df["step"] = pd.to_numeric(
        df["step"],
        errors="raise"
    ).astype("int64")

    df["eh_fraude_real"] = pd.to_numeric(
        df["eh_fraude_real"],
        errors="raise"
    ).astype("int8")

    # Converter score para numero.
    df["knn_score"] = pd.to_numeric(
        df["knn_score"],
        errors="raise"
    ).astype("float64")

    # Normalizar os alertas.
    df["knn_alerta"] = normalizar_alertas(
        df["knn_alerta"]
    )

    # Validar os valores da classe real.
    if not df["eh_fraude_real"].isin([0, 1]).all():
        raise ValueError(
            "A classe real possui valores diferentes de 0 e 1."
        )

    # Validar os scores.
    if not np.isfinite(df["knn_score"].to_numpy()).all():
        raise ValueError(
            "O CSV possui scores nulos ou nao finitos."
        )

    if not df["knn_score"].between(0, 1).all():
        raise ValueError(
            "Existem scores fora do intervalo [0, 1]."
        )

    # Conferir a quantidade esperada.
    if len(df) != TOTAL_ESPERADO:
        raise ValueError(
            f"Quantidade divergente no CSV do Colab: "
            f"{len(df):,}; esperado: {TOTAL_ESPERADO:,}."
        )

    # Conferir a quantidade de fraudes.
    total_fraudes = int(
        df["eh_fraude_real"].sum()
    )

    if total_fraudes != FRAUDES_ESPERADAS:
        raise ValueError(
            f"Quantidade de fraudes divergente: "
            f"{total_fraudes:,}; esperado: {FRAUDES_ESPERADAS:,}."
        )

    # Conferir os limites temporais.
    if not df["step"].between(
        STEP_INICIAL,
        STEP_FINAL
    ).all():
        raise ValueError(
            "Existem registros fora do intervalo de teste."
        )

    # Conferir se os alertas respeitam o limiar congelado.
    alertas_esperados = (
        df["knn_score"] >= LIMIAR_CONGELADO
    ).astype("int8")

    if not np.array_equal(
        df["knn_alerta"].to_numpy(),
        alertas_esperados.to_numpy()
    ):
        raise ValueError(
            "Os alertas armazenados no Colab divergem "
            "do limiar congelado."
        )

    print("Arquivo:", ARQUIVO_REFERENCIA)
    print("Registros:", f"{len(df):,}")
    print("IDs unicos:", f"{df['id_transacao'].nunique():,}")
    print("Fraudes:", f"{total_fraudes:,}")
    print("Limiar confirmado:", LIMIAR_CONGELADO)

    return df


# ============================================================
# 4. CARREGAMENTO DO MODELO CONGELADO
# ============================================================

def carregar_modelo():
    """Carrega o classificador e o scaler originais."""

    print("\n=== CARREGAMENTO DO KNN V2 ===")

    artifacts = load_knn_v2_artifacts()

    if not np.isclose(
        artifacts.threshold,
        LIMIAR_CONGELADO,
        rtol=0,
        atol=1e-12
    ):
        raise ValueError(
            "O limiar carregado diverge do limiar congelado."
        )

    print("Modelo carregado:", "KNN V2")
    print("SHA-256:", artifacts.model_sha256)
    print("Features:", len(artifacts.features))
    print("Vizinhos:", artifacts.modelo.n_neighbors)
    print("Limiar:", artifacts.threshold)

    return artifacts


# ============================================================
# 5. EXECUCAO DA INFERENCIA NO DATABRICKS
# ============================================================

def executar_inferencia_local(artifacts) -> pd.DataFrame:
    """
    Consulta a Gold KNN e executa a inferencia no Windows.

    Utiliza os mesmos steps avaliados no Google Colab.
    Não consulta o target durante a inferencia.
    """

    print("\n=== INFERENCIA LOCAL NO DATABRICKS ===")

    resultados = []
    total_processado = 0

    # Consultar os registros em lotes.
    for numero_lote, transacoes in enumerate(
        iter_gold_knn_v2_batches(
            STEP_INICIAL,
            STEP_FINAL,
            batch_size=TAMANHO_LOTE,
        ),
        start=1,
    ):

        if transacoes.empty:
            continue

        # Executar o scoring com o modelo congelado.
        resultado = score_knn_v2_transactions(
            transacoes,
            artifacts,
        )

        # Selecionar somente os campos necessarios.
        previsoes = resultado[
            [
                "id_transacao",
                "step",
                "fraud_score",
                "fraud_alert",
            ]
        ].copy()

        # Padronizar os tipos.
        previsoes["id_transacao"] = (
            previsoes["id_transacao"].astype("string").str.strip()
        )

        previsoes["step"] = (
            previsoes["step"].astype("int64")
        )

        previsoes["fraud_score"] = (
            previsoes["fraud_score"].astype("float64")
        )

        previsoes["fraud_alert"] = (
            previsoes["fraud_alert"].astype("int8")
        )

        # Guardar as previsoes locais.
        resultados.append(previsoes)

        total_processado += len(previsoes)

        print(
            f"Lote {numero_lote}: "
            f"{len(previsoes):,} registros | "
            f"Acumulado: {total_processado:,}",
            flush=True,
        )

    if not resultados:
        raise RuntimeError(
            "O Databricks nao retornou registros para inferencia."
        )

    # Consolidar todos os lotes.
    df_local = pd.concat(
        resultados,
        ignore_index=True
    )

    # Validar quantidade.
    if len(df_local) != TOTAL_ESPERADO:
        raise RuntimeError(
            f"Quantidade divergente na inferencia local: "
            f"{len(df_local):,}; esperado: {TOTAL_ESPERADO:,}."
        )

    # Validar unicidade dos IDs.
    if df_local["id_transacao"].duplicated().any():
        raise RuntimeError(
            "A inferencia local retornou IDs duplicados."
        )

    # Validar os scores.
    if not np.isfinite(
        df_local["fraud_score"].to_numpy()
    ).all():
        raise RuntimeError(
            "A inferencia local retornou scores nao finitos."
        )

    if not df_local["fraud_score"].between(0, 1).all():
        raise RuntimeError(
            "A inferencia local retornou scores fora de [0, 1]."
        )

    print("\nTotal processado:", f"{len(df_local):,}")
    print(
        "IDs unicos:",
        f"{df_local['id_transacao'].nunique():,}"
    )

    return df_local


# ============================================================
# 6. COMPARACAO ENTRE COLAB E VSCODE
# ============================================================

def comparar_previsoes(
    df_colab: pd.DataFrame,
    df_local: pd.DataFrame,
) -> tuple[pd.DataFrame, dict]:
    """Compara scores, alertas, IDs e steps."""

    print("\n=== COMPARACAO COLAB X VSCODE ===")

    # Cruzar os dois ambientes pelo ID da transacao.
    df_comparacao = df_colab.merge(
        df_local,
        on="id_transacao",
        how="outer",
        suffixes=("_colab", "_vscode"),
        indicator=True,
        validate="one_to_one",
    )

    # Verificar cobertura total.
    registros_sem_correspondencia = int(
        (df_comparacao["_merge"] != "both").sum()
    )

    if registros_sem_correspondencia:
        raise RuntimeError(
            f"Existem {registros_sem_correspondencia:,} "
            "registros sem correspondencia entre os ambientes."
        )

    # Comparar os steps.
    steps_iguais = (
        df_comparacao["step_colab"].to_numpy()
        ==
        df_comparacao["step_vscode"].to_numpy()
    )

    # Extrair os scores.
    scores_colab = df_comparacao[
        "knn_score"
    ].to_numpy(dtype=np.float64)

    scores_vscode = df_comparacao[
        "fraud_score"
    ].to_numpy(dtype=np.float64)

    # Calcular as diferenças absolutas.
    diferencas = np.abs(
        scores_colab - scores_vscode
    )

    # Comparar os scores respeitando a tolerancia definida.
    scores_iguais = np.isclose(
        scores_colab,
        scores_vscode,
        rtol=0,
        atol=TOLERANCIA,
    )

    # Comparar os alertas.
    alertas_colab = df_comparacao[
        "knn_alerta"
    ].to_numpy(dtype=np.uint8)

    alertas_vscode = df_comparacao[
        "fraud_alert"
    ].to_numpy(dtype=np.uint8)

    alertas_iguais = (
        alertas_colab == alertas_vscode
    )

    # Comparar as classes reais preservadas no CSV.
    classes_validas = df_comparacao[
        "eh_fraude_real"
    ].isin([0, 1]).all()

    # Conferir o total.
    total = len(df_comparacao)

    quantidade_scores_iguais = int(
        scores_iguais.sum()
    )

    quantidade_alertas_iguais = int(
        alertas_iguais.sum()
    )

    quantidade_steps_iguais = int(
        steps_iguais.sum()
    )

    quantidade_scores_diferentes = int(
        total - quantidade_scores_iguais
    )

    quantidade_alertas_diferentes = int(
        total - quantidade_alertas_iguais
    )

    maior_diferenca = float(
        diferencas.max()
    )

    # Acrescentar informacoes de auditoria.
    df_comparacao["diferenca_score"] = diferencas

    df_comparacao["score_equivalente"] = (
        scores_iguais
    )

    df_comparacao["alerta_equivalente"] = (
        alertas_iguais
    )

    df_comparacao["step_equivalente"] = (
        steps_iguais
    )

    # Remover a coluna tecnica do merge.
    df_comparacao = df_comparacao.drop(
        columns=["_merge"]
    )

    # Montar o resumo da comparacao.
    resumo = {
        "modelo": "KNN V2",
        "origem_referencia": "Google Colab",
        "ambiente_inferencia": "VS Code / Windows",
        "registros_comparados": int(total),
        "ids_sem_correspondencia": registros_sem_correspondencia,
        "scores_equivalentes": quantidade_scores_iguais,
        "scores_diferentes": quantidade_scores_diferentes,
        "alertas_equivalentes": quantidade_alertas_iguais,
        "alertas_diferentes": quantidade_alertas_diferentes,
        "steps_equivalentes": quantidade_steps_iguais,
        "maior_diferenca_score": maior_diferenca,
        "tolerancia_score": TOLERANCIA,
        "limiar_congelado": LIMIAR_CONGELADO,
        "classes_reais_validas": bool(classes_validas),
    }

    # Aprovar somente se todas as comparacoes coincidirem.
    aprovado = (
        total == TOTAL_ESPERADO
        and quantidade_scores_iguais == total
        and quantidade_alertas_iguais == total
        and quantidade_steps_iguais == total
        and registros_sem_correspondencia == 0
        and classes_validas
    )

    resumo["equivalencia_aprovada"] = bool(aprovado)

    return df_comparacao, resumo


# ============================================================
# 7. EXECUCAO PRINCIPAL
# ============================================================

def main() -> None:
    """Executa a auditoria completa de equivalencia."""

    print("=" * 72)
    print("VALIDACAO DE EQUIVALENCIA - KNN V2")
    print("=" * 72)

    # Carregar previsoes originais.
    df_colab = carregar_previsoes_colab()

    # Carregar os artefatos congelados.
    artifacts = carregar_modelo()

    # Executar inferencia local sobre a Gold.
    df_local = executar_inferencia_local(
        artifacts
    )

    # Comparar os resultados.
    df_comparacao, resumo = comparar_previsoes(
        df_colab,
        df_local,
    )

    # Salvar a auditoria individual.
    df_comparacao.to_csv(
        ARQUIVO_RELATORIO,
        index=False,
    )

    # Salvar o resumo em JSON.
    ARQUIVO_RESUMO.write_text(
        json.dumps(
            resumo,
            indent=4,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # Exibir o resultado final.
    print("\n" + "=" * 72)
    print("RESUMO DA EQUIVALENCIA")
    print("=" * 72)

    for nome, valor in resumo.items():

        if isinstance(valor, float):
            print(f"{nome}: {valor:.16f}")

        else:
            print(f"{nome}: {valor}")

    print("\nRelatorio detalhado:", ARQUIVO_RELATORIO)
    print("Resumo JSON:", ARQUIVO_RESUMO)

    # Informar o resultado da auditoria.
    if resumo["equivalencia_aprovada"]:

        print("\n" + "=" * 72)
        print("EQUIVALENCIA APROVADA!")
        print(
            "O VS Code reproduziu as previsoes do Colab "
            "dentro da tolerancia definida."
        )
        print("=" * 72)

    else:

        print("\n" + "=" * 72)
        print("EQUIVALENCIA NAO APROVADA!")
        print(
            "Existem divergencias que precisam ser investigadas."
        )
        print("=" * 72)


# ============================================================
# 8. PONTO DE ENTRADA
# ============================================================

if __name__ == "__main__":
    main()
