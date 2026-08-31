"""Frontend authentication session helpers."""

import base64
import binascii
import json

import streamlit as st


def initialize_session() -> None:
    """initialize frontend session state."""

    defaults = {
        "page": "Home",
        "authenticated": False,
        "token": None,
        "username": None,
        "role": None,
        "remember_me": False,
        "post_login_page": "Home",
        "prediction_result": None,
    }

    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def set_authenticated_session(
    token: str,
    username: str,
    remember_me: bool = False,
) -> None:
    """store authentication information in the Streamlit session."""

    st.session_state.authenticated = True
    st.session_state.token = token
    st.session_state.username = username
    st.session_state.remember_me = remember_me
    st.session_state.role = get_role_from_token(token)


def clear_authenticated_session() -> None:
    """clear authentication state."""

    st.session_state.authenticated = False
    st.session_state.token = None
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.remember_me = False
    st.session_state.post_login_page = "Home"
    st.session_state.prediction_result = None
    st.session_state.page = "Home"


def get_role_from_token(token: str | None) -> str | None:
    """
    Read the role claim from the JWT.

    This is used only for frontend navigation visibility.
    Backend authorization remains authoritative.
    """

    if not token:
        return None

    try:
        parts = token.split(".")

        if len(parts) != 3:
            return None

        payload = parts[1]

        padding = "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(
            payload + padding,
        )

        claims = json.loads(decoded.decode("utf-8"))

        role = claims.get("role")

        if isinstance(role, str):
            return role

    except (
        ValueError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        binascii.Error,
    ):
        return None

    return None


def is_authenticated() -> bool:
    """return whether the current session is authenticated."""

    return bool(st.session_state.get("authenticated") and st.session_state.get("token"))


def is_admin() -> bool:
    """return whether the current user has the admin role."""

    return is_authenticated() and st.session_state.get("role") == "admin"


def is_data_scientist() -> bool:
    """return whether the current user has the standard user role."""

    return is_authenticated() and st.session_state.get("role") == "user"


def request_page(page: str) -> None:
    """
    Request navigation to a page.

    Protected pages remember the requested destination so that
    successful login can return the user directly to that page.
    """

    protected_pages = {
        "Prediction",
        "Model Insights",
        "Monitoring",
    }

    if page in protected_pages and not is_authenticated():
        st.session_state.post_login_page = page
        st.session_state.page = "Login"
        return

    st.session_state.page = page
