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


def login_with_google(client):
    """Initiate Google OAuth login."""
    try:
        response = client.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {
                "redirect_to": st.secrets["oauth"]["app_url"]
            }
        })
        if response.url:
            st.markdown(f'<meta http-equiv="refresh" content="0;url={response.url}">', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Login error: {e}")


def logout(client):
    """Sign out the current user."""
    try:
        client.auth.sign_out()
        st.rerun()
    except Exception as e:
        st.error(f"Logout error: {e}")


def require_login(client):
    """Check auth and show login page if needed. Returns user or None."""
    # Handle OAuth callback
    query_params = st.query_params
    if "access_token" in query_params or "code" in query_params:
        st.query_params.clear()
        st.rerun()

    user = get_user(client)

    # Check if auth is required
    try:
        require_auth = st.secrets["features"]["require_auth"]
    except KeyError:
        require_auth = True

    if require_auth and not user:
        st.title("Annie Budget 💰")
        st.write("Please sign in to continue.")

        if st.button("Sign in with Google", type="primary"):
            login_with_google(client)

        st.stop()

    # Return mock user if auth disabled
    if not user:
        user = MockUser()

    return user
