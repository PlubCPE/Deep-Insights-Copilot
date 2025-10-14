from sqlalchemy import create_engine, text
import pandas as pd
from openai import OpenAI
import os

# Example connection string: postgresql://user:password@host:port/dbname
DATABASE_URL = "postgresql://postgres:Plubzay_01@localhost:5432/Deep Insights Copilot"

engine = create_engine(DATABASE_URL)

# def check_sqlalchemy_connection():
#     try:
#         with engine.connect() as conn:
#             result = conn.execute(text("SELECT NOW()"))
#             print("✅ Connected successfully!")
#             print("🕓 Database time:", result.scalar())
#     except Exception as e:
#         print("❌ Connection failed:", e)

# check_sqlalchemy_connection()

# def test_select_query():
#     try:
#         with engine.connect() as conn:
#             print("✅ Connected successfully!")

#             # 🧠 Example 1: simple test
#             result = conn.execute(text("SELECT 1 AS test;"))
#             print("SELECT 1 →", result.scalar())

#             # 🧠 Example 2: test reading from an existing table
#             result = conn.execute(text("SELECT * FROM customers LIMIT 5;"))
#             rows = result.fetchall()

#             print("\n📊 Sample data from 'customers':")
#             for row in rows:
#                 print(row)

#     except Exception as e:
#         print("❌ Query failed:", e)

# test_select_query()

# table_name = "fact_tickets"
# df = pd.read_sql(f"SELECT * FROM analytics.{table_name} LIMIT 10;", engine)

# print(f"📊 First 10 rows from analytics.{table_name}:")
# print(df)


from openai import OpenAI

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key= "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"
)

completion = client.chat.completions.create(
  extra_headers={
    "HTTP-Referer": "<YOUR_SITE_URL>", # Optional. Site URL for rankings on openrouter.ai.
    "X-Title": "<YOUR_SITE_NAME>", # Optional. Site title for rankings on openrouter.ai.
  },
  extra_body={},
  model="meta-llama/llama-3.3-8b-instruct:free",
  messages=[
    {
      "role": "user",
      "content": "What is the meaning of life?"
    }
  ]
)
print(completion.choices[0].message.content)