$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "Ambiente virtual .venv não encontrado. Instale as dependências de requirements.txt."
}
Set-Location -LiteralPath $projectRoot
& $python -m uvicorn src.local_frontend.app:app --host 127.0.0.1 --port 8001
