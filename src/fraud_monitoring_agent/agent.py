from google.adk.agents import Agent

from .promptz import PROMPT_FRAUD_AGENT
from ..call_backs.tenacity_callback import criar_modelo_com_retry
from ..tools.csv_export_tool import exportar_transacoes_csv
from ..tools.sql_search_tool import consultar_transacoes

root_agent = Agent(
    name="fraud_analysis_agent",
    model=criar_modelo_com_retry("gemini-3.5-flash-lite"),
    description="Agente de apoio à análise experimental de transações e fraudes.",
    instruction=PROMPT_FRAUD_AGENT,
    tools=[consultar_transacoes, exportar_transacoes_csv],
)
