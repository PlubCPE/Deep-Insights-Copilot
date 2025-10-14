
from sqlalchemy import create_engine, text

engine = create_engine("postgres://postgres:Plubzay_01@localhost:5432/Deep Insights Copilot")

try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("✅ Connected to DB:", result.scalar())
except Exception as e:
    print("❌ Database connection failed:", e)