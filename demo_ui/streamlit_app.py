import streamlit as st
import requests
import pandas as pd
from datetime import date

st.set_page_config(page_title="Deep Insights Copilot — Streamlit Demo", layout="wide")

# Configurable API URL via secrets or environment fallback
API_URL = "http://localhost:8000/ask"
TIMEOUT = 30

st.title("Deep Insights Copilot — Streamlit Demo UI")
st.markdown("Use this UI to ask questions and test LLM connectivity. The **Test LLM** button sends a short prompt designed to verify the LLM responds.")

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
        # Use a deterministic test token the LLM should return verbatim
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
        # Simple check: does the expected token appear in the returned answer?
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

st.markdown("---")
st.markdown("Notes: For the LLM test to pass, the API server must be reachable and the backend must be configured to use an LLM provider (OpenRouter/OpenAI). If you use OpenRouter with Llama 3.3 8B, ensure `OPENROUTER_API_KEY` and `OPENROUTER_MODEL` are set in the API environment.")
