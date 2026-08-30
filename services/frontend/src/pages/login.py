"""ASP login page."""

import streamlit as st

from services.frontend.src.services.auth_service import login


def login_page() -> None:
    """Render the login page."""

    left, center, right = st.columns([1, 1.15, 1])

    with center:
        st.html(
            """
            <div class="asp-login-brand">
                <div class="asp-login-logo">ASP</div>
                <div class="asp-login-title">Accident Severity<br>Predictor</div>
            </div>

            <div class="asp-login-heading">Welcome back!</div>
            <div class="asp-login-subtitle">
                Please sign in to continue
            </div>
            """
        )

        with st.form("login_form"):
            username = st.text_input(
                "Username",
                placeholder="Enter your username",
            )

            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password",
            )

            remember = st.checkbox("Remember me")

            submitted = st.form_submit_button(
                "Login",
                use_container_width=True,
            )

        if submitted:
            if not username or not password:
                st.error("Please enter both username and password.")
                return

            token = login(username, password)

            if token is None:
                st.error("Invalid username or password.")
                return

            st.session_state.authenticated = True
            st.session_state.token = token.access_token
            st.session_state.username = username
            st.session_state.remember_me = remember
            st.session_state.page = "Home"

            st.success("Login successful.")
            st.rerun()

        st.html(
            """
            <div class="asp-login-footer">
                ASP v1.0.0<br>
                Capstone Project · DataScientest · 2026
            </div>
            """
        )
