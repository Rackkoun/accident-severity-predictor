"""
ASP home page.
"""

import streamlit as st

from services.frontend.src.components.metric_card import MetricCard, render_metric_card
from services.frontend.src.components.status_card import StatusCard, render_status_card


def home_page() -> None:

    st.title("🚗 Accident Severity Predictor")
    st.markdown("---")
    st.header("AI-powered Road Accident Severity Prediction")
    st.info("Welcome to the ASP plateform. \n\nUse the sidebar to navigate through the application")

    col1, col2 = st.columns(2)

    backend_status_card = StatusCard(title="Backend", value="Running", icon="🟢")
    prediction_status_card = StatusCard(title="Prediction API", value="Healthy", icon="✅")

    model_metric_card = MetricCard(title="Model", value="Random Forest")
    accuracy_metric_card = MetricCard(title="Accuracy", value="80.47 %")

    with col1:
        render_status_card(backend_status_card)
        render_status_card(prediction_status_card)

    with col2:
        render_metric_card(model_metric_card)
        render_metric_card(accuracy_metric_card)

    if st.button("Try Prediction"):
        st.session_state.page = "Prediction"
