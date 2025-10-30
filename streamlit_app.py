# import streamlit as st
# import requests

# st.title("AI Support Ticket Classifier")

# text = st.text_area("Paste a customer complaint:")
# if st.button("Classify"):
#     with st.spinner("Classifying..."):
#         r = requests.post(f"{st.secrets['API_URL']}/classify", json={"ticket_text": text})
#         if r.status_code == 200:
#             res = r.json()
#             try:
#                 confidence = float(res.get("confidence", 0))
#             except (TypeError, ValueError):
#                 confidence = 0.0

#             st.success(f"Category: {res['category']} ({confidence:.2f})")
#             st.caption(res['explanation'])
#         else:
#             st.error(r.text)



# import streamlit as st
# import requests
# import json

# st.title("AI Support Ticket Classifier")

# # 1️⃣ Model selection
# model_choice = st.selectbox(
#     "Select Model",
#     ["Auto (OpenAI)", "OpenAI", "Bedrock"]
# )

# # 2️⃣ User input for ticket
# ticket_text = st.text_area("Paste the customer ticket here:")

# if st.button("Classify Ticket"):
#     if not ticket_text.strip():
#         st.warning("Please enter a ticket text.")
#     else:
#         # Map the selectbox to the value we want to send in JSON
#         if model_choice == "Auto (OpenAI)":
#             model_value = "auto"
#         elif model_choice == "OpenAI":
#             model_value = "openai"
#         elif model_choice == "Bedrock":
#             model_value = "bedrock"

#         payload = {
#             "ticket_text": ticket_text,
#             "model": model_value
#         }

#         try:
#             res = requests.post(
#                 f"{st.secrets['API_URL']}/classify",
#                 json=payload
#             )
#             res.raise_for_status()
#             data = res.json()

#             # Display results
#             confidence = float(data.get("confidence", 0))
#             st.success(f"Category: {data.get('category')} ({confidence:.2f})")
#             st.info(f"Explanation: {data.get('explanation')}")
#         except Exception as e:
#             st.error(f"Error: {e}")


import streamlit as st
import requests
import json
from collections import Counter
import pandas as pd
import altair as alt

st.set_page_config(page_title="AI Support Ticket Classifier", layout="wide")
st.title("AI Support Ticket Classifier 🚀")

# 1️⃣ Model selection
model_choice = st.selectbox(
    "Select Model",
    ["Auto (OpenAI)", "OpenAI", "Bedrock"]
)

# 2️⃣ Ticket input
ticket_text = st.text_area("Paste the customer ticket here:")

if st.button("Classify Ticket"):
    if not ticket_text.strip():
        st.warning("Please enter a ticket text.")
    else:
        # Map selection to value sent to API
        if model_choice == "Auto (OpenAI)":
            model_value = "auto"
        elif model_choice == "OpenAI":
            model_value = "openai"
        elif model_choice == "Bedrock":
            model_value = "bedrock"

        payload = {
            "ticket_text": ticket_text,
            "model": model_value
        }

        try:
            res = requests.post(
                f"{st.secrets['API_URL']}/classify",
                json=payload
            )
            res.raise_for_status()
            data = res.json()

            confidence = float(data.get("confidence", 0))
            st.success(f"Category: {data.get('category')} ({confidence:.2f})")
            st.info(f"Explanation: {data.get('explanation')}")
        except Exception as e:
            st.error(f"Error: {e}")

st.markdown("---")

# 3️⃣ Fetch and display recent tickets
st.subheader("Recent Tickets")
try:
    resp = requests.get(f"{st.secrets['API_URL']}/tickets")
    resp.raise_for_status()
    tickets = resp.json()

    if tickets:
        # Display table
        df = pd.DataFrame(tickets)
        df["confidence"] = df["confidence"].astype(float)
        df = df.sort_values(by="created_at", ascending=False)
        st.dataframe(df[["ticket_text", "category", "confidence", "created_at"]])

        # 4️⃣ Category counts chart
        category_counts = Counter(df["category"])
        chart_data = pd.DataFrame({
            "category": list(category_counts.keys()),
            "count": list(category_counts.values())
        })

        chart = alt.Chart(chart_data).mark_bar().encode(
            x="category",
            y="count",
            tooltip=["category", "count"]
        ).properties(
            width=600,
            height=400,
            title="Ticket Counts per Category"
        )

        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No tickets found yet.")
except Exception as e:
    st.error(f"Failed to load tickets: {e}")
