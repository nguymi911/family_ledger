import streamlit as st
from database import get_connection
from auth import require_login, logout

st.set_page_config(page_title="Annie Budget", page_icon="💰")

# Initialize connection and authenticate
conn = get_connection()
client = conn.client
user = require_login(client)

# Store in session state for pages to access
st.session_state["client"] = client
st.session_state["user"] = user

# User info in sidebar (visible on all pages)
with st.sidebar:
    st.write(f"**{user.email}**")
    if st.button("Logout"):
        logout(client)
    st.divider()

# Navigation
pages = [
    st.Page("pages/0_Add_Transaction.py", title="Add Transaction", icon="➕"),
    st.Page("pages/1_Monthly_Transactions.py", title="Monthly Transactions", icon="📅"),
    st.Page("pages/2_Manage_Categories.py", title="Manage Categories", icon="⚙️"),
]

nav = st.navigation(pages)
nav.run()
