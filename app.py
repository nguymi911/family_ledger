import streamlit as st
from st_supabase_connection import SupabaseConnection
from gemini_client import get_gemini_model
from nlp_parser import parse_expense

# Initialize connection
st_conn = st.connection(
    "supabase",
    type=SupabaseConnection,
    url=st.secrets["connections"]["supabase"]["url"],
    key=st.secrets["connections"]["supabase"]["key"],
)

# Initialize Gemini model
model = get_gemini_model()

st.title("Family Ledger")
st.success("Gemini 1.5 Flash connected")

# NLP Expense Entry
st.subheader("Quick Entry")
with st.form("expense_form"):
    expense_input = st.text_input(
        "Enter expense",
        placeholder="e.g., 200k for Annie toys, lunch 150k, coffee 50k yesterday"
    )
    submitted = st.form_submit_button("Parse")

if submitted and expense_input:
    with st.spinner("Parsing..."):
        parsed = parse_expense(expense_input, model)

    if "error" in parsed:
        st.error(parsed["error"])
    else:
        st.write("**Parsed Result:**")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Amount", f"{parsed['amount']:,.0f}")
            st.write(f"**Category:** {parsed['category']}")
        with col2:
            st.write(f"**Description:** {parsed['description']}")
            st.write(f"**Date:** {parsed['date'] or 'Today'}")
        if parsed["is_annie_related"]:
            st.info("Tagged as Annie-related expense")

st.divider()

# Perform a query.
st.subheader("Recent Transactions")
rows = st_conn.client.from_("transactions").select("*", count="exact").execute()

# Print results.
for row in rows.data:
    st.write(f"{row['description']} costs {row['amount']}")
