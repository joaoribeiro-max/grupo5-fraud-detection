from google.adk.agents import Agent
from .promptz import PROMPT_FRAUD_AGENT
from ..tools.sql_search_tool import seach_in_sql

root_agent = Agent(
    name="fraud_analysis_agent",
    model="gemini-3.5-flash-lite",
    description="voce e um agente que verifica transaçoes fraudulentas",
    instruction=PROMPT_FRAUD_AGENT,
    tools=[seach_in_sql,]
)