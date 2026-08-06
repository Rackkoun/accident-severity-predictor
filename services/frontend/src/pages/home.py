"""
ASP home page.
"""

import streamlit as st


def home_page() -> None:

    st.title("🚗 Accident Severity Predictor")
    st.markdown("---")
    st.header("AI-powered Road Accident Severity Prediction")
    st.info("Welcome to the ASP plateform. \n\nUse the sidebar to navigate through the application")
