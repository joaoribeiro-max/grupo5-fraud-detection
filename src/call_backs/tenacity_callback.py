from google.adk.models import Gemini
from google.genai import types


# HttpRetryOptions configura o cliente Google Gen AI usado pelo modelo ADK.
# O SDK aplica backoff exponencial com jitter; attempts inclui a chamada inicial.
def criar_modelo_com_retry(modelo: str) -> Gemini:
    return Gemini(
        model=modelo,
        retry_options=types.HttpRetryOptions(
            attempts=8,
            initial_delay=2.0,
            max_delay=60.0,
            exp_base=2.0,
            jitter=1.0,
            http_status_codes=[408, 429, 500, 502, 503, 504],
        ),
    )
