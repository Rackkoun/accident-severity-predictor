"""
Metric card component.
"""

import streamlit as st


def metric_card(
    title: str,
    value: str,
    delta: str | None = None,
) -> None:

    st.metric(
        label=title,
        value=value,
        delta=delta,
    )
