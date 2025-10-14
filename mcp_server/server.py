# mcp_server/server.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import logging
import re

# lazy import psycopg inside the functions so the module loads even if psycopg
# isn't installed (useful for quick linting). Errors will be clear at runtime.
try:
    import psycopg
except Exception:
    psycopg = None

app = FastAPI(title="MCP Server (tools)")

# IMPORTANT: use a valid, URL-safe DB name (no spaces). Prefer "postgresql://" scheme.
# Replace the default below with your actual DB connection string or set env var DATABASE_URL.
DATABASE_URL ="postgresql://postgres:Plubzay_01@localhost:5432/Deep Insights Copilot"


logger = logging.getLogger("mcp_server")
logging.basicConfig(level=logging.INFO)


class ToolCall(BaseModel):
    tool: str
    params: dict = {}


@app.post("/tools/call")
def call_tool(call: ToolCall):
    """
    Generic tool call entrypoint. Dispatch by tool name.
    """
    tool = (call.tool or "").strip()
    if tool == "kb.search":
        return kb_search(call.params)
    if tool == "kpi.top_root_causes":
        return kpi_top_root_causes(call.params)
    if tool == "sql.query":
        return sql_query(call.params)
    raise HTTPException(status_code=400, detail=f"unknown tool: {call.tool}")


def kb_search(params: dict):
    """
    Simple mocked KB search for quick demo. If you want a real pgvector search,
    replace this with SQL that uses the <-> operator or a full-text search.
    """
    # Basic parameter handling
    q = (params or {}).get("q", "")
    top_k = int((params or {}).get("top_k", 5))

    if not q:
        return []

    # For small demo, fallback to simple ILIKE search against analytics.kb_docs.
    if psycopg is None:
        # psycopg not installed: return a mocked response so the API still runs
        return [{"doc_id": "doc-1", "chunk": "Example doc chunk about refund policy.", "source": "mock"}]

    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT doc_id, chunk_id, chunk_text, source
                    FROM analytics.kb_docs
                    WHERE chunk_text ILIKE %s
                    LIMIT %s
                    """,
                    (f"%{q}%", top_k),
                )
                rows = cur.fetchall()
                results = []
                for r in rows:
                    results.append({
                        "doc_id": r[0],
                        "chunk_id": r[1],
                        "chunk_text": r[2],
                        "source": r[3],
                    })
                return results
    except Exception as e:
        logger.exception("kb_search DB error")
        raise HTTPException(status_code=500, detail=f"kb_search DB error: {e}")


def kpi_top_root_causes(params: dict):
    """
    Simple KPI implementation that aggregates top root causes.
    Expects params: start_date, end_date, top_n (optional)
    """
    start_date = params.get("start_date", "2025-09-01")
    end_date = params.get("end_date", "2025-09-30")
    top_n = int(params.get("top_n", 5))

    if psycopg is None:
        # Return a demo payload if DB driver not available
        return [
            {"root_cause": "Payment Gateway", "product_id": 1, "count_tickets": 124, "pct_open": 0.42},
            {"root_cause": "Session Timeout", "product_id": 2, "count_tickets": 98, "pct_open": 0.10},
        ]

    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT root_cause, product_id, count(*) as count_tickets,
                           sum(case when status <> 'closed' then 1 else 0 end)::float / count(*) as pct_open
                    FROM analytics.fact_tickets
                    WHERE created_at BETWEEN %s::date AND %s::date
                    GROUP BY root_cause, product_id
                    ORDER BY count_tickets DESC
                    LIMIT %s
                    """,
                    (start_date, end_date, top_n),
                )
                rows = cur.fetchall()
                results = [
                    {"root_cause": r[0], "product_id": r[1], "count_tickets": r[2], "pct_open": float(r[3])}
                    for r in rows
                ]
                return results
    except Exception as e:
        logger.exception("kpi_top_root_causes DB error")
        raise HTTPException(status_code=500, detail=f"kpi DB error: {e}")


def sql_query(params: dict):
    """
    Execute read-only SQL (demo). In production *do not* accept arbitrary SQL:
    prefer named templates + parameter validation. This demo allows a single
    'sql' string but blocks writes with a blacklist.
    """
    if psycopg is None:
        raise HTTPException(status_code=500, detail="psycopg driver not installed on server")

    sql = (params or {}).get("sql")
    if not sql:
        raise HTTPException(status_code=400, detail="sql param required")

    # Basic safety: block write DDL/DML keywords
    forbidden = re.compile(r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke)\b", flags=re.I)
    if forbidden.search(sql):
        raise HTTPException(status_code=400, detail="Only read-only queries are allowed")

    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                cols = [c.name for c in cur.description] if cur.description else []
                rows = cur.fetchall()
                return {"columns": cols, "rows": rows}
    except Exception as e:
        logger.exception("sql_query DB error")
        raise HTTPException(status_code=500, detail=f"sql_query DB error: {e}")
