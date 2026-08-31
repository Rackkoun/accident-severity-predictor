"""ASP Prediction Lab."""

import streamlit as st

from services.frontend.src.config.features_mapping import (
    FEATURE_MAPS,
    FEATURES_LABELS,
)


def _html(content: str) -> None:
    """render trusted application HTML."""

    st.html(content)


def _section_title(title: str, icon: str) -> None:
    """render a Prediction Lab section title."""

    _html(
        f"""
        <div class="asp-prediction-section-title">
            <span>{icon}</span>
            <span>{title}</span>
        </div>
        """
    )


def _select_mapped_feature(
    feature: str,
    *,
    key: str,
) -> int:
    """render a mapped categorical feature and return its API value."""

    mapping = FEATURE_MAPS[feature]

    values = list(mapping.keys())
    labels = list(mapping.values())

    selected_label = st.selectbox(
        FEATURES_LABELS[feature],
        labels,
        key=key,
    )

    return values[labels.index(selected_label)]


def _render_vehicle_inputs() -> dict:
    """render vehicle and victim inputs."""

    values: dict = {}

    _section_title("Vehicle & Victim", "🚗")

    values["catv"] = _select_mapped_feature(
        "catv",
        key="prediction_catv",
    )

    values["catu"] = _select_mapped_feature(
        "catu",
        key="prediction_catu",
    )

    values["sexe"] = _select_mapped_feature(
        "sexe",
        key="prediction_sexe",
    )

    values["secu1"] = _select_mapped_feature(
        "secu1",
        key="prediction_secu1",
    )

    values["obsm"] = _select_mapped_feature(
        "obsm",
        key="prediction_obsm",
    )

    values["motor"] = _select_mapped_feature(
        "motor",
        key="prediction_motor",
    )

    values["place"] = st.number_input(
        FEATURES_LABELS["place"],
        min_value=1,
        max_value=10,
        value=1,
        step=1,
        key="prediction_place",
    )

    values["victim_age"] = st.number_input(
        FEATURES_LABELS["victim_age"],
        min_value=1.0,
        max_value=120.0,
        value=35.0,
        step=1.0,
        key="prediction_victim_age",
    )

    values["nb_victim"] = st.number_input(
        FEATURES_LABELS["nb_victim"],
        min_value=1,
        max_value=100,
        value=1,
        step=1,
        key="prediction_nb_victim",
    )

    values["nb_vehicles"] = st.number_input(
        FEATURES_LABELS["nb_vehicles"],
        min_value=1,
        max_value=100,
        value=1,
        step=1,
        key="prediction_nb_vehicles",
    )

    return values


def _render_environment_inputs() -> dict:
    """render road and environmental inputs."""

    values: dict = {}

    _section_title("Road & Environment", "🛣️")

    values["catr"] = _select_mapped_feature(
        "catr",
        key="prediction_catr",
    )

    values["circ"] = _select_mapped_feature(
        "circ",
        key="prediction_circ",
    )

    values["surf"] = _select_mapped_feature(
        "surf",
        key="prediction_surf",
    )

    values["situ"] = _select_mapped_feature(
        "situ",
        key="prediction_situ",
    )

    values["lum"] = _select_mapped_feature(
        "lum",
        key="prediction_lum",
    )

    values["agg"] = _select_mapped_feature(
        "agg",
        key="prediction_agg",
    )

    values["int"] = _select_mapped_feature(
        "int",
        key="prediction_int",
    )

    values["atm"] = _select_mapped_feature(
        "atm",
        key="prediction_atm",
    )

    values["col"] = _select_mapped_feature(
        "col",
        key="prediction_col",
    )

    values["vma"] = st.number_input(
        FEATURES_LABELS["vma"],
        min_value=1,
        max_value=130,
        value=50,
        step=1,
        key="prediction_vma",
    )

    return values


def _render_time_location_inputs() -> dict:
    """render temporal and geographic inputs."""

    values: dict = {}

    _section_title("Time & Location", "🕒")

    values["year_acc"] = st.number_input(
        FEATURES_LABELS["year_acc"],
        min_value=2021,
        max_value=2024,
        value=2024,
        step=1,
        key="prediction_year_acc",
    )

    values["jour"] = st.number_input(
        FEATURES_LABELS["jour"],
        min_value=1,
        max_value=31,
        value=15,
        step=1,
        key="prediction_jour",
    )

    values["mois"] = st.number_input(
        FEATURES_LABELS["mois"],
        min_value=1,
        max_value=12,
        value=6,
        step=1,
        key="prediction_mois",
    )

    values["hour"] = st.number_input(
        FEATURES_LABELS["hour"],
        min_value=0,
        max_value=23,
        value=14,
        step=1,
        key="prediction_hour",
    )

    values["dep"] = st.number_input(
        FEATURES_LABELS["dep"],
        min_value=1,
        max_value=976,
        value=75,
        step=1,
        key="prediction_dep",
    )

    values["com"] = st.number_input(
        FEATURES_LABELS["com"],
        min_value=1,
        max_value=99999,
        value=101,
        step=1,
        key="prediction_com",
    )

    values["lat"] = st.number_input(
        FEATURES_LABELS["lat"],
        min_value=41.0,
        max_value=51.0,
        value=48.8566,
        step=0.0001,
        format="%.4f",
        key="prediction_lat",
    )

    values["long"] = st.number_input(
        FEATURES_LABELS["long"],
        min_value=-5.0,
        max_value=10.0,
        value=2.3522,
        step=0.0001,
        format="%.4f",
        key="prediction_long",
    )

    return values


def _render_result_placeholder() -> None:
    """render empty prediction result."""

    _html(
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
        """
    )


def _render_probability_placeholder() -> None:
    """render probability placeholder."""

    _html(
        """
        <div class="asp-prediction-result-card">

            <div class="asp-card-title">
                CLASS PROBABILITIES
            </div>

            <div class="asp-placeholder-message">
                Probability visualization will appear after the
                prediction API is connected.
            </div>

        </div>
        """
    )


def _render_factors_placeholder() -> None:
    """render feature importance placeholder."""

    _html(
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
        """
    )


def prediction_page() -> None:
    """render the ASP Prediction Lab."""

    _html(
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
        """
    )

    results_column, input_column = st.columns(
        [7, 3],
        gap="medium",
    )

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

        _html(
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
            """
        )

    with input_column:
        _html(
            """
            <div class="asp-input-panel-title">
                ACCIDENT CONDITIONS
            </div>
            """
        )

        with st.form("prediction_form"):
            vehicle_values = _render_vehicle_inputs()

            environment_values = _render_environment_inputs()

            time_location_values = _render_time_location_inputs()

            _html('<div class="asp-form-divider"></div>')

            submitted = st.form_submit_button(
                "🔍  Predict Severity",
                use_container_width=True,
            )

        if submitted:
            collected_values = {
                **vehicle_values,
                **environment_values,
                **time_location_values,
            }

            st.session_state.prediction_draft = collected_values

            st.info("Prediction API integration is the next step. The selected values have been collected without changing their API representation.")
