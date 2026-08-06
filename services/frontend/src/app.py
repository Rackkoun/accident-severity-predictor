"""
ASP frontend entrypoint
"""

from pathlib import Path

import streamlit as st

from services.frontend.src.config.settings import settings

st.set_page_config(
    page_title=settings.page_title,
    page_icon=settings.page_icon,
    layout=settings.layout,
    initial_sidebar_state=settings.sidebar_state,
)

css = Path(__file__).parent / "assets" / "style.css"
with open(css) as f:
    st.markdown(
        f"<style>{f.read()}</style>",
        unsafe_allow_html=True,
    )
