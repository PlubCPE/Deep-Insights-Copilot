# import re
# from typing import Dict, Any, List
# from .mcp_client import call_tool
# from .llm_client import generate_completion
# import time
# import os

# # Simple intent keywords for deciding to call KPI/SQL tools
# KPI_KEYWORDS = ["top", "kpi", "root cause", "root causes", "churn", "rate", "average", "avg", "count", "how many", "which product"]

# PROMPT_TEMPLATE = """
# You are a domain-aware assistant for dBank. Answer the user's question using ONLY the provided context and tool outputs.
# If you cannot answer from the context, say you don't know and suggest the KB documents to review.
# Provide a concise answer, then include a 'SOURCES' section listing document ids or tool names used.
# ------
# CONTEXT:
# {context}
# ------
# TOOL OUTPUTS:
# {kpi_output}
# ------
# QUESTION:
# {question}
# ------
# INSTRUCTIONS:
# - Use the context first. If numeric facts are needed, prefer KPI/tool results.
# - Always include a short 'SOURCES' list.
# - Do not invent emails, phone numbers, or any PII.
# - If PII appears, redact it in the answer.
# """

# def needs_kpi(question: str) -> bool:
#     q = question.lower()
#     return any(k in q for k in KPI_KEYWORDS)

# async def generate_answer(question: str, params: Dict[str, Any] = {}) -> Dict[str, Any]:
#     """
#     High-level RAG flow:
#     1) Call MCP 'kb.search' to retrieve top-k docs
#     2) If question triggers KPI/SQL, call MCP 'kpi.top_root_causes' or 'sql.query' as appropriate
#     3) Build prompt with context and tool outputs, call LLM, and return answer with provenance
#     """
#     start = time.time()
#     # 1) KB search
#     try:
#         kb_resp = await call_tool("kb.search", {"q": question, "top_k": params.get("top_k", 5)})
#     except Exception as e:
#         kb_resp = []
#     # Normalize kb chunks into text context
#     context_chunks: List[str] = []
#     if isinstance(kb_resp, list):
#         for c in kb_resp:
#             # support different field names
#             text = c.get("chunk") or c.get("chunk_text") or c.get("text") or str(c)
#             src = c.get("doc_id") or c.get("source") or c.get("docid") or ""
#             context_chunks.append(f"[{src}] {text}")
#     elif isinstance(kb_resp, dict):
#         # some MCP implementations return {"results": [...]}
#         items = kb_resp.get("results") or []
#         for c in items:
#             text = c.get("chunk") or c.get("chunk_text") or str(c)
#             src = c.get("doc_id") or c.get("source") or ""
#             context_chunks.append(f"[{src}] {text}")

#     context = "\n\n".join(context_chunks[:6]) if context_chunks else "No relevant documents retrieved."

#     # 2) KPI / SQL tool calls (if needed)
#     kpi_output = ""
#     sql_exec = None
#     tool_calls = []
#     if needs_kpi(question):
#         # For this demo, call the generic kpi.top_root_causes tool; params can include dates and product filters
#         kpi_params = {
#             "start_date": params.get("start_date", os.getenv('DEFAULT_START_DATE', "2025-09-01")),
#             "end_date": params.get("end_date", os.getenv('DEFAULT_END_DATE', "2025-09-30")),
#             "product_ids": params.get("product_ids"),
#             "top_n": params.get("top_n", 5)
#         }
#         try:
#             kpi_resp = await call_tool("kpi.top_root_causes", kpi_params)
#             kpi_output = str(kpi_resp)
#             tool_calls.append({"tool": "kpi.top_root_causes", "params": kpi_params, "response": kpi_resp})
#         except Exception as e:
#             kpi_output = f"[kpi tool error: {str(e)}]"
#     # 3) Build prompt and call LLM
#     prompt = PROMPT_TEMPLATE.format(context=context, kpi_output=kpi_output, question=question)
#     llm_answer = await generate_completion(prompt, max_tokens=512, temperature=0.0)
#     elapsed_ms = int((time.time() - start) * 1000)
#     # 4) Redact possible PII (simple heuristics) - email and phone
#     redacted_answer = redact_pii(llm_answer)
#     # Prepare provenance
#     provenance = {
#         "kb": kb_resp,
#         "tool_calls": tool_calls,
#     }
#     return {
#         "answer": redacted_answer,
#         "provenance": provenance,
#         "prompt_used": prompt[:4000],  # trimmed
#         "latency_ms": elapsed_ms
#     }

# # Simple PII redaction using regex: remove emails and phone-like patterns
# def redact_pii(text: str) -> str:
#     # redact emails
#     text = re.sub(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "[REDACTED_EMAIL]", text)
#     # redact phone-like (Thai-ish) numbers: series of 7-12 digits possibly with spaces or dashes
#     text = re.sub(r"(?:\+?\d[\d\-\s]{6,}\d)", "[REDACTED_PHONE]", text)
#     return text



# api/app/rag.py
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

