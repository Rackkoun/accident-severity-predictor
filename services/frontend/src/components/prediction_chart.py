"""Prediction probability visualization."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from services.frontend.src.models.model_info import ModelInfo
from services.frontend.src.models.prediction_model import PredictionResponse


def _probability_color(
    probability: float,
    *,
    severity_code: int,
) -> str:
    """
    Dynamic color based on probability.

    Class 1 = higher severity:
        low probability  -> green
        medium           -> orange
        high             -> red

    Class 0 = lower severity:
        high probability -> green
        medium           -> orange
        low probability  -> red
    """
    if severity_code == 1:
        if probability >= 0.70:
            return "#ef4444"
        if probability >= 0.40:
            return "#f59e0b"
        return "#22c55e"

    if probability >= 0.70:
        return "#22c55e"
    if probability >= 0.40:
        return "#f59e0b"
    return "#ef4444"


def _build_gauge(
    *,
    title: str,
    probability: float,
    severity_code: int,
) -> go.Figure:
    value = probability * 100

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            number={
                "suffix": "%",
                "font": {
                    "size": 30,
                },
            },
            title={
                "text": title,
                "font": {
                    "size": 15,
                },
            },
            gauge={
                "axis": {
                    "range": [0, 100],
                    "ticksuffix": "%",
                    "tickwidth": 1,
                    "dtick": 25,
                },
                "bar": {
                    "color": _probability_color(
                        probability,
                        severity_code=severity_code,
                    ),
                    "thickness": 0.65,
                },
                "bgcolor": "rgba(128, 128, 128, 0.12)",
                "borderwidth": 0,
            },
        )
    )

    fig.update_layout(
        height=230,
        margin={
            "l": 20,
            "r": 20,
            "t": 55,
            "b": 10,
        },
        paper_bgcolor="rgba(0,0,0,0)",
        font={
            "color": "#E5E7EB",
        },
    )

    return fig


def render_prediction_confidence(
    result: PredictionResponse,
) -> None:
    """
    Render the probability of each severity class as a gauge.
    """

    probabilities = result.probabilities

    unharmed_probability = float(probabilities.get(0, 0.0))
    severe_probability = float(probabilities.get(1, 0.0))

    st.html(
        """
        <div style="
            margin-top: 1rem;
            margin-bottom: 0.25rem;
            font-size: 0.95rem;
            font-weight: 600;
        ">
            Prediction Confidence
        </div>
        """
    )

    col1, col2 = st.columns(2)

    with col1:
        fig = _build_gauge(
            title="Unharmed / Lightly injured",
            probability=unharmed_probability,
            severity_code=0,
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": False,
            },
        )

    with col2:
        fig = _build_gauge(
            title="Injured / Killed",
            probability=severe_probability,
            severity_code=1,
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": False,
            },
        )


def render_key_factors(model_info: ModelInfo) -> None:
    """Render the top global model factors as a radar chart."""

    feature_importance = getattr(model_info, "feature_importance", None)

    if not feature_importance:
        return

    top_features = sorted(
        feature_importance.items(),
        key=lambda item: item[1],
        reverse=True,
    )[:6]

    if not top_features:
        return

    names = [name for name, _ in top_features]
    importances = [float(value) for _, value in top_features]

    max_importance = max(importances)

    if max_importance <= 0:
        return

    # Normalize relative to the most important feature.
    normalized = [(value / max_importance) * 100 for value in importances]

    # Close the polygon.
    radar_names = names + [names[0]]
    radar_values = normalized + [normalized[0]]

    actual_percentages = [value * 100 for value in importances]

    hover_values = [f"{name}<br>Global importance: {value:.2f}%" for name, value in zip(names, actual_percentages, strict=True)]

    fig = go.Figure()

    fig.add_trace(
        go.Scatterpolar(
            r=radar_values,
            theta=radar_names,
            fill="toself",
            name="Model factors",
            text=hover_values + [hover_values[0]],
            hovertemplate="%{text}<extra></extra>",
            line={
                "width": 2,
            },
            marker={
                "size": 6,
            },
        )
    )

    fig.update_layout(
        height=430,
        margin={
            "l": 70,
            "r": 70,
            "t": 55,
            "b": 55,
        },
        paper_bgcolor="rgba(0,0,0,0)",
        polar={
            "radialaxis": {
                "visible": True,
                "range": [0, 100],
                "showticklabels": False,
                "gridwidth": 1,
            },
            "angularaxis": {
                "tickfont": {
                    "size": 11,
                },
            },
        },
        showlegend=False,
    )

    st.html(
        """
        <div style="
            margin-top: 1rem;
            margin-bottom: 0.25rem;
            font-size: 0.95rem;
            font-weight: 600;
        ">
            Key Model Factors
        </div>

        <div style="
            margin-bottom: 0.5rem;
            font-size: 0.78rem;
            opacity: 0.65;
        ">
            Top global feature importances used by the model
        </div>
        """
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "displayModeBar": False,
        },
    )
