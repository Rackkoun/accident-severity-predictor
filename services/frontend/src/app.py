"""
ASP frontend entrypoint
"""

from pathlib import Path

import streamlit as st

from services.frontend.src.components.sidebar import render_sidebar
from services.frontend.src.config.settings import settings
from services.frontend.src.pages.home import home_page
from services.frontend.src.pages.login import login_page
from services.frontend.src.pages.monitoring import monitoring_page
from services.frontend.src.pages.prediction import prediction_page


def load_css() -> None:
    css = Path(__file__).parent / "assets" / "style.css"
    with open(css, encoding="utf-8") as file:
        st.markdown(
            f"<style>{file.read()}</style>",
            unsafe_allow_html=True,
        )


def initialize_session() -> None:

    defaults = {
        "page": "Home",
        "authenticated": False,
        "token": None,
    }

    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def main() -> None:
    st.set_page_config(
        page_title=settings.page_title,
        page_icon=settings.page_icon,
        layout=settings.layout,
        initial_sidebar_state=settings.sidebar_state,
    )

    # load css
    load_css()
    # initialize session state
    initialize_session()
    # render sidebar
    render_sidebar()

    page = st.session_state.page

    if page == "Home":
        home_page()
    elif page == "Prediction":
        prediction_page()
    elif page == "Monitoring":
        monitoring_page()
    elif page == "Login":
        login_page()


if __name__ == "__main__":
    main()
