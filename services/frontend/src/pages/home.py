"""
ASP home page.
"""

import streamlit as st

from services.frontend.src.components.metric_card import metric_card
from services.frontend.src.components.status_card import status_card


def home_page() -> None:

    st.title("🚗 Accident Severity Predictor")
    st.markdown("---")
    st.header("AI-powered Road Accident Severity Prediction")
    st.info("Welcome to the ASP plateform. \n\nUse the sidebar to navigate through the application")

    col1, col2 = st.columns(2)

    with col1:
        status_card("Backend", "Running", "🟢")
        status_card("Prediction API", "Healthy", "✅")

    with col2:
        metric_card("Model", "Random Forest")
        metric_card("Accuracy", "80.47 %")
