FROM python:3.11-slim
WORKDIR /app
COPY server.py ./
RUN pip install fastapi uvicorn psycopg[binary] pydantic pgvector
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "9000"]