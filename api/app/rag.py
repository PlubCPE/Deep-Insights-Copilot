import re
import time
import json
import os
from typing import Dict, Any, List, Optional
from .mcp_client import call_tool
from .llm_client import generate_completion

# Keywords that indicate KPI/SQL may be required
KPI_KEYWORDS = [
    "top", "kpi", "root cause", "root causes", "churn", "rate", "average", "avg",
    "count", "how many", "which product", "percent", "percentage", "trend"
]

PROMPT_TEMPLATE = """
You are a domain-aware assistant for dBank. Answer using ONLY the provided CONTEXT and TOOL OUTPUTS.
If the requested fact is not present in the CONTEXT or TOOL OUTPUTS, say you don't know and refer to the KB docs.
Be concise (2-6 sentences) and at the end include a SOURCES section listing document ids or tool names used.

CONTEXT:
{context}

TOOL OUTPUTS (structured):
{kpi_table}

QUESTION:
{question}

INSTRUCTIONS:
- Use concrete numbers from TOOL OUTPUTS when available.
- If TOOL OUTPUTS are estimates or mocked, clearly label them as MOCKED.
- Do NOT invent PII; redact any PII in answers.
- Provide a final short answer and then a SOURCES list.
"""

def needs_kpi(question: str) -> bool:
    q = (question or "").lower()
    return any(k in q for k in KPI_KEYWORDS)

def redact_pii(text: str) -> str:
    text = re.sub(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "[REDACTED_EMAIL]", text)
    text = re.sub(r"(?:\+?\d[\d\-\s]{6,}\d)", "[REDACTED_PHONE]", text)
    return text

def format_kpi_for_prompt(kpi_resp: Any, mocked: bool = False) -> str:
    if not kpi_resp:
        return "No KPI/tool outputs available."
    try:
        if isinstance(kpi_resp, list):
            keys = []
            for item in kpi_resp:
                if isinstance(item, dict):
                    keys = list(item.keys())
                    break
            if keys:
                lines = ["| " + " | ".join(keys) + " |", "| " + " | ".join(["---"] * len(keys)) + " |"]
                for r in kpi_resp[:10]:
                    lines.append("| " + " | ".join(str(r.get(k, "")) for k in keys) + " |")
                if mocked:
                    lines.append("\n(MOCKED KPI OUTPUTS)\n")
                return "\n".join(lines)
        s = json.dumps(kpi_resp, default=str, indent=2)
        if mocked:
            s = "(MOCKED)\n" + s
        return s
    except Exception:
        return str(kpi_resp)

async def generate_answer(question: str, params: Dict[str, Any] = {}) -> Dict[str, Any]:
    start = time.time()
    provenance = {"kb": None, "tools": [], "errors": []}
    context_text = "No relevant documents retrieved."

    # KB search
    try:
        kb_resp = await call_tool("kb.search", {"q": question, "top_k": params.get("top_k", 5)})
        provenance["kb"] = kb_resp
        if isinstance(kb_resp, list) and kb_resp:
            chunks = []
            for c in kb_resp[:6]:
                text = c.get("chunk") or c.get("chunk_text") or c.get("text") or str(c)
                src = c.get("doc_id") or c.get("source") or c.get("docid") or ""
                chunks.append(f"[{src}] {text}")
            context_text = "\n\n".join(chunks)
    except Exception as e:
        provenance["errors"].append({"step": "kb.search", "error": str(e)})

    # KPI / SQL tool
    kpi_output = None
    kpi_mocked = False
    if needs_kpi(question):
        kpi_params = {
            "start_date": params.get("start_date"),
            "end_date": params.get("end_date"),
            "product_ids": params.get("product_ids"),
            "top_n": params.get("top_n", 5)
        }
        try:
            kpi_resp = await call_tool("kpi.top_root_causes", kpi_params)
            provenance["tools"].append({"tool": "kpi.top_root_causes", "params": kpi_params, "response": kpi_resp})
            kpi_output = kpi_resp
        except Exception as e:
            provenance["errors"].append({"step": "kpi.top_root_causes", "error": str(e)})
            # try fallback sql.query if provided
            try:
                if params.get("fallback_sql"):
                    resp = await call_tool("sql.query", {"sql": params.get("fallback_sql")})
                    provenance["tools"].append({"tool": "sql.query", "params": {"sql": params.get("fallback_sql")}, "response": resp})
                    kpi_output = resp
            except Exception as e2:
                provenance["errors"].append({"step": "sql.query_fallback", "error": str(e2)})
                # final fallback mocked KPI for demo
                kpi_output = [
                    {"root_cause": "(MOCK) Payment Gateway", "count_tickets": 120, "pct_open": 0.42},
                    {"root_cause": "(MOCK) UI Bug", "count_tickets": 80, "pct_open": 0.10},
                ]
                kpi_mocked = True
                provenance["tools"].append({"tool": "kpi.mocked", "response": kpi_output})

    # Build prompt and call LLM
    kpi_for_prompt = format_kpi_for_prompt(kpi_output, mocked=kpi_mocked) if kpi_output is not None else "No KPI/tool outputs available."
    prompt = PROMPT_TEMPLATE.format(context=context_text, kpi_table=kpi_for_prompt, question=question)

    try:
        llm_resp = await generate_completion(prompt, max_tokens=512, temperature=0.0)
    except Exception as e:
        provenance["errors"].append({"step": "llm_call", "error": str(e)})
        elapsed_ms = int((time.time() - start) * 1000)
        return {
            "answer": None,
            "provenance": provenance,
            "error": f"LLM call failed: {str(e)}",
            "latency_ms": elapsed_ms
        }

    answer = redact_pii(llm_resp)
    elapsed_ms = int((time.time() - start) * 1000)

    result = {
        "answer": answer,
        "provenance": provenance,
        "kpi_used": kpi_output,
        "prompt_used": prompt[:4000],
        "latency_ms": elapsed_ms,
        "warnings": provenance.get("errors", [])
    }
    return result
