"""Prediction probability visualization."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from services.frontend.src.models.prediction_model import PredictionResponse

SEVERITY_LABELS = {
    0: "Unharmed / Lightly injured",
    1: "Injured (hospitalized) / Killed",
}


def render_prediction_confidence(result: PredictionResponse) -> None:
    """Render probability for each severity class."""

    if not result.probabilities:
        if result.probability is None:
            st.html(
                """
                <div class="asp-chart-unavailable">
                    Probability data is not available.
                </div>
                """
            )
            return

        # Backward-compatible fallback while the backend is being updated.
        probabilities = {
            result.severity_code: result.probability,
        }
    else:
        probabilities = result.probabilities

    class_codes = sorted(probabilities)
    labels = [SEVERITY_LABELS.get(code, f"Class {code}") for code in class_codes]
    values = [max(0.0, min(1.0, probabilities[code])) * 100 for code in class_codes]

    fig = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            text=[f"{value:.1f}%" for value in values],
            textposition="inside",
            hovertemplate=("<b>%{y}</b><br>Probability: %{x:.1f}%<extra></extra>"),
        )
    )

    fig.update_layout(
        height=130,
        margin=dict(
            l=0,
            r=0,
            t=5,
            b=5,
        ),
        xaxis=dict(
            range=[0, 100],
            showgrid=False,
            showticklabels=False,
            zeroline=False,
            fixedrange=True,
        ),
        yaxis=dict(
            showgrid=False,
            showticklabels=True,
            zeroline=False,
            fixedrange=True,
            automargin=True,
        ),
        showlegend=False,
        hovermode="y",
    )

    st.plotly_chart(
        fig,
        width="stretch",
        config={
            "displayModeBar": False,
            "responsive": True,
        },
    )
