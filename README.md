# Deep Insights Copilot — README

**Status:** Prototype/demo for dBank assessment — includes an API (RAG + LLM), MCP tools server, and a Streamlit demo UI.

This repository contains a working demo of an AI-powered assistant that answers natural-language questions using company data + documentation, and runs safe/parameterized SQL/KPI queries via an MCP tool server.

---

## Prerequisites
- Python 3.10+
- PostgreSQL (local or Docker). Example DB name used in examples: `Deep Insights Copilot` (you can change this)
- Optional: Docker & docker-compose (recommended to avoid polluting system Python)
- Optional: OpenRouter API key if you want to use **Llama 3.3 8B** for real LLM responses.

---

## Important environment variables (.env)
Create a `.env` at project root (there is a template in the repo). Example values:
```
DATABASE_URL=postgresql://postgres:Plubzay_01@localhost:5432/Deep Insights Copilot
MCP_URL=http://localhost:9000
OPENROUTER_API_KEY=or-REPLACE_WITH_KEY
OPENROUTER_MODEL=llama-3.3-8b
PGVECTOR_DIM=1536
STREAMLIT_API_URL=http://localhost:8000/ask
LOG_LEVEL=INFO
```
**Do not commit** `.env` to Git. Add it to `.gitignore` (already included).

---

## Quick start — run locally (no virtualenv)
1. Install dependencies system-wide or `--user`:
```bash
python -m pip install --user -r requirements.txt
python -m pip install --user -r demo_ui/requirements.txt
```
2. Ensure PostgreSQL is running and `DATABASE_URL` points to a valid DB. Create DB if missing:
```bash
psql -U postgres -h localhost -c "CREATE DATABASE deep_insights_copilot;" || true
```
3. (Optional) Load schema & CSV seeds if you have them. Use `psql` and `\copy` to load CSVs into `raw.*` tables (paths must be accessible).
4. In one terminal, start MCP server (tools):
```bash
export DATABASE_URL="postgresql://postgres:Plubzay_01@localhost:5432/deep_insights_copilot"
uvicorn mcp_server.server:app --host 0.0.0.0 --port 9000 --reload
```
5. In another terminal, start the API (RAG + LLM layer):
```bash
export MCP_URL="http://localhost:9000"
export OPENROUTER_API_KEY="or-REPLACE_WITH_KEY"   # optional
uvicorn api.app.main:app --host 0.0.0.0 --port 8000 --reload
```
6. Run Streamlit demo UI:
```bash
streamlit run demo_ui/streamlit_app.py
# default: http://localhost:8501
```

### Notes
- If you don't set `OPENROUTER_API_KEY`, the app will return a deterministic **stub** answer for offline demos.
- If MCP is run in Docker Compose the MCP service name `mcp_server` is reachable by name inside containers; for local runs use `http://localhost:9000`.

---

## Quick start — Docker (recommended)
If you prefer Docker, add an `api` and `mcp_server` service to `docker-compose.yml` and pass `.env` as `env_file`. Example snippet for the `api` service (add to your compose file):
```yaml
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: Plubzay_01
    volumes:
      - pgdata:/var/lib/postgresql/data

  mcp_server:
    build: ./mcp_server
    env_file: ./.env
    command: uvicorn mcp_server.server:app --host 0.0.0.0 --port 9000 --reload
    depends_on:
      - postgres

  api:
    build: ./api
    env_file: ./.env
    command: uvicorn api.app.main:app --host 0.0.0.0 --port 8000 --reload
    depends_on:
      - mcp_server
      - postgres

volumes:
  pgdata:
```
Then run:
```bash
docker-compose up --build
```

---

## Ingest KB (docs → analytics.kb_docs)
If you have markdown docs under `/mnt/data/project_dataset/docs`, run the ingestion script to chunk and insert them into `analytics.kb_docs`:
```bash
export DATABASE_URL="postgresql://postgres:Plubzay_01@localhost:5432/deep_insights_copilot"
export DOC_DIR="/mnt/data/project_dataset/docs"
python mcp_server/ingest_kb.py
```
- The demo ingestion uses a deterministic MD5-based embedding for offline similarity. If you want real embeddings, modify `mcp_server/embeddings.py` to call OpenRouter/OpenAI embeddings (requires keys & network access).

