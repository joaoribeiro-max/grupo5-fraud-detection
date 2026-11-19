from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import BaseModel, Field

from src.fraud_monitoring_agent.agent import root_agent

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPORT_DIR = PROJECT_ROOT / "exports"
INDEX_FILE = Path(__file__).parent / "static" / "index.html"
APP_NAME = root_agent.name
LOCAL_USER_ID = "local-user"
CSV_FILENAME = re.compile(r"^transacoes_\d{8}T\d{6}Z_[a-f0-9]{8}\.csv$")

session_service = InMemorySessionService()
runner = Runner(app_name=APP_NAME, agent=root_agent, session_service=session_service)
session_locks: dict[str, asyncio.Lock] = {}
app = FastAPI(title="Fraud Monitoring Local", docs_url=None, redoc_url=None)
app.mount("/assets", StaticFiles(directory=Path(__file__).parent / "static"), name="assets")


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=12_000)


def _valid_filename(filename: str) -> bool:
    return bool(CSV_FILENAME.fullmatch(filename))


async def _get_session(session_id: str) -> Any | None:
    return await session_service.get_session(
        app_name=APP_NAME, user_id=LOCAL_USER_ID, session_id=session_id
    )


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    if not INDEX_FILE.is_file():
        raise HTTPException(status_code=500, detail="Interface local não encontrada.")
    return HTMLResponse(INDEX_FILE.read_text(encoding="utf-8-sig"))


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "agent": APP_NAME}


@app.post("/api/sessions")
async def create_session() -> dict[str, str]:
    session = await session_service.create_session(app_name=APP_NAME, user_id=LOCAL_USER_ID)
    return {"session_id": session.id}


@app.get("/api/sessions/{session_id}")
async def check_session(session_id: str) -> dict[str, bool]:
    if await _get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="Conversa local expirada.")
    return {"valid": True}


@app.post("/api/chat")
async def chat(payload: ChatRequest) -> dict[str, str]:
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Digite uma mensagem para o agente.")
    if await _get_session(payload.session_id) is None:
        raise HTTPException(status_code=404, detail="Conversa expirada. Inicie uma nova conversa.")

    lock = session_locks.setdefault(payload.session_id, asyncio.Lock())
    try:
        async with lock:
            final_text = ""
            async for event in runner.run_async(
                user_id=LOCAL_USER_ID,
                session_id=payload.session_id,
                new_message=types.UserContent(parts=[types.Part(text=message)]),
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    final_text = "".join(
                        part.text or ""
                        for part in event.content.parts
                        if getattr(part, "text", None)
                    ).strip()
        if not final_text:
            final_text = "O agente concluiu a solicitação, mas não retornou uma mensagem de texto."
        return {"response": final_text}
    except Exception:
        logger.exception("Falha ao processar mensagem na interface local")
        raise HTTPException(
            status_code=502,
            detail="Não foi possível obter resposta do agente. Consulte o terminal local.",
        ) from None


@app.get("/api/exports")
async def list_exports() -> dict[str, list[dict[str, Any]]]:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    export_root = EXPORT_DIR.resolve()
    files: list[dict[str, Any]] = []
    for candidate in EXPORT_DIR.iterdir():
        if not _valid_filename(candidate.name):
            continue
        try:
            resolved = candidate.resolve(strict=True)
            if resolved.parent != export_root or not resolved.is_file():
                continue
            stat = resolved.stat()
        except OSError:
            continue
        files.append({
            "name": candidate.name,
            "size_bytes": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        })
    files.sort(key=lambda item: item["modified_at"], reverse=True)
    return {"files": files}


@app.get("/api/exports/{filename}")
async def download_export(filename: str) -> FileResponse:
    if not _valid_filename(filename):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
    try:
        export_root = EXPORT_DIR.resolve(strict=True)
        target = (EXPORT_DIR / filename).resolve(strict=True)
    except OSError:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.") from None
    if target.parent != export_root or not target.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
    return FileResponse(path=target, media_type="text/csv; charset=utf-8", filename=filename)


