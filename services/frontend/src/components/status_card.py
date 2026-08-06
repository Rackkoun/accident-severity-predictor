"""
status card component
"""

import streamlit as st


def status_card(title: str, value: str, icon: str = "ℹ️") -> None:

    st.metric(label=f"{icon} {title}", value=value)
