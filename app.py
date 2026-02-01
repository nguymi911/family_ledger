import streamlit as st
from st_supabase_connection import SupabaseConnection
from gemini_client import get_gemini_model

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

# Perform a query.
rows = st_conn.client.from_("transactions").select("*", count="exact").execute()

# Print results.
for row in rows.data:
    st.write(f"{row['description']} costs {row['amount']}")
