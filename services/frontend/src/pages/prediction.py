"""ASP Prediction Lab page."""

import streamlit as st

from services.frontend.src.models.prediction_model import PredictionResponse
from services.frontend.src.services.prediction_service import predict


def _prediction_result_card(result: PredictionResponse) -> None:
    """Render the prediction result."""

    probability = f"{result.probability * 100:.1f}%" if result.probability is not None else "N/A"

    st.html(
        f"""
        <div class="asp-card asp-prediction-result">
            <div class="asp-card-title">PREDICTION RESULT</div>

            <div class="asp-prediction-severity">
                {result.severity}
            </div>

            <div class="asp-prediction-confidence">
                Confidence: {probability}
            </div>

            <div class="asp-model-details">
                <span>Model</span>
                <strong>{result.model_used}</strong>
            </div>
        </div>
        """
    )


def _prediction_form() -> None:
    """Render the prediction input form."""

    st.html(
        """
        <div class="asp-card-title">ACCIDENT INFORMATION</div>
        """
    )

    col1, col2 = st.columns(2)

    with col1:
        place = st.number_input(
            "Victim position (place)",
            min_value=0,
            step=1,
            value=1,
        )

        catu = st.number_input(
            "Victim category (catu)",
            min_value=0,
            step=1,
            value=1,
        )

        sexe = st.number_input(
            "Sex (sexe)",
            min_value=0,
            step=1,
            value=1,
        )

        secu1 = st.number_input(
            "Safety equipment (secu1)",
            min_value=0,
            step=1,
            value=1,
        )

        victim_age = st.number_input(
            "Victim age",
            min_value=0,
            max_value=120,
            step=1,
            value=30,
        )

        nb_victim = st.number_input(
            "Number of victims",
            min_value=1,
            step=1,
            value=1,
        )

        catv = st.number_input(
            "Vehicle type (catv)",
            min_value=0,
            step=1,
            value=7,
        )

        obsm = st.number_input(
            "Fixed obstacle (obsm)",
            min_value=0,
            step=1,
            value=0,
        )

        motor = st.number_input(
            "Motor type (motor)",
            min_value=0,
            step=1,
            value=0,
        )

        nb_vehicles = st.number_input(
            "Number of vehicles",
            min_value=1,
            step=1,
            value=1,
        )

        catr = st.number_input(
            "Road category (catr)",
            min_value=0,
            step=1,
            value=3,
        )

        circ = st.number_input(
            "Traffic direction (circ)",
            min_value=0,
            step=1,
            value=2,
        )

        surf = st.number_input(
            "Road surface (surf)",
            min_value=0,
            step=1,
            value=1,
        )

        situ = st.number_input(
            "Accident situation (situ)",
            min_value=0,
            step=1,
            value=1,
        )

    with col2:
        vma = st.number_input(
            "Speed limit (vma)",
            min_value=0,
            step=1,
            value=50,
        )

        jour = st.number_input(
            "Day (jour)",
            min_value=1,
            max_value=31,
            step=1,
            value=15,
        )

        mois = st.number_input(
            "Month (mois)",
            min_value=1,
            max_value=12,
            step=1,
            value=8,
        )

        lum = st.number_input(
            "Lighting (lum)",
            min_value=0,
            step=1,
            value=1,
        )

        dep = st.number_input(
            "Department (dep)",
            min_value=0,
            step=1,
            value=75,
        )

        com = st.number_input(
            "Municipality (com)",
            min_value=0,
            step=1,
            value=1,
        )

        agg = st.number_input(
            "Urban area (agg)",
            min_value=0,
            step=1,
            value=1,
        )

        int_value = st.number_input(
            "Intersection (int)",
            min_value=0,
            step=1,
            value=1,
        )

        atm = st.number_input(
            "Weather conditions (atm)",
            min_value=0,
            step=1,
            value=1,
        )

        col = st.number_input(
            "Collision type (col)",
            min_value=0,
            step=1,
            value=1,
        )

        lat = st.number_input(
            "Latitude",
            value=48.8566,
            format="%.6f",
        )

        longitude = st.number_input(
            "Longitude",
            value=2.3522,
            format="%.6f",
        )

        hour = st.number_input(
            "Hour",
            min_value=0,
            max_value=23,
            step=1,
            value=12,
        )

        year_acc = st.number_input(
            "Accident year",
            min_value=2005,
            max_value=2100,
            step=1,
            value=2024,
        )

    st.html("<div style='height: 12px;'></div>")

    predict_clicked = st.button(
        "🔮  Predict Severity",
        use_container_width=True,
        type="primary",
    )

    if not predict_clicked:
        return

    token = st.session_state.get("access_token")

    if not token:
        st.error("Authentication required. Please log in first.")
        return

    payload = {
        "place": place,
        "catu": catu,
        "sexe": sexe,
        "secu1": secu1,
        "year_acc": year_acc,
        "victim_age": victim_age,
        "nb_victim": nb_victim,
        "catv": catv,
        "obsm": obsm,
        "motor": motor,
        "nb_vehicles": nb_vehicles,
        "catr": catr,
        "circ": circ,
        "surf": surf,
        "situ": situ,
        "vma": vma,
        "jour": jour,
        "mois": mois,
        "lum": lum,
        "dep": dep,
        "com": com,
        "agg": agg,
        "int": int_value,
        "atm": atm,
        "col": col,
        "lat": lat,
        "long": longitude,
        "hour": hour,
    }

    with st.spinner("Running prediction..."):
        result = predict(payload, token)

    if result is None:
        st.error("Prediction failed. Please verify the input values and backend availability.")
        return

    st.session_state.prediction_result = result


def prediction_page() -> None:
    """Render the ASP Prediction Lab."""

    st.html(
        """
        <div class="asp-page-header">
            <div>
                <div class="asp-eyebrow">MACHINE LEARNING</div>
                <h1>Prediction Lab</h1>
                <p>
                    Configure accident characteristics and predict
                    road accident severity.
                </p>
            </div>
        </div>
        """
    )

    left, right = st.columns(
        [7, 3],
        gap="large",
    )

    with left:
        st.html(
            """
            <div class="asp-card">
                <div class="asp-card-title">PREDICTION INPUT</div>
            """
        )

        _prediction_form()

        st.html("</div>")

    with right:
        result = st.session_state.get("prediction_result")

        if result is not None:
            _prediction_result_card(result)
        else:
            st.html(
                """
                <div class="asp-card asp-prediction-empty">
                    <div class="asp-card-title">PREDICTION RESULT</div>

                    <div class="asp-prediction-empty-content">
                        <div class="asp-prediction-empty-icon">◎</div>

                        <div class="asp-prediction-empty-title">
                            Ready for prediction
                        </div>

                        <div class="asp-prediction-empty-text">
                            Configure the accident information and
                            click <strong>Predict Severity</strong>.
                        </div>
                    </div>
                </div>
                """
            )
