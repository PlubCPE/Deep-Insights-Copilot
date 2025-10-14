# Deep-Insights-Copilot

5-Days dData Deep Lab : “Deep Insights Copilot”

Scenario
dBank is Largest Virtual Bank in Thailand, services 40 million customers, receives ~50k support tickets/month
and internal Operation support team need “Deep Insights Copilot” system:
1. answer natural-language questions grounded in company data/docs, and
2. run safe, parameterized actions (SQL, KPI queries) via MCP tools.
Business Requirements Spec
● Goal: Reduce time for Operation support team by 80% and deflect 25% “repeat-question” tickets.
● Must answer (examples):
● “Top 5 root causes of product issues in the previous month by category with % open ticket.”
● “Did ticket volume spike after Virtual Bank App v1.2 release? Show anomaly window and
related product, eg. Digital Saving, Digital Lending”
● “Write the SQL for churned customers in the last 30, 90 days. (Not log in to the Virtual Bank
App”

● AI Guardrails: read-only DB access; PII (Sensitive Data) must be masked; every tool call must be
parameterized & logged.
What to build (minimum)
● Data layer: ingest & model three sources (customer, tickets, login access, products) into Postgres (star
schema or 3NF) + dbt transformations + data tests.
● Retrieval layer: chunk & embed docs (knowledge base markdown/PDFs) into a vector store (pgvector
is fine).
● LLM layer (RAG): FastAPI endpoint `/ask` that answers questions from users by retrieving context +
MCP tool calls for SQL/KPIs.
● MCP server exposing at least 3 tools:
* `sql.query` (read-only SQL with templated parameters)
* `kb.search` (semantic search over the doc store)
* `kpi.top_root_causes` (aggregation helper)
Tools must be discoverable and invocable per MCP’s tools/list and tools/call semantics.
● Thin UI (CLI or tiny web page) for demoing questions & tool invocations.

© dData. Proprietary and Confidential.

dD

● Deployment-grade (DevOps Engineer track): github, containerization, CI, observability,
resource/secret hygiene, rate limits, circuit breakers, cost & safety controls.

MCP is an open standard for connecting AI apps to tools/data with a consistent “list tools / call tools /
resources / prompts” model; candidates should follow the current spec concepts.
Data and Model Requirements
● Customer and Customer Access login
● Customer Open Tickets / Issues
● Customer Product Holding
● Product knowledge base/ (5–10 short markdown files with known issues, condition, policies, release
notes)
