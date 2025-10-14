import os, psycopg
from pathlib import Path

DATABASE_URL = os.getenv("DATABASE_URL", "postgres://demo:demopw@localhost:5432/deep_insights")
DOC_DIR = "/mnt/data/project_dataset/docs"

def embed_text(text):
    # TODO: call OpenAI embeddings or sentence-transformers; for now use a short deterministic vector stub
    # Example stub: convert first 1536 chars to small floats (not useful for real similarity, but demoable)
    import hashlib, struct
    h = hashlib.md5(text.encode()).digest()
    # simple fixed-dim stub
    return [float(b)/255.0 for b in h] * (1536 // len(h))

def ingest_docs():
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            for p in Path(DOC_DIR).glob("*.md"):
                text = p.read_text(encoding="utf-8")
                chunks = [text[i:i+800] for i in range(0, len(text), 800)]
                for idx, chunk in enumerate(chunks):
                    emb = embed_text(chunk)  # list of floats (1536)
                    # store as array literal for vector column if pgvector installed; else skip embedding column
                    cur.execute(
                      "INSERT INTO analytics.kb_docs (doc_id, chunk_id, chunk_text, embedding, source) VALUES (%s, %s, %s, %s, %s)",
                      (p.stem, idx, chunk, emb, 'internal_policy')
                    )
            conn.commit()

if __name__ == "__main__":
    ingest_docs()
