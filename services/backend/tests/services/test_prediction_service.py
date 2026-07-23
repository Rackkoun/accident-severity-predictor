"""
Tests for prediction_service.
"""

import json
from unittest.mock import MagicMock, mock_open, patch

import pytest
from fastapi import HTTPException

from services.backend.src.schemas.prediction import PredictionRequest

# solve situation where latest model is not found in test cache
# AssertionError: assert None == 'model_20260723000000'
# access live model cache as 2nd approach since resetting cache has not worked
from services.backend.src.services import prediction_service
from services.backend.src.services.prediction_service import (
    _latest_feature_path,
    _latest_model_path,
    # _model_cache,  # remove import model cache from the list
    get_model_status,
    load_latest_model,
    predict_accident,
)


@pytest.fixture(autouse=True)
def reset_model_cache() -> None:
    """ensure clean cache state for every test"""
    prediction_service._model_cache.update({"model": None, "features": None, "name": None})


@patch("services.backend.src.services.prediction_service.MODEL_DIR")
def test_latest_model_path_found(mock_dir: MagicMock) -> None:
    """return the most recently modified model file."""

    mock_old = MagicMock()
    mock_old.stat.return_value.st_mtime = 1000
    mock_old.name = "model_20260722000000.joblib"

    mock_new = MagicMock()
    mock_new.stat.return_value.st_mtime = 2000
    mock_new.name = "model_20260723000000.joblib"

    mock_dir.glob.return_value = [mock_old, mock_new]

    result = _latest_model_path(mock_dir, "model")
    assert result.name == "model_20260723000000.joblib"


@patch("services.backend.src.services.prediction_service.MODEL_DIR")
def test_latest_model_path_not_found(mock_dir: MagicMock) -> None:
    """raise FileNotFoundError when no model exists."""

    mock_dir.glob.return_value = []
    with pytest.raises(FileNotFoundError, match="No trained model found"):
        _latest_model_path(mock_dir, "model")


@patch("services.backend.src.services.prediction_service.MODEL_DIR")
def test_latest_feature_path_found(mock_dir: MagicMock) -> None:
    """return the most recently modified features file."""

    mock_old = MagicMock()
    mock_old.stat.return_value.st_mtime = 1000
    mock_old.name = "model_20260722000000_features.json"

    mock_new = MagicMock()
    mock_new.stat.return_value.st_mtime = 2000
    mock_new.name = "model_20260723000000_features.json"

    # ensure mocked glob return the mocked files
    mock_dir.glob.return_value = [mock_old, mock_new]

    result = _latest_feature_path(mock_dir, "model")
    assert result.name == "model_20260723000000_features.json"


@patch("services.backend.src.services.prediction_service.MODEL_DIR")
def test_latest_feature_path_not_found(mock_dir: MagicMock) -> None:
    """raise FileNotFoundError when no features file exists."""

    mock_dir.glob.return_value = []

    with pytest.raises(FileNotFoundError, match="No feature file found"):
        _latest_feature_path(mock_dir, "model")


@patch("services.backend.src.services.prediction_service.MODEL_DIR")
def test_load_no_model(mock_dir: MagicMock) -> None:
    """raise HTTPException(503) when no model is available."""
    mock_dir.glob.return_value = []

    with pytest.raises(HTTPException) as exc_info:
        load_latest_model()

    assert exc_info.value.status_code == 503
    assert "No trained model available" in exc_info.value.detail


@patch("services.backend.src.services.prediction_service.joblib.load")
@patch("services.backend.src.services.prediction_service.MODEL_DIR")
def test_load_success(mock_dir: MagicMock, mock_load: MagicMock) -> None:
    """Successfully load model and features into cache."""

    mock_model = MagicMock()
    mock_model.stat.return_value.st_mtime = 1000
    mock_model.stem = "model_20260723000000"

    mock_feat = MagicMock()
    mock_feat.stat.return_value.st_mtime = 1000

    mock_dir.glob.side_effect = [
        [mock_model],
        [mock_feat],
    ]
    mock_load.return_value = MagicMock()

    with patch("builtins.open", mock_open(read_data=json.dumps(["place", "catu"]))):
        load_latest_model()

    assert prediction_service._model_cache["name"] == "model_20260723000000"
    assert prediction_service._model_cache["features"] == ["place", "catu"]


@pytest.mark.parametrize(
    ("prediction", "proba", "expected_severity", "expected_code", "expected_prob"),
    [
        (1, [0.3, 0.7], "Injured (hospitalized) / Killed", 1, 0.7),
        (0, [0.8, 0.2], "Unharmed / Lightly injured", 0, 0.8),
    ],
)
def test_predict_severity(
    loaded_model_cache: None,
    mock_model: MagicMock,
    valid_payload: dict,
    prediction: int,
    proba: list[float],
    expected_severity: str,
    expected_code: int,
    expected_prob: float,
) -> None:
    """predict severity codes map correctly to labels and probabilities."""
    mock_model.predict.return_value = [prediction]
    mock_model.predict_proba.return_value = [proba]

    request = PredictionRequest(**valid_payload)
    result = predict_accident(request)

    assert result.severity_code == expected_code
    assert result.severity == expected_severity
    assert result.probability == expected_prob
    assert result.model_used == "model_test"


def test_predict_feature_mismatch(loaded_model_cache: None, valid_payload: dict) -> None:
    """raise HTTPException(422) when features don't match the model."""
    prediction_service._model_cache["features"] = ["place", "catu", "sexe", "unknown_feature"]

    request = PredictionRequest(**valid_payload)

    with pytest.raises(HTTPException) as exc_info:
        predict_accident(request)

    assert exc_info.value.status_code == 422
    assert "Feature mismatch" in exc_info.value.detail


@pytest.mark.parametrize(
    ("loaded", "name", "features", "expected_count"),
    [
        (False, None, None, 0),
        (True, "model_2026", ["a", "b", "c"], 3),
    ],
)
def test_model_status(loaded: bool, name: str | None, features: list[str] | None, expected_count: int) -> None:
    """status reflects current cache state."""

    prediction_service._model_cache.update({"model": MagicMock() if loaded else None, "name": name, "features": features})
    status = get_model_status()
    assert status["loaded"] is loaded
    assert status["name"] == name
    assert status["features_count"] == expected_count
