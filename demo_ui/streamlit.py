import streamlit as st
import requests
import pandas as pd
import os
from datetime import date

st.set_page_config(page_title="Deep Insights Copilot — Streamlit Demo", layout="wide")

API_URL = "http://localhost:8000/ask"
TIMEOUT = 30

st.title("Deep Insights Copilot — Streamlit Demo UI")
st.markdown("Use this UI to ask questions, test LLM connectivity, and test database connectivity.")

with st.sidebar:
    st.header("Demo Controls")
    start_date = st.date_input("Start date", value=date(2025, 9, 1))
    end_date = st.date_input("End date", value=date(2025, 9, 30))
    top_n = st.number_input("Top N (KPIs)", min_value=1, max_value=50, value=5)
    product_id = st.text_input("Product ID filter (optional)")
    show_raw = st.checkbox("Show raw JSON", value=False)
    st.markdown("---")
    st.markdown("Example questions:\n- `Top 5 root causes of product issues in Sep 2025`\n- `What does the refunds policy say about chargebacks?`")

query = st.text_area("Question", height=120, value="Top 5 root causes of product issues in Sep 2025")

col1, col2 = st.columns(2)
with col1:
    if st.button("Ask"):
        payload = {
            "question": query,
            "params": {
                "start_date": str(start_date),
                "end_date": str(end_date),
                "top_n": int(top_n),
                "product_id": product_id or None,
            }
        }
        with st.spinner("Calling API..."):
            try:
                resp = requests.post(API_URL, json=payload, timeout=TIMEOUT)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                st.error(f"Request failed: {e}")
                st.stop()
        # Display results
        st.subheader("Answer")
        st.markdown(data.get("answer", "No answer returned."))
        # Show KPI used
        if data.get("kpi_used"):
            st.subheader("KPI / Tool Output Used")
            try:
                kpi_df = pd.DataFrame(data["kpi_used"])
                st.dataframe(kpi_df)
            except Exception:
                st.json(data["kpi_used"])
        # Show warnings
        if data.get("warnings"):
            st.subheader("Warnings / Tool Errors")
            for w in data["warnings"]:
                st.warning(f'{w.get("step")}: {w.get("error")}')
        if data.get("provenance"):
            st.subheader("Provenance / Tool Calls")
            st.json(data["provenance"])
        if data.get("prompt_used"):
            with st.expander("Prompt used (truncated)"):
                st.code(data["prompt_used"][:3000])
        if show_raw:
            st.subheader("Raw response JSON")
            st.json(data)

with col2:
    st.subheader("LLM Connectivity Test")
    st.markdown("Press the button below to run a quick connectivity test. This sends a short, deterministic instruction to the LLM via the `/ask` endpoint and checks for a specific token in the response.")
    if st.button("Test LLM"):
        test_token = "LLM_CONNECT_OK"
        test_question = f"LLM CONNECTION TEST: Respond exactly with the single token: {test_token} and nothing else."
        payload = {"question": test_question, "params": {}}
        with st.spinner("Testing LLM..."):
            try:
                resp = requests.post(API_URL, json=payload, timeout=TIMEOUT)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                st.error(f"LLM test failed to call API: {e}")
                st.stop()
        answer = data.get("answer", "") or ""
        if test_token in answer:
            st.success("LLM test succeeded — model returned the expected token.")
            st.write("Returned answer:")
            st.code(answer)
        else:
            st.error("LLM test did NOT return the expected token.")
            st.write("Returned answer (may include explanation or failure):")
            st.code(answer)
        if show_raw:
            st.subheader("Raw response JSON")
            st.json(data)

# DB Test area left unchanged
st.markdown("---")
st.header("Database Connectivity Test")
st.markdown("This test attempts to connect directly to the Postgres database and run `SELECT * FROM raw.customers LIMIT 20`.\n\nThe Streamlit process will try to read the database URL from (in order): `st.secrets['DATABASE_URL']`, query param `db_url`, or the environment variable `DATABASE_URL`. If `psycopg` is not installed in this environment, the test will tell you how to install it.")

db_url = "postgresql://postgres:Plubzay_01@localhost:5432/Deep Insights Copilot"
if db_url:
    st.write("Using database URL from configuration.")
else:
    st.warning("No DATABASE_URL found. Please set st.secrets['DATABASE_URL'], pass ?db_url=... in the URL, or set the DATABASE_URL environment variable where Streamlit runs. Example: postgresql://demo:demopw@localhost:5432/deep_insights")

if st.button("Test DB (SELECT * FROM raw.customers)"):
    if not db_url:
        st.error("Cannot run DB test — no DATABASE_URL configured.")
    else:
        try:
            import psycopg
        except Exception as e:
            st.error("Missing required package 'psycopg'. Install it with: pip install psycopg[binary]")
            st.stop()
        with st.spinner("Connecting to database and running query..."):
            try:
                conn = psycopg.connect(db_url, autocommit=True)
                with conn.cursor() as cur:
                    cur.execute('SELECT * FROM analytics.dim_customer LIMIT 20;')
                    cols = [c.name for c in cur.description]
                    rows = cur.fetchall()
                df = pd.DataFrame(rows, columns=cols)
                st.success(f"Query returned {len(df)} rows.")
                st.dataframe(df)
            except Exception as e:
                st.error(f"DB query failed: {e}")

st.markdown("""
Notes:
- For Docker / compose, point DATABASE_URL to the 'postgres' service (e.g. postgresql://demo:demopw@postgres:5432/deep_insights).
- If running Streamlit locally, ensure the Postgres port is reachable and credentials are correct.
""")