# Prompt template: clear, concise, and instruct LLM to use only provided context/tool outputs.
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

# Simple heuristic to decide if KPI tool should be invoked
def needs_kpi(question: str) -> bool:
    q = (question or "").lower()
    return any(k in q for k in KPI_KEYWORDS)

# simple PII redaction
def redact_pii(text: str) -> str:
    text = re.sub(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "[REDACTED_EMAIL]", text)
    text = re.sub(r"(?:\+?\d[\d\-\s]{6,}\d)", "[REDACTED_PHONE]", text)
    return text

# utility to format KPI/tool outputs as a small table or JSON for the prompt
def format_kpi_for_prompt(kpi_resp: Any, mocked: bool = False) -> str:
    if not kpi_resp:
        return "No KPI/tool outputs available."
    try:
        # Prefer to format a list-of-dicts into a markdown-like table or JSON
        if isinstance(kpi_resp, list):
            # try pretty table for first 6 rows
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
        # fallback to JSON string
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

    # 1) KB search (best-effort)
    try:
        kb_resp = await call_tool("kb.search", {"q": question, "top_k": params.get("top_k", 5)})
        provenance["kb"] = kb_resp
        # build simple context from top chunks (limit characters to avoid huge prompts)
        if isinstance(kb_resp, list) and kb_resp:
            chunks = []
            for c in kb_resp[:6]:
                # support various field names
                text = c.get("chunk") or c.get("chunk_text") or c.get("text") or str(c)
                src = c.get("doc_id") or c.get("source") or c.get("docid") or ""
                chunks.append(f"[{src}] {text}")
            context_text = "\n\n".join(chunks)
    except Exception as e:
        provenance["errors"].append({"step": "kb.search", "error": str(e)})
        # keep context_text as default message

    # 2) KPI / SQL tool (if heuristics say so)
    kpi_output = None
    kpi_mocked = False
    if needs_kpi(question):
        kpi_params = {
            "start_date": params.get("start_date"),
            "end_date": params.get("end_date"),
            "product_ids": params.get("product_ids"),
            "top_n": params.get("top_n", 5)
        }
        # Try kpi.top_root_causes first
        try:
            kpi_resp = await call_tool("kpi.top_root_causes", kpi_params)
            provenance["tools"].append({"tool": "kpi.top_root_causes", "params": kpi_params, "response": kpi_resp})
            kpi_output = kpi_resp
        except Exception as e:
            provenance["errors"].append({"step": "kpi.top_root_causes", "error": str(e)})
            # fallback: try generic sql.query with a named template (if available)
            try:
                sql_template_name = params.get("sql_template", "templates/logins_by_app_version.sql")
                # Example: call sql.query with a rendered SQL or template name depending on your MCP implementation
                # Here we assume a safe sql.query that accepts {"sql": "..."} for demo
                # If your MCP supports named templates, call the appropriate tool format
                sql_params = params.copy()
                resp = await call_tool("sql.query", {"sql": params.get("fallback_sql", "")}) if params.get("fallback_sql") else None
                if resp:
                    provenance["tools"].append({"tool": "sql.query", "params": {"sql": params.get("fallback_sql")}, "response": resp})
                    kpi_output = resp
            except Exception as e2:
                provenance["errors"].append({"step": "sql.query_fallback", "error": str(e2)})
                # Final fallback: mocked KPI so LLM can show something useful in demo
                kpi_output = [
                    {"root_cause": "(MOCK) Payment Gateway", "count_tickets": 120, "pct_open": 0.42},
                    {"root_cause": "(MOCK) UI Bug", "count_tickets": 80, "pct_open": 0.10},
                ]
                kpi_mocked = True
                provenance["tools"].append({"tool": "kpi.mocked", "response": kpi_output})

    # 3) Build prompt
    kpi_for_prompt = format_kpi_for_prompt(kpi_output, mocked=kpi_mocked) if kpi_output is not None else "No KPI/tool outputs available."
    prompt = PROMPT_TEMPLATE.format(context=context_text, kpi_table=kpi_for_prompt, question=question)

    # 4) Call LLM (OpenRouter/OpenAI) - keep any exception from killing the API
    try:
        llm_resp = await generate_completion(prompt, max_tokens=512, temperature=0.0)
    except Exception as e:
        provenance["errors"].append({"step": "llm_call", "error": str(e)})
        # return a helpful error to user instead of stub
        elapsed_ms = int((time.time() - start) * 1000)
        return {
            "answer": None,
            "provenance": provenance,
            "error": f"LLM call failed: {str(e)}",
            "latency_ms": elapsed_ms
        }

    # 5) Redact PII and assemble final result
    answer = redact_pii(llm_resp)
    elapsed_ms = int((time.time() - start) * 1000)

    result = {
        "answer": answer,
        "provenance": provenance,
        "kpi_used": kpi_output,
        "prompt_used": prompt[:4000],
        "latency_ms": elapsed_ms,
        "warnings": provenance.get("errors", [])  # show any warnings to UI
    }
    return result
