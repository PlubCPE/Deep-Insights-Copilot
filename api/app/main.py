from fastapi import FastAPI
from .api_router import router


app = FastAPI(title="Deep Insights Copilot - API")
app.include_router(router)


@app.get("/health")
def health():
return {"status": "ok"}