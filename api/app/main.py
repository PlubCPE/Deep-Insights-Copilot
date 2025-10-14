from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api_router import router

app = FastAPI(title="Deep Insights Copilot - API (RAG + LLM)")

# Enable CORS for demo. Restrict origins in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="")

@app.get("/health")
def health():
    return {"status": "ok"}
