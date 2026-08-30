"""ASP Prediction Lab."""

import streamlit as st

from services.frontend.src.config.features_mapping import (
    FEATURE_MAPS,
    FEATURES_LABELS,
)


def _section_title(title: str, icon: str) -> None:
    """Render a Prediction Lab section title."""

    st.html(
        f"""
        <div class="asp-prediction-section-title">
            <span>{icon}</span>
            <span>{title}</span>
        </div>
        """,
    )


def _mapping_pending(feature: str) -> None:
    """Render a disabled placeholder for an unmapped feature."""

    label = FEATURES_LABELS.get(feature, feature)

    st.selectbox(
        label,
        options=["Mapping pending"],
        disabled=True,
        key=f"prediction_pending_{feature}",
        help=(f"Value mapping for '{feature}' is not implemented yet. No domain value is invented by the frontend."),
    )


def _render_vehicle_inputs() -> dict:
    """Render currently available vehicle-related inputs."""

    values: dict = {}

    _section_title("Vehicle & Victim", "🚗")

    # ------------------------------------------------------------
    # Vehicle category
    # ------------------------------------------------------------

    if "catv" in FEATURE_MAPS:
        options = FEATURE_MAPS["catv"]
        labels = list(options.values())
        codes = list(options.keys())

        selected = st.selectbox(
            FEATURES_LABELS["catv"],
            labels,
            key="prediction_catv",
        )

        values["catv"] = codes[labels.index(selected)]

    else:
        _mapping_pending("catv")

    # ------------------------------------------------------------
    # Road user
    # ------------------------------------------------------------

    options = FEATURE_MAPS["catu"]
    labels = list(options.values())
    codes = list(options.keys())

    selected = st.selectbox(
        FEATURES_LABELS["catu"],
        labels,
        key="prediction_catu",
    )

    values["catu"] = codes[labels.index(selected)]

    # ------------------------------------------------------------
    # Sex
    # ------------------------------------------------------------

    options = FEATURE_MAPS["sexe"]
    labels = list(options.values())
    codes = list(options.keys())

    selected = st.selectbox(
        FEATURES_LABELS["sexe"],
        labels,
        key="prediction_sexe",
    )

    values["sexe"] = codes[labels.index(selected)]

    # ------------------------------------------------------------
    # Remaining vehicle/victim mappings
    # ------------------------------------------------------------

    for feature in (
        "place",
        "secu1",
        "victim_age",
        "nb_victim",
        "obsm",
        "motor",
        "nb_vehicles",
    ):
        if feature not in FEATURE_MAPS:
            _mapping_pending(feature)

    return values


def _render_environment_inputs() -> dict:
    """Render currently available environment inputs."""

    values: dict = {}

    _section_title("Road & Environment", "🛣️")

    # ------------------------------------------------------------
    # Weather
    # ------------------------------------------------------------

    options = FEATURE_MAPS["atm"]
    labels = list(options.values())
    codes = list(options.keys())

    selected = st.selectbox(
        FEATURES_LABELS["atm"],
        labels,
        key="prediction_atm",
    )

    values["atm"] = codes[labels.index(selected)]

    # ------------------------------------------------------------
    # Features waiting for domain mappings
    # ------------------------------------------------------------

    for feature in (
        "catr",
        "circ",
        "surf",
        "situ",
        "lum",
        "agg",
        "int",
        "col",
    ):
        if feature not in FEATURE_MAPS:
            _mapping_pending(feature)

    return values


def _render_time_inputs() -> dict:
    """Render temporal prediction inputs."""

    values: dict = {}

    _section_title("Time & Location", "🕒")

    for feature in (
        "year_acc",
        "jour",
        "mois",
        "hour",
        "dep",
        "com",
        "lat",
        "long",
    ):
        if feature not in FEATURE_MAPS:
            _mapping_pending(feature)

    return values


def _render_result_placeholder() -> None:
    """Render the initial prediction result area."""

    st.html(
        """
        <div class="asp-prediction-result-card">

            <div class="asp-card-title">
                PREDICTED SEVERITY
            </div>

            <div class="asp-prediction-empty">

                <div class="asp-prediction-empty-icon">
                    ✦
                </div>

                <div class="asp-prediction-empty-title">
                    Ready for prediction
                </div>

                <div class="asp-prediction-empty-text">
                    Configure the accident conditions and run the
                    prediction to see the severity and confidence.
                </div>

            </div>

        </div>
        """,
    )


def _render_probability_placeholder() -> None:
    """Render probability placeholder."""

    st.html(
        """
        <div class="asp-prediction-result-card">

            <div class="asp-card-title">
                CLASS PROBABILITIES
            </div>

            <div class="asp-placeholder-message">
                Probability visualization will appear after
                the prediction API is connected.
            </div>

        </div>
        """,
    )


def _render_factors_placeholder() -> None:
    """Render feature importance placeholder."""

    st.html(
        """
        <div class="asp-prediction-result-card">

            <div class="asp-card-title">
                KEY FACTORS
            </div>

            <div class="asp-placeholder-message">
                Feature importance will be displayed here once
                prediction/explainability data is available.
            </div>

        </div>
        """,
    )


def prediction_page() -> None:
    """Render the ASP Prediction Lab."""

    st.html(
        """
        <div class="asp-page-header">

            <div class="asp-eyebrow">
                AI PREDICTION
            </div>

            <h1>
                Prediction Lab
            </h1>

            <p>
                Configure accident conditions and get an AI-powered
                severity prediction.
            </p>

        </div>
        """,
    )

    # ------------------------------------------------------------
    # Mapping warning
    # ------------------------------------------------------------

    st.warning(
        "Some BAAC feature value mappings are still being completed. "
        "Unmapped fields are intentionally disabled and no domain "
        "values are invented by the frontend."
    )

    # ------------------------------------------------------------
    # Main layout
    # ------------------------------------------------------------

    results_column, input_column = st.columns(
        [7, 3],
        gap="medium",
    )

    # ------------------------------------------------------------
    # RESULTS
    # ------------------------------------------------------------

    with results_column:
        _render_result_placeholder()

        probability_column, factors_column = st.columns(
            [1, 1],
            gap="medium",
        )

        with probability_column:
            _render_probability_placeholder()

        with factors_column:
            _render_factors_placeholder()

        st.html(
            """
            <div class="asp-prediction-result-card asp-explanation-card">

                <div class="asp-card-title">
                    AI EXPLANATION
                </div>

                <div class="asp-placeholder-message">
                    The LLM explanation will be connected after the
                    prediction API and result payload are implemented.
                </div>

            </div>
            """,
        )

    # ------------------------------------------------------------
    # INPUT FORM
    # ------------------------------------------------------------

    with input_column:
        st.html(
            """
            <div class="asp-input-panel-title">
                ACCIDENT CONDITIONS
            </div>
            """,
        )

        with st.form("prediction_form"):
            vehicle_values = _render_vehicle_inputs()

            environment_values = _render_environment_inputs()

            time_values = _render_time_inputs()

            st.html(
                '<div class="asp-form-divider"></div>',
            )

            submitted = st.form_submit_button(
                "🔍  Predict Severity",
            )

        if submitted:
            collected_values = {
                **vehicle_values,
                **environment_values,
                **time_values,
            }

            st.info(
                "Prediction is not submitted yet. "
                "The API integration will be implemented in the "
                "next step after the remaining feature mappings "
                "are completed."
            )

            st.session_state.prediction_draft = collected_values
