"""Prediction confidence visualization."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from services.frontend.src.models.prediction_model import PredictionResponse


def render_prediction_confidence(result: PredictionResponse) -> None:
    """Render the confidence of the predicted severity."""

    if result.probability is None:
        st.html(
            """
            <div class="asp-chart-unavailable">
                Confidence data is not available.
            </div>
            """
        )
        return

    probability = max(0.0, min(1.0, result.probability))
    confidence_percent = probability * 100

    fig = go.Figure(
        go.Bar(
            x=[confidence_percent],
            y=["Confidence"],
            orientation="h",
            text=[f"{confidence_percent:.1f}%"],
            textposition="inside",
            hovertemplate=("<b>Prediction confidence</b><br>%{x:.1f}%<extra></extra>"),
        )
    )

    fig.update_layout(
        height=90,
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
            showticklabels=False,
            zeroline=False,
            fixedrange=True,
        ),
        showlegend=False,
        hovermode="x",
    )

    st.plotly_chart(
        fig,
        width="stretch",
        config={
            "displayModeBar": False,
            "responsive": True,
        },
    )
