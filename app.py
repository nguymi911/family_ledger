import streamlit as st
from database import get_connection, get_profile, create_profile
from auth import require_login, logout

st.set_page_config(page_title="Annie Budget", page_icon="💰")

# Initialize connection and authenticate
conn = get_connection()
client = conn.client
user = require_login(client)

# Check if user has a profile, create one if not (only if auth is enabled)
require_auth = st.session_state.get("require_auth", True)

if require_auth:
    profile = get_profile(client, user.id)

    if not profile:
        # Hide sidebar on profile setup page
        st.markdown("""
            <style>
                [data-testid="stSidebar"] { display: none; }
                [data-testid="stSidebarNav"] { display: none; }
            </style>
        """, unsafe_allow_html=True)

        st.title("Welcome to Annie Budget!")
        st.write("Please set up your profile to continue.")

        # Check if we have a pending display name from signup
        default_name = st.session_state.get("pending_display_name", "")

        with st.form("profile_form"):
            display_name = st.text_input("Your Name", value=default_name)
            submitted = st.form_submit_button("Save Profile", type="primary")
            if submitted:
                if display_name:
                    try:
                        create_profile(client, user.id, display_name)
                        if "pending_display_name" in st.session_state:
                            del st.session_state["pending_display_name"]
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error creating profile: {e}")
                else:
                    st.error("Name is required.")
        st.stop()
else:
    # Mock profile for when auth is disabled
    profile = {"display_name": "Demo User"}

# Store in session state for pages to access
st.session_state["client"] = client
st.session_state["user"] = user
st.session_state["profile"] = profile

# User info in sidebar (visible on all pages)
with st.sidebar:
    st.write(f"**{profile['display_name']}**")
    st.caption(user.email)
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
