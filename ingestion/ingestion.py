# Minimal ingestion script that creates example tables & sample data and a pgvector column
import os
import psycopg


DATABASE_URL = os.getenv("DATABASE_URL", "postgres://demo:demopw@localhost:5432/deep_insights")


def create_tables():
with psycopg.connect(DATABASE_URL) as conn:
with conn.cursor() as cur:
cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
cur.execute("\nCREATE TABLE IF NOT EXISTS kb_docs (id serial primary key, doc_id text, chunk_text text, embedding vector(1536), source text);\n")
cur.execute("\nCREATE TABLE IF NOT EXISTS fact_tickets (ticket_id serial primary key, customer_id int, product_id int, created_at timestamp, status text, root_cause text);\n")
conn.commit()


if __name__ == '__main__':
create_tables()
print("Created tables")