"""
ASP home page.
"""

import streamlit as st

from services.frontend.src.components.metric_card import MetricCard, render_metric_card
from services.frontend.src.components.status_card import StatusCard, render_status_card
from services.frontend.src.services.health_service import get_health


def home_page() -> None:

    st.title("🚗 Accident Severity Predictor")
    st.markdown("---")
    st.header("AI-powered Road Accident Severity Prediction")
    st.info("Welcome to the ASP plateform. \n\nUse the sidebar to navigate through the application")

    health = get_health()

    backend_is_healthy = health.status == "healthy"
    backend_status = "Running" if backend_is_healthy else "Offline"
    backend_icon = "🟢" if backend_is_healthy else "🔴"

    prediction_status = "Healthy" if backend_is_healthy else "Unavailable"
    prediction_icon = "✅" if backend_is_healthy else "❌"

    model_name = health.model_name if health.model_loaded else "Not Loaded"

    backend_status_card = StatusCard(title="Backend", value=backend_status, icon=backend_icon)
    prediction_status_card = StatusCard(title="Prediction API", value=prediction_status, icon=prediction_icon)

    model_metric_card = MetricCard(title="Model", value=model_name)

    col1, col2 = st.columns(2)

    with col1:
        render_status_card(backend_status_card)
        render_status_card(prediction_status_card)

    with col2:
        render_metric_card(model_metric_card)

    if st.button("Try Prediction"):
        st.session_state.page = "Prediction"
