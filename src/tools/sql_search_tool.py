import os 
import re
import json
from databricks import sql
from dotenv import load_dotenv

load_dotenv()

def sql_connection():
    """Abre conecçao com o SQL Warehouse do Databricks."""
    return sql.connect(
        server_hostname=os.getenv("DATABRICKS_SERVER_HOSTNAME"),
        http_path=os.getenv("DATABRICKS_HTTP_PATH"),
        access_token=os.getenv("DATABRICKS_TOKEN")
    )

def seach_in_sql(sql_query:str) -> str:
    """
    Executa uma consulta SQL (dialeto Databricks / Spark SQL) nas tabelas tratadas da Prefeitura
    para responder perguntas sobre transações, secretarias, fornecedores, valores e fraudes.

    SCHEMA DA TABELA NO DATABRICKS:
    Catálogo/Tabela: workspace.bronze.cidade_inteligente
    Colunas:
   SCHEMA DA TABELA NO DATABRICKS:
    Catálogo/Tabela: workspace.bronze.cidade_inteligente
    Colunas:
    - `step` (INT): Unidade de tempo da simulação em horas (1 step = 1 hora).
    - `type` (STRING): Tipo da transação financeira (ex: 'PAYMENT', 'TRANSFER', 'CASH_OUT', 'DEBIT', 'CASH_IN').
    - `amount` (DOUBLE): Valor financeiro da transação.
    - `nameOrig` (STRING): Identificador único do cliente/conta que iniciou a transação.
    - `oldbalanceOrg` (DOUBLE): Saldo inicial da conta de origem antes da transação.
    - `newbalanceOrig` (DOUBLE): Novo saldo da conta de origem após a transação.
    - `nameDest` (STRING): Identificador único do cliente/conta destinatária da transação.
    - `oldbalanceDest` (DOUBLE): Saldo inicial da conta de destino antes da transação (observação: sem informação para contas de comerciantes iniciadas com 'M').
    - `newbalanceDest` (DOUBLE): Novo saldo da conta de destino após a transação (observação: sem informação para contas de comerciantes iniciadas com 'M').
    - `isFraud` (INT): Indicador real de fraude (1 = Fraude, 0 = Normal).
    - `isFlaggedFraud` (INT): Indicador de tentativa ilegal sinalizada pelo sistema de regras (ex: transferências acima de 200.000 em uma única operação; 1 = Sinalizada, 0 = Não sinalizada).

    REGRAS OBRIGATÓRIAS PARA GERAR A QUERY:
    1. Use APENAS comandos `SELECT` ou `WITH`.
    2. Use sintaxe Databricks SQL (ex: use `ILIKE '%termo%'` para textos e `LIMIT 20` para listagens).
    3. Sempre referencie o nome completo da tabela no `FROM`.

    Args:
        sql_query: Consulta SQL válida em dialeto Databricks SQL.

    Returns:
        JSON contendo as linhas retornadas ou o erro técnico do Databricks para autocorreção.
    """

    sql_limpa = sql_query.split()
    sql_upper = sql_query.upper()

    if not (sql_query.startswith("SELECT") or sql_upper.startswith("WITH")):
        return json.dumps({
            "status":"erro_segurança",
            "mensagem":"Operaçao negada. apenas consultas sao permitidas"
        })

    comandos_proibidos = r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|TRUNCATE|MERGE|CREATE|GRANT|REVOKE)\b"
    if re.search(comandos_proibidos,sql_query):
        return json.dumps({
            "status":"erro_segurança",
            "mansagem": "comando nao autorizado detectado na query"
        })

    if ";" in sql_limpa[:-1]:
        return json.dumps({
            "status":"erro_segurança",
            "mensagem": "Multiplas instruçoes SQL nao sao permitidas"
        })

    try:
        with sql_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql_query)

                colunas = [desc[0] for desc in cursor.description]
                linhas = cursor.fetchmany(50)

                if not linhas:
                    return json.dumps({
                        "status":"sucesso",
                        "dados":[],
                        "aviso":"Consulta executada com sucesso, mas nenhum registro foi encontrado "
                    })
                dados_formatados = [dict(zip(colunas, linha)) for linha in linhas]

                return json.dumps({
                    "status":"sucesso",
                    "total_retornado": len(dados_formatados),
                    "dados": dados_formatados
                }, default=str, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "status":"erro_databricks",
            "mensagem":f"Erro ao executar query no Databricks: {str(e)}, revise a sixtaxe ou nome de colunas e tente novamente"
        }, ensure_ascii=False) 

