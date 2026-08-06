"""
Sidebar component
"""

import streamlit as st


def render_sidebar() -> None:
    with st.sidebar:
        st.title("🚗 ASP")
        st.markdown("---")

        if st.button("Home"):
            st.session_state.page = "Home"

        if st.button("🧪 Prediction Lab"):
            st.session_state.page = "Prediction"

        if st.button("📈 Monitoring"):
            st.session_state.page = "Monitoring"

        st.markdown("---")

        if st.session_state.authenticated:
            if st.button("🔓 Logout"):
                st.session_state.authenticated = False
                st.session_state.token = None
                st.session_state.page = "Home"
        else:
            if st.button("🔒 Login"):
                st.session_state.page = "Login"
