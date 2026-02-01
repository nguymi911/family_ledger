import streamlit as st
from st_supabase_connection import SupabaseConnection

# Initialize connection
st_conn = st.connection(
    "supabase",
    type=SupabaseConnection,
    url=st.secrets["connections"]["supabase"]["url"],
    key=st.secrets["connections"]["supabase"]["key"],
)

st.title("Family Ledger")

# Perform a query.
rows = st_conn.client.from_("transactions").select("*", count="exact").execute()

# Print results.
for row in rows.data:
    st.write(f"{row['description']} costs {row['amount']}")
