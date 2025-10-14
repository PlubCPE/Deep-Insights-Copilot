from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import psycopg


app = FastAPI(title="MCP Server (tools)")


DATABASE_URL = os.getenv("DATABASE_URL", "postgres://demo:demopw@localhost:5432/deep_insights")


class ToolCall(BaseModel):
tool: str
params: dict = {}


@app.post("/tools/call")
def call_tool(call: ToolCall):
if call.tool == "kb.search":
return kb_search(call.params)
if call.tool == "kpi.top_root_causes":
return kpi_top_root_causes(call.params)
if call.tool == "sql.query":
return sql_query(call.params)
raise HTTPException(status_code=400, detail="unknown tool")




def kb_search(params):
# Mocked: return example chunks
return [{"doc_id": "doc-1", "chunk": "Example doc chunk about refund policy."}]




def kpi_top_root_causes(params):
# Example aggregation (mock)
return [
{"root_cause": "Payment Gateway", "count": 124, "pct_open": 0.42},
{"root_cause": "Session Timeout", "count": 98, "pct_open": 0.10},
]




def sql_query(params):
# Only allow named templates in production. This is a demo that runs provided SQL read-only.
sql = params.get("sql")
if not sql:
raise HTTPException(status_code=400, detail="sql param required")
with psycopg.connect(DATABASE_URL) as conn:
with conn.cursor() as cur:
cur.execute(sql)
cols = [c.name for c in cur.description] if cur.description else []
rows = cur.fetchall()
return {"columns": cols, "rows": rows}