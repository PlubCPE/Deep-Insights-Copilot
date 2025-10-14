from fastapi import APIRouter, Body
from pydantic import BaseModel
from .mcp_client import call_tool


router = APIRouter()


class AskRequest(BaseModel):
question: str
params: dict = {}


@router.post("/ask")
async def ask(req: AskRequest):
# 1) semantic search via MCP
kb = await call_tool("kb.search", {"q": req.question, "top_k": 4})


# 2) decide if KPI needed (simple heuristic)
kpi_resp = None
if any(k in req.question.lower() for k in ["top", "kpi", "root cause", "churn"]):
kpi_resp = await call_tool("kpi.top_root_causes", {"start_date": "2025-09-01", "end_date": "2025-09-30", "top_n": 5})


# 3) stubbed LLM call (replace with real LLM call)
answer = f"Answer (mock) for: {req.question} -- include {len(kb or [])} kb chunks"


return {
"answer": answer,
"kb": kb,
"kpi": kpi_resp,
}