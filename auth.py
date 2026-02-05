import streamlit as st
import database as db


def set_session_cookie(token: str):
    """Set session token in browser cookie via JavaScript."""
    st.markdown(f"""
        <script>
            document.cookie = "session_token={token}; path=/; max-age=604800; SameSite=Lax";
        </script>
    """, unsafe_allow_html=True)


def clear_session_cookie():
    """Clear session cookie via JavaScript."""
    st.markdown("""
        <script>
            document.cookie = "session_token=; path=/; max-age=0; path=/";
        </script>
    """, unsafe_allow_html=True)


def get_session_from_cookie():
    """
    Read session token from cookie using JS and redirect if needed.
    """
    # Check if we already have session in query params
    if st.query_params.get("session"):
        return

    # Inject JS to read cookie and redirect if token exists
    # Using st.markdown for earlier execution than components.html
    st.markdown("""
        <script>
            (function() {
                const cookies = document.cookie.split(';');
                for (let cookie of cookies) {
                    const [name, value] = cookie.trim().split('=');
                    if (name === 'session_token' && value) {
                        const url = new URL(window.location.href);
                        if (!url.searchParams.has('session')) {
                            url.searchParams.set('session', value);
                            window.location.replace(url.toString());
                        }
                    }
                }
            })();
        </script>
    """, unsafe_allow_html=True)


class SessionUser:
    """User object constructed from session state."""
    def __init__(self, user_id, email):
        self.id = user_id
        self.email = email


def get_user(client):
    """Get current authenticated user from session token or session state."""
    # Check session state first (faster) - but only if we have a session token
    if ("auth_user_id" in st.session_state and
        "auth_user_email" in st.session_state and
        "session_token" in st.session_state):
        # Ensure session token stays in URL for page navigation
        if not st.query_params.get("session"):
            st.query_params["session"] = st.session_state["session_token"]
        return SessionUser(st.session_state["auth_user_id"], st.session_state["auth_user_email"])

    # Try to restore session from cookie if not in URL
    get_session_from_cookie()

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

            if not session_token:
                st.error("Failed to create session. Check that the sessions table exists in Supabase.")
                return None

            # Store user info in session state
            st.session_state["auth_user_id"] = response.user.id
            st.session_state["auth_user_email"] = response.user.email
            st.session_state["session_token"] = session_token

            # Persist session token to cookie and URL
            set_session_cookie(session_token)
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

        # Clear cookie and query params
        clear_session_cookie()
        st.query_params.clear()

        client.auth.sign_out()
        st.rerun()
    except Exception as e:
        st.error(f"Logout error: {e}")


def require_login(client):
    """Check auth and show login page if needed. Returns authenticated user."""
    user = get_user(client)

    if not user:
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

    return user
