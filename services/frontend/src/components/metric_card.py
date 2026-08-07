"""
Metric card component.
"""

from dataclasses import dataclass

import streamlit as st


@dataclass(slots=True)
class MetricCard:
    title: str
    value: str
    delta: str | None = None


def render_metric_card(card: MetricCard) -> None:

    st.metric(
        label=card.title,
        value=card.value,
        delta=card.delta,
    )
