import streamlit as st
import database as db


class MockUser:
    """Mock user for when auth is disabled."""
    id = "00000000-0000-0000-0000-000000000000"
    email = "demo@example.com"


class SessionUser:
    """User object constructed from session state."""
    def __init__(self, user_id, email):
        self.id = user_id
        self.email = email


def get_user(client):
    """Get current authenticated user from session token or session state."""
    # Check session state first (faster)
    if "auth_user_id" in st.session_state and "auth_user_email" in st.session_state:
        return SessionUser(st.session_state["auth_user_id"], st.session_state["auth_user_email"])

    # Try to restore from session token in query params
    params = st.query_params
    session_token = params.get("session")

    if session_token:
        # Validate session token
        user_id = db.get_session(client, session_token)
        if user_id:
            # Get user email from profile
            profile = db.get_profile(client, user_id)
            if profile:
                email = profile.get("display_name", "user")  # Use display_name as fallback
                # Restore to session state
                st.session_state["auth_user_id"] = user_id
                st.session_state["auth_user_email"] = email
                st.session_state["session_token"] = session_token
                return SessionUser(user_id, email)
        else:
            # Invalid or expired session token, clear it
            st.query_params.clear()

    return None


def sign_up(client, email, password, display_name):
    """Register a new user with email and password."""
    try:
        response = client.auth.sign_up({"email": email, "password": password})
        if response.user:
            if response.user.identities and len(response.user.identities) == 0:
                st.error("This email is already registered. Please sign in.")
            else:
                # Store display name in session for profile creation after email confirmation
                st.session_state["pending_display_name"] = display_name
                st.success("Check your email for a confirmation link.")
        return response
    except Exception as e:
        st.error(f"Sign up error: {e}")
        return None


def sign_in(client, email, password):
    """Sign in with email and password."""
    try:
        response = client.auth.sign_in_with_password({"email": email, "password": password})
        if response.user:
            # Create session token
            session_token = db.create_session(client, response.user.id)

            # Store user info in session state
            st.session_state["auth_user_id"] = response.user.id
            st.session_state["auth_user_email"] = response.user.email
            st.session_state["session_token"] = session_token

            # Persist only session token to URL query params (not raw user data)
            st.query_params["session"] = session_token

            st.rerun()
        return response
    except Exception as e:
        st.error(f"Sign in error: {e}")
        return None


def logout(client):
    """Sign out the current user."""
    try:
        # Delete session from database
        if "session_token" in st.session_state:
            db.delete_session(client, st.session_state["session_token"])
            del st.session_state["session_token"]

        # Clear session state
        if "auth_user_id" in st.session_state:
            del st.session_state["auth_user_id"]
        if "auth_user_email" in st.session_state:
            del st.session_state["auth_user_email"]
        if "profile" in st.session_state:
            del st.session_state["profile"]

        # Clear query params
        st.query_params.clear()

        client.auth.sign_out()
        st.rerun()
    except Exception as e:
        st.error(f"Logout error: {e}")


def require_login(client):
    """Check auth and show login page if needed. Returns user or None."""
    user = get_user(client)

    # Check if auth is required
    try:
        require_auth = st.secrets["features"]["require_auth"]
    except KeyError:
        require_auth = True

    if require_auth and not user:
        # Hide sidebar on login page
        st.markdown("""
            <style>
                [data-testid="stSidebar"] { display: none; }
                [data-testid="stSidebarNav"] { display: none; }
            </style>
        """, unsafe_allow_html=True)

        st.title("Annie Budget")
        st.write("Please sign in to continue.")

        tab_signin, tab_signup = st.tabs(["Sign In", "Sign Up"])

        with tab_signin:
            with st.form("signin_form"):
                email = st.text_input("Email", key="signin_email")
                password = st.text_input("Password", type="password", key="signin_password")
                submitted = st.form_submit_button("Sign In", type="primary")
                if submitted and email and password:
                    sign_in(client, email, password)

        with tab_signup:
            with st.form("signup_form"):
                display_name = st.text_input("Your Name", key="signup_name")
                email = st.text_input("Email", key="signup_email")
                password = st.text_input("Password", type="password", key="signup_password")
                password_confirm = st.text_input("Confirm Password", type="password", key="signup_password_confirm")
                submitted = st.form_submit_button("Sign Up", type="primary")
                if submitted:
                    if not display_name:
                        st.error("Name is required.")
                    elif not email or not password:
                        st.error("Email and password are required.")
                    elif password != password_confirm:
                        st.error("Passwords do not match.")
                    elif len(password) < 6:
                        st.error("Password must be at least 6 characters.")
                    else:
                        sign_up(client, email, password, display_name)

        st.stop()

    # Return mock user if auth disabled
    if not user:
        user = MockUser()

    return user
