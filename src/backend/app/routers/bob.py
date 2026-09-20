"""Bob router — thin wrapper over the shared IBM Bob service."""
from __future__ import annotations
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..config import get_settings
from ..db import get_db
from ..models import ChatMessage
from ..response_models import BobAnswerResponse, BobHistoryResponse, BobStatusResponse
from ..services import bob as bob_svc
from ..services import bob_agent, llm
router = APIRouter(prefix="/api", tags=["bob"])
class BobBody(BaseModel): message: str
@router.get("/bob/status", response_model=BobStatusResponse)
def status():
    settings = get_settings()
    return {"provider": llm.provider(), "configured": bool(settings.bob_api_key), "cli_available": bob_agent._cli_path() is not None, "mcp": "PortPulse AI", "tools": 12, "fallback": "deterministic engine-grounded"}
@router.get("/bob", response_model=BobHistoryResponse)
def history(db: Session = Depends(get_db)):
    rows = db.execute(select(ChatMessage).order_by(ChatMessage.id.desc()).limit(50)).scalars().all()
    return {"messages": [{"role": r.role, "content": r.content, "meta": r.meta, "created_at": r.created_at.isoformat()} for r in reversed(rows)]}
@router.post("/bob", response_model=BobAnswerResponse)
def ask(body: BobBody, db: Session = Depends(get_db)):
    out = bob_svc.respond(db, body.message, persist=True)
    return {k: out[k] for k in ("content", "actions", "mode", "provider", "intent", "grounded")}
