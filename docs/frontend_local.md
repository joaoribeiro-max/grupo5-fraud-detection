# Interface local do agente de fraudes

## Iniciar no Windows

Na pasta raiz do projeto, execute no PowerShell:

```powershell
.\run_local_frontend.ps1
```

Abra <http://127.0.0.1:8001>. O servidor é vinculado à máquina local e usa o ambiente virtual `.venv`.

A conversa usa o Runner do ADK. As sessões ficam em memória e são apagadas ao encerrar o servidor. Os CSVs ficam em `exports/`; a aba **Arquivos CSV** lista as exportações e permite baixá-las pelo navegador.

O arquivo `.env` deve conter as credenciais necessárias para Gemini e Databricks. Se ainda não tiver instalado as dependências, instale `requirements.txt` no ambiente virtual do projeto.
