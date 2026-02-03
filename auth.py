import streamlit as st


class MockUser:
    """Mock user for when auth is disabled."""
    id = "00000000-0000-0000-0000-000000000000"
    email = "demo@example.com"


def get_user(client):
    """Get current authenticated user from session."""
    try:
        session = client.auth.get_session()
        if session:
            return session.user
    except Exception:
        pass
    return None


def sign_up(client, email, password):
    """Register a new user with email and password."""
    try:
        response = client.auth.sign_up({"email": email, "password": password})
        if response.user:
            if response.user.identities and len(response.user.identities) == 0:
                st.error("This email is already registered. Please sign in.")
            else:
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
            st.rerun()
        return response
    except Exception as e:
        st.error(f"Sign in error: {e}")
        return None


def logout(client):
    """Sign out the current user."""
    try:
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
                email = st.text_input("Email", key="signup_email")
                password = st.text_input("Password", type="password", key="signup_password")
                password_confirm = st.text_input("Confirm Password", type="password", key="signup_password_confirm")
                submitted = st.form_submit_button("Sign Up", type="primary")
                if submitted:
                    if not email or not password:
                        st.error("Email and password are required.")
                    elif password != password_confirm:
                        st.error("Passwords do not match.")
                    elif len(password) < 6:
                        st.error("Password must be at least 6 characters.")
                    else:
                        sign_up(client, email, password)

        st.stop()

    # Return mock user if auth disabled
    if not user:
        user = MockUser()

    return user
