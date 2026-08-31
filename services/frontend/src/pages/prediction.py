"""ASP Prediction Lab page."""

import streamlit as st

from services.frontend.src.config.features_mapping import (
    FEATURE_MAPS,
    FEATURE_RANGES,
    FEATURES_LABELS,
)
from services.frontend.src.models.prediction_model import PredictionResponse
from services.frontend.src.services.prediction_service import predict


def _mapped_selectbox(
    feature: str,
    *,
    default_value: int | None = None,
) -> int:
    """render a human-readable selectbox and return the API value."""

    mapping = FEATURE_MAPS[feature]
    label = FEATURES_LABELS[feature]

    values = list(mapping.keys())

    if default_value is not None and default_value in values:
        default_index = values.index(default_value)
    else:
        default_index = 0

    selected_value = st.selectbox(
        label,
        options=values,
        index=default_index,
        format_func=lambda value: mapping[value],
        key=f"prediction_{feature}",
    )

    return selected_value


def _number_input(
    feature: str,
    *,
    value: int | float,
    step: int | float = 1,
) -> int | float:
    """render a constrained numeric input using FEATURE_RANGES."""

    label = FEATURES_LABELS[feature]
    min_value, max_value = FEATURE_RANGES[feature]

    return st.number_input(
        label,
        min_value=min_value,
        max_value=max_value,
        value=value,
        step=step,
        key=f"prediction_{feature}",
    )


def _prediction_result_card(result: PredictionResponse) -> None:
    """render the prediction result."""

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
    """render the prediction input form."""

    st.html(
        """
        <div class="asp-card-title">ACCIDENT INFORMATION</div>
        """
    )

    col1, col2 = st.columns(2)

    # ================================================================
    # LEFT COLUMN — VICTIM / VEHICLE
    # ================================================================

    with col1:
        place = _mapped_selectbox(
            "place",
            default_value=1,
        )

        catu = _mapped_selectbox(
            "catu",
            default_value=1,
        )

        sexe = _mapped_selectbox(
            "sexe",
            default_value=1,
        )

        secu1 = _mapped_selectbox(
            "secu1",
            default_value=1,
        )

        victim_age = _number_input(
            "victim_age",
            value=30,
        )

        nb_victim = _number_input(
            "nb_victim",
            value=1,
        )

        catv = _mapped_selectbox(
            "catv",
            default_value=2,
        )

        obsm = _mapped_selectbox(
            "obsm",
            default_value=0,
        )

        motor = _mapped_selectbox(
            "motor",
            default_value=0,
        )

        nb_vehicles = _number_input(
            "nb_vehicles",
            value=1,
        )

        # ============================================================
        # ROAD
        # ============================================================

        catr = _mapped_selectbox(
            "catr",
            default_value=3,
        )

        circ = _mapped_selectbox(
            "circ",
            default_value=2,
        )

        surf = _mapped_selectbox(
            "surf",
            default_value=1,
        )

        situ = _mapped_selectbox(
            "situ",
            default_value=1,
        )

    # ================================================================
    # RIGHT COLUMN — CONDITIONS / LOCATION
    # ================================================================

    with col2:
        vma = _number_input(
            "vma",
            value=50,
        )

        jour = _number_input(
            "jour",
            value=15,
        )

        mois = _number_input(
            "mois",
            value=8,
        )

        lum = _mapped_selectbox(
            "lum",
            default_value=1,
        )

        dep = _number_input(
            "dep",
            value=75,
        )

        com = _number_input(
            "com",
            value=1,
        )

        agg = _mapped_selectbox(
            "agg",
            default_value=1,
        )

        int_value = _mapped_selectbox(
            "int",
            default_value=1,
        )

        atm = _mapped_selectbox(
            "atm",
            default_value=0,
        )

        col = _mapped_selectbox(
            "col",
            default_value=1,
        )

        lat = _number_input(
            "lat",
            value=48.8566,
            step=0.0001,
        )

        longitude = _number_input(
            "long",
            value=2.3522,
            step=0.0001,
        )

        hour = _number_input(
            "hour",
            value=12,
        )

        year_acc = _number_input(
            "year_acc",
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

    # ================================================================
    # AUTHENTICATION
    # ================================================================

    token = st.session_state.get("access_token")

    if not token:
        st.error("Authentication required. Please log in first.")
        return

    # ================================================================
    # API PAYLOAD
    #
    # IMPORTANT:
    # Values returned by mapped selectboxes are the actual API values.
    # Human-readable labels never enter the payload.
    # ================================================================

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
    """render the ASP Prediction Lab."""

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

    # ================================================================
    # INPUT PANEL
    # ================================================================

    with left:
        st.html(
            """
            <div class="asp-card">
                <div class="asp-card-title">PREDICTION INPUT</div>
            """
        )

        _prediction_form()

        st.html("</div>")

    # ================================================================
    # RESULT PANEL
    # ================================================================

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
