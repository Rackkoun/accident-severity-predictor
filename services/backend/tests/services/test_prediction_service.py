"""
Tests for prediction_service.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from services.backend.src.schemas.prediction import PredictionRequest
from services.backend.src.services import prediction_service
from services.backend.src.services.prediction_service import (
    get_model_status,
    load_model,
    predict_accident,
)


@pytest.fixture(autouse=True)
def reset_model_cache() -> None:
    """Ensure a clean cache before every test."""

    prediction_service._model_cache.update(
        {
            "model": None,
            "features": None,
            "name": None,
            "alias": None,
        }
    )


# ---------------------------------------------------------------------------
# load_model
# ---------------------------------------------------------------------------


@patch("services.backend.src.services.prediction_service.load_registered_model")
@patch("services.backend.src.services.prediction_service.setup_mlflow")
def test_load_model_success(
    mock_setup_mlflow: MagicMock,
    mock_load_registered_model: MagicMock,
) -> None:
    """Successfully load a registered model into the cache."""

    mock_model = MagicMock()

    mock_load_registered_model.return_value = {
        "model": mock_model,
        "features": ["place", "catu"],
        "version": "7",
        "run_id": "run-123",
    }

    load_model()

    mock_setup_mlflow.assert_called_once()

    mock_load_registered_model.assert_called_once_with(
        registry_model_name="accident-severity-predictor",
        alias="production",
    )

    assert prediction_service._model_cache["model"] is mock_model
    assert prediction_service._model_cache["features"] == [
        "place",
        "catu",
    ]
    assert prediction_service._model_cache["name"] == "accident-severity-predictor@production (v7)"
    assert prediction_service._model_cache["alias"] == "production"


@patch("services.backend.src.services.prediction_service.load_registered_model")
@patch("services.backend.src.services.prediction_service.setup_mlflow")
def test_load_model_skips_cached_model(
    mock_setup_mlflow: MagicMock,
    mock_load_registered_model: MagicMock,
) -> None:
    """Loading is skipped when the requested alias is already cached."""

    prediction_service._model_cache.update(
        {
            "model": MagicMock(),
            "features": ["place"],
            "name": "cached",
            "alias": "production",
        }
    )

    load_model()

    mock_setup_mlflow.assert_not_called()
    mock_load_registered_model.assert_not_called()


@patch("services.backend.src.services.prediction_service.load_registered_model")
@patch("services.backend.src.services.prediction_service.setup_mlflow")
def test_load_model_force_reload(
    mock_setup_mlflow: MagicMock,
    mock_load_registered_model: MagicMock,
) -> None:
    """force_reload=True ignores the cache."""

    prediction_service._model_cache.update(
        {
            "model": MagicMock(),
            "features": ["place"],
            "name": "cached",
            "alias": "production",
        }
    )

    mock_load_registered_model.return_value = {
        "model": MagicMock(),
        "features": ["place"],
        "version": "8",
        "run_id": "run-456",
    }

    load_model(force_reload=True)

    mock_setup_mlflow.assert_called_once()
    mock_load_registered_model.assert_called_once()


@patch("services.backend.src.services.prediction_service.load_registered_model")
@patch("services.backend.src.services.prediction_service.setup_mlflow")
def test_load_model_failure(
    mock_setup_mlflow: MagicMock,
    mock_load_registered_model: MagicMock,
) -> None:
    """Any loading failure is translated into HTTPException(503)."""

    mock_load_registered_model.side_effect = RuntimeError("MLflow unavailable")

    with pytest.raises(HTTPException) as exc_info:
        load_model()

    assert exc_info.value.status_code == 503

    assert prediction_service._model_cache == {
        "model": None,
        "features": None,
        "name": None,
        "alias": None,
        "version": None,
        "run_id": None,
    }


# ---------------------------------------------------------------------------
# predict_accident
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("prediction", "proba", "expected_severity", "expected_code", "expected_prob"),
    [
        (1, [0.3, 0.7], "Injured (hospitalized) / Killed", 1, 0.7),
        (0, [0.8, 0.2], "Unharmed / Lightly injured", 0, 0.8),
    ],
)
@pytest.mark.usefixtures("loaded_model_cache")
def test_predict_severity(
    mock_model: MagicMock,
    valid_payload: dict,
    prediction: int,
    proba: list[float],
    expected_severity: str,
    expected_code: int,
    expected_prob: float,
) -> None:
    """Prediction output is mapped correctly."""

    mock_model.predict.return_value = [prediction]
    mock_model.predict_proba.return_value = [proba]

    request = PredictionRequest(**valid_payload)

    result = predict_accident(request)

    assert result.severity_code == expected_code
    assert result.severity == expected_severity
    assert result.probability == expected_prob


@patch("services.backend.src.services.prediction_service.load_model")
def test_predict_lazy_load(
    mock_load_model: MagicMock,
    valid_payload: dict,
) -> None:
    """
    predict_accident lazily loads a model when none is cached.
    """

    model = MagicMock()
    model.predict.return_value = [0]
    model.predict_proba.return_value = [[0.9, 0.1]]

    mock_load_model.side_effect = lambda: prediction_service._model_cache.update(
        {
            "model": model,
            "features": list(valid_payload.keys()),
            "name": "loaded",
            "alias": "production",
        }
    )

    request = PredictionRequest(**valid_payload)

    predict_accident(request)

    mock_load_model.assert_called_once()


@pytest.mark.usefixtures("loaded_model_cache")
def test_predict_feature_mismatch(
    valid_payload: dict,
) -> None:
    """A feature mismatch results in HTTPException(422)."""

    prediction_service._model_cache["features"] = [
        "place",
        "catu",
        "sexe",
        "unknown_feature",
    ]

    request = PredictionRequest(**valid_payload)

    with pytest.raises(HTTPException) as exc_info:
        predict_accident(request)

    assert exc_info.value.status_code == 422
    assert "Feature mismatch" in exc_info.value.detail


# ---------------------------------------------------------------------------
# get_model_status
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("loaded", "name", "alias", "features", "expected_count"),
    [
        (False, None, None, None, 0),
        (
            True,
            "accident-severity-predictor@production (v7)",
            "production",
            ["a", "b", "c"],
            3,
        ),
    ],
)
def test_model_status(
    loaded: bool,
    name: str | None,
    alias: str | None,
    features: list[str] | None,
    expected_count: int,
) -> None:
    """Status reflects the current cache contents."""

    prediction_service._model_cache.update(
        {
            "model": MagicMock() if loaded else None,
            "name": name,
            "alias": alias,
            "features": features,
        }
    )

    status = get_model_status()

    assert status["loaded"] is loaded
    assert status["name"] == name
    assert status["alias"] == alias
    assert status["features_count"] == expected_count
