import streamlit as st
import requests

st.title("AI Support Ticket Classifier")

text = st.text_area("Paste a customer complaint:")
if st.button("Classify"):
    with st.spinner("Classifying..."):
        r = requests.post(f"{st.secrets['API_URL']}/classify", json={"ticket_text": text})
        if r.status_code == 200:
            res = r.json()
            try:
                confidence = float(res.get("confidence", 0))
            except (TypeError, ValueError):
                confidence = 0.0

            st.success(f"Category: {res['category']} ({confidence:.2f})")
            st.caption(res['explanation'])
        else:
            st.error(r.text)
