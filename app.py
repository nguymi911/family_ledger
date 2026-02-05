import streamlit as st
from database import get_connection, get_profile, create_profile
from auth import require_login, logout

st.set_page_config(page_title="Annie Budget", page_icon="💰")

# Global styles for consistent look across all pages
st.markdown("""
    <style>
    /* Main content text */
    [data-testid="stMarkdown"] p {
        font-size: 1.15rem;
        line-height: 1.4;
    }
    /* Caption/meta text */
    [data-testid="stCaptionContainer"] {
        font-size: 0.85rem;
    }
    /* Form labels */
    [data-testid="stWidgetLabel"] {
        font-size: 0.9rem;
    }
    /* Hide "Press Enter to submit form" text */
    [data-testid="stFormSubmitButton"] div[data-testid="stMarkdownContainer"] {
        display: none;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize connection and authenticate
conn = get_connection()
client = conn.client
user = require_login(client)

# Check if user has a profile, create one if not
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