---

## Key HTTP endpoints

### MCP server (tools)
- `POST /tools/call` — main entry for tools. Example request body:
```json
{"tool": "kpi.top_root_causes", "params": {"start_date":"2025-09-01","end_date":"2025-09-30","top_n":5}}
```
- `kb.search`, `kpi.top_root_causes`, `sql.query` are implemented.

### API (RAG + LLM)
- `GET /health` — basic health check.
- `GET /health/llm` — tests LLM by asking to return a deterministic token (requires `OPENROUTER_API_KEY` or `OPENAI_API_KEY`).
- `POST /ask` — main RAG endpoint. Request body:
```json
{"question":"Top 5 root causes of product issues in Sep 2025","params":{"start_date":"2025-09-01","end_date":"2025-09-30","top_n":5}}
```
Response includes:
- `answer` (LLM text, PII redacted),
- `kpi_used` (tool output used),
- `provenance` (kb and tool calls),
- `warnings` (any tool/LLM errors),
- `prompt_used` (truncated prompt),
- `latency_ms`.

### Streamlit demo UI
- Uses the `/ask` endpoint by default (`http://localhost:8000/ask`).
- Has buttons:
  - **Ask** — submit a question (uses RAG flow).
  - **Test LLM** — checks `/ask` with a token request to verify LLM connectivity.
  - **Test DB** — attempts to connect directly to Postgres and run `SELECT * FROM raw.customers LIMIT 20` (reads `DATABASE_URL` from `st.secrets`, query param `db_url`, or environment).

---

## Example curl tests
```bash
# MCP KPI tool
curl -X POST "http://localhost:9000/tools/call" -H "Content-Type: application/json" \
  -d '{"tool":"kpi.top_root_causes","params":{"start_date":"2025-09-01","end_date":"2025-09-30","top_n":3}}' | jq

# API ask (RAG)
curl -X POST "http://localhost:8000/ask" -H "Content-Type: application/json" \
  -d '{"question":"Top 5 root causes of product issues in Sep 2025","params":{"start_date":"2025-09-01","end_date":"2025-09-30","top_n":5}}' | jq

# LLM health
curl http://localhost:8000/health/llm | jq
```

---

## Troubleshooting tips
- `getaddrinfo failed` when API calls MCP → `MCP_URL` is pointing to `http://mcp_server:9000` but you're running API on host; change `MCP_URL` to `http://localhost:9000` (or run both in Docker compose).
- `database "..." does not exist` → create DB or update `DATABASE_URL` to an existing DB.
- If LLM returns `STUB ANSWER` → either LLM key not set or LLM call failed. Check `/health/llm` and ensure `OPENROUTER_API_KEY`/`OPENAI_API_KEY` are in the API process environment and restart the API.
- If `analytics.kb_docs` is empty → run `mcp_server/ingest_kb.py` to populate from `/mnt/data/project_dataset/docs`.
- For vector similarity, ensure `pgvector` is installed and the `embedding` column type matches the embedding dimension (if using real embeddings). The demo code falls back to `ILIKE` when `pgvector` isn't available.

---

## Security and production notes
- This is a prototype. **Do not** expose the `/tools/call` endpoint publicly without auth and rigorous SQL safeguards. In production:
  - Use named, parameterized templates for SQL (do not accept raw SQL from clients).
  - Harden PII handling, masking, and access controls.
  - Use a proper secrets manager for API keys.
  - Add rate-limiting and authentication on all endpoints.

---

## Want help?
Tell me which action you'd like next — I can:
- write a `create_schema.sql` that builds the tables and indexes,
- generate dbt models for the analytics schema,
- convert this to a Docker Compose manifest that runs Postgres, MCP, API, and Streamlit together,
- or run a sample `/ask` here (using stub LLM) and show the JSON response.

