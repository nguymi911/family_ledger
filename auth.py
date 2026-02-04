import streamlit as st
import streamlit.components.v1 as components
import urllib.parse


class MockUser:
    """Mock user for when auth is disabled."""
    id = "00000000-0000-0000-0000-000000000000"
    email = "demo@example.com"


class SessionUser:
    """User object constructed from session state."""
    def __init__(self, user_id, email):
        self.id = user_id
        self.email = email


def get_cookies_from_header():
    """Get cookies from the HTTP request header."""
    try:
        from streamlit.web.server.websocket_headers import _get_websocket_headers
        headers = _get_websocket_headers()
        if headers and "Cookie" in headers:
            cookie_str = headers["Cookie"]
            cookies = {}
            for item in cookie_str.split(";"):
                if "=" in item:
                    key, value = item.strip().split("=", 1)
                    cookies[key] = value
            return cookies
    except Exception:
        pass
    return {}


def set_cookies_and_reload(user_id, email):
    """Set cookies via JavaScript and reload the page."""
    encoded_email = urllib.parse.quote(email)
    max_age = 30 * 24 * 60 * 60  # 30 days

    js = f"""
    <script>
        // Set cookies on parent window
        document.cookie = "auth_user_id={user_id}; max-age={max_age}; path=/; SameSite=Strict";
        document.cookie = "auth_user_email={encoded_email}; max-age={max_age}; path=/; SameSite=Strict";

        // Reload parent page after a short delay
        window.parent.location.reload();
    </script>
    """
    components.html(js, height=0)


def clear_cookies_and_reload():
    """Clear cookies via JavaScript and reload the page."""
    js = """
    <script>
        // Clear cookies on parent window
        document.cookie = "auth_user_id=; max-age=0; path=/; SameSite=Strict";
        document.cookie = "auth_user_email=; max-age=0; path=/; SameSite=Strict";

        // Reload parent page
        window.parent.location.reload();
    </script>
    """
    components.html(js, height=0)


def get_user(client):
    """Get current authenticated user from cookies or session."""
    # Check session state first (faster)
    if "auth_user_id" in st.session_state and "auth_user_email" in st.session_state:
        return SessionUser(st.session_state["auth_user_id"], st.session_state["auth_user_email"])

    # Try to restore from cookies
    cookies = get_cookies_from_header()
    user_id = cookies.get("auth_user_id")
    user_email = cookies.get("auth_user_email")

    if user_id and user_email:
        # URL decode the email
        user_email = urllib.parse.unquote(user_email)
        # Restore to session state
        st.session_state["auth_user_id"] = user_id
        st.session_state["auth_user_email"] = user_email
        return SessionUser(user_id, user_email)

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
            # Store user info in session state
            st.session_state["auth_user_id"] = response.user.id
            st.session_state["auth_user_email"] = response.user.email

            # Set cookies and reload via JavaScript (don't call st.rerun)
            set_cookies_and_reload(response.user.id, response.user.email)
            st.stop()  # Stop execution, let JS reload the page
        return response
    except Exception as e:
        st.error(f"Sign in error: {e}")
        return None


def logout(client):
    """Sign out the current user."""
    try:
        # Clear session state
        if "auth_user_id" in st.session_state:
            del st.session_state["auth_user_id"]
        if "auth_user_email" in st.session_state:
            del st.session_state["auth_user_email"]
        if "profile" in st.session_state:
            del st.session_state["profile"]

        client.auth.sign_out()

        # Clear cookies and reload via JavaScript
        clear_cookies_and_reload()
        st.stop()  # Stop execution, let JS reload the page
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
