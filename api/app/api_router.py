from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from .rag import generate_answer

router = APIRouter()

class AskRequest(BaseModel):
    question: str
    params: Optional[Dict[str, Any]] = {}

@router.post("/ask")
async def ask(req: AskRequest):
    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="question is required")
    out = await generate_answer(req.question, req.params or {})
    return out
