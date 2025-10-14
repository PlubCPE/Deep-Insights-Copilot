# demo_ui/streamlit_app.py
import streamlit as st
import requests
import pandas as pd
from datetime import date

# API_URL = st.secrets.get("API_URL", "http://localhost:8000/ask")
TIMEOUT = 30

st.set_page_config(page_title="Deep Insights Copilot — Demo", layout="wide")

st.title("Deep Insights Copilot — Demo UI (Streamlit)")
st.write("Ask questions and see RAG + KPI tool outputs with provenance and SQL templates.")

with st.sidebar:
    st.header("Query parameters")
    start_date = st.date_input("Start date", value=date(2025, 9, 1))
    end_date = st.date_input("End date", value=date(2025, 9, 30))
    top_n = st.number_input("Top N (KPIs)", min_value=1, max_value=50, value=5)
    product_id = st.text_input("Product ID filter (optional)")
    show_raw = st.checkbox("Show raw JSON", value=False)
    st.markdown("---")
    st.markdown("Tip: use questions like:\n- `Top 5 root causes of product issues in Sep 2025`\n- `What does the refunds policy say about chargebacks?`")

query = st.text_area("Question", height=120, value="Top 5 root causes of product issues in Sep 2025")
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

    # Main answer area
    st.subheader("Answer")
    answer = data.get("answer", "")
    st.markdown(answer)

    # Provenance / KB chunks
    kb = data.get("kb")
    if kb:
        st.subheader("Retrieved knowledge chunks")
        for i, chunk in enumerate(kb):
            title = chunk.get("source", f"chunk-{i}") + f" — score: {chunk.get('score', '')}"
            with st.expander(title, expanded=(i == 0)):
                # try fields
                if "chunk" in chunk:
                    st.write(chunk["chunk"])
                elif "chunk_text" in chunk:
                    st.write(chunk["chunk_text"])
                else:
                    st.write(chunk)

    # KPI / structured tables
    kpi = data.get("kpi")
    if kpi:
        st.subheader("KPI / Aggregation results")
        try:
            df = pd.DataFrame(kpi)
            st.dataframe(df)
            # small bar chart if numeric
            if "count" in df.columns:
                st.bar_chart(df.set_index(df.columns[0])["count"])
        except Exception:
            st.write(kpi)

    # SQL info (if returned)
    sql_info = data.get("sql_executed") or data.get("sql")
    if sql_info:
        st.subheader("SQL executed / Template")
        if isinstance(sql_info, dict):
            # expect {"template": "...", "rendered": "..."}
            template = sql_info.get("template")
            rendered = sql_info.get("rendered")
            if template:
                st.markdown("**Template:**")
                st.code(template, language="sql")
            if rendered:
                st.markdown("**Rendered SQL:**")
                st.code(rendered, language="sql")
        else:
            st.code(sql_info, language="sql")

    # audit log snippet if available
    audit = data.get("audit")
    if audit:
        st.subheader("Audit log (last entry)")
        st.json(audit)

    if show_raw:
        st.subheader("Raw response JSON")
        st.json(data)
