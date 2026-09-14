"""
Tests for prediction_service.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from services.backend.src.core.metrics import REGISTRY
from services.backend.src.schemas.prediction import PredictionRequest
from services.backend.src.services import prediction_service
from services.backend.src.services.prediction_service import (
    _coerce_parse,
    get_model_info,
    get_model_status,
    load_model,
    predict_accident,
)

# ---------------------------------------------------------------------------
# _coerce_parse
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ('{"a": 1}', {"a": 1}),
        ("[1, 2, 3]", [1, 2, 3]),
        ("42", 42),
        ("3.14", 3.14),
        ("true", True),
        ("null", None),
        ("1e-3", 0.001),
    ],
)
def test_coerce_parse_valid_json(raw: str, expected: object) -> None:
    """Valid JSON strings are deserialized to their Python equivalent."""
    assert _coerce_parse(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "not-json",
        "{broken",
        "  ",
        "[1, 2",
        "{'a': 1}",
    ],
)
def test_coerce_parse_invalid_json_returns_original(raw: str) -> None:
    """Strings that are not valid JSON are returned unchanged."""
    assert _coerce_parse(raw) == raw


# ---------------------------------------------------------------------------
# get_model_info
# ---------------------------------------------------------------------------


def _make_run(
    params: dict[str, str] | None = None,
    metrics: dict[str, str] | None = None,
    start_time_ms: int = 1_700_000_000_000,
):
    run = MagicMock()
    run.info.start_time = start_time_ms
    run.data.params = params or {}
    run.data.metrics = metrics or {}
    return run


@pytest.mark.usefixtures("loaded_model_cache")
def test_get_model_info(
    mock_features: list[str],
) -> None:
    """Return full model metadata when a model is cached and MLflow is reachable."""
    prediction_service._model_cache["run_id"] = "run-123"
    prediction_service._model_cache["version"] = "7"
    prediction_service._model_cache["features"] = ["place", "catu"]

    # mock model with feature_importances_
    prediction_service._model_cache["model"].feature_importances_ = [0.6, 0.4]

    mock_run = _make_run(
        params={"n_estimators": "100", "max_depth": "5"},
        metrics={"accuracy": "0.91"},
    )

    with patch("services.backend.src.services.prediction_service.MlflowClient") as client_cls:
        client_cls.return_value.get_run.return_value = mock_run
        info = get_model_info()

    assert info["registry_name"] == "accident-severity-predictor"
    assert info["alias"] == "production"
    assert info["version"] == "7"
    assert info["dataset"] == "BAAC 2005-2024 (FR)"
    assert info["features_count"] == 2
    assert info["parameters"] == {"n_estimators": 100, "max_depth": 5}
    assert info["metrics"] == {"accuracy": 0.91}
    assert info["feature_importance"] == {"place": 0.6, "catu": 0.4}

    # trained_at should be a valid ISO timestamp
    dt = datetime.fromisoformat(info["trained_at"])
    assert dt.tzinfo is not None


@pytest.mark.usefixtures("loaded_model_cache")
def test_get_model_info_no_feature_importances() -> None:
    """feature_importance is empty when the model lacks feature_importances_."""
    prediction_service._model_cache["run_id"] = "run-123"
    prediction_service._model_cache["version"] = "7"
    del prediction_service._model_cache["model"].feature_importances_

    mock_run = _make_run()

    with patch("services.backend.src.services.prediction_service.MlflowClient") as client_cls:
        client_cls.return_value.get_run.return_value = mock_run
        info = get_model_info()

    assert info["feature_importance"] == {}


@pytest.mark.usefixtures("loaded_model_cache")
def test_get_model_info_feature_importance_length_mismatch() -> None:
    """feature_importance is empty when importances length ≠ features length."""
    prediction_service._model_cache["run_id"] = "run-123"
    prediction_service._model_cache["version"] = "7"
    prediction_service._model_cache["model"].feature_importances_ = [0.5]
    # 2 features vs 1 importance → no match
    prediction_service._model_cache["features"] = ["place", "catu"]

    mock_run = _make_run()

    with patch("services.backend.src.services.prediction_service.MlflowClient") as client_cls:
        client_cls.return_value.get_run.return_value = mock_run
        info = get_model_info()

    assert info["feature_importance"] == {}


def test_get_model_info_no_run_id() -> None:
    """HTTPException(503) when run_id is not set in the cache."""
    prediction_service._model_cache.update(
        {
            "model": MagicMock(),
            "run_id": None,
        }
    )

    with pytest.raises(HTTPException) as exc_info:
        get_model_info()

    assert exc_info.value.status_code == 503
    assert "run metadata" in exc_info.value.detail.lower()


@patch("services.backend.src.services.prediction_service.load_model")
def test_get_model_info_lazy_load(
    mock_load_model: MagicMock,
) -> None:
    """load_model() is called when the cache is empty."""
    prediction_service._model_cache.update(
        {
            "model": None,
            "features": ["place"],
            "name": "loaded",
            "alias": "production",
            "version": "1",
            "run_id": "run-001",
        }
    )

    mock_load_model.return_value = None

    mock_run = _make_run()

    with patch("services.backend.src.services.prediction_service.MlflowClient") as client_cls:
        client_cls.return_value.get_run.return_value = mock_run
        get_model_info()

    mock_load_model.assert_called_once()


def test_get_model_info_mlflow_client_failure() -> None:
    """HTTPException(503) when MlflowClient.get_run raises."""
    prediction_service._model_cache.update(
        {
            "model": MagicMock(),
            "run_id": "run-123",
        }
    )

    with patch("services.backend.src.services.prediction_service.MlflowClient") as client_cls:
        client_cls.return_value.get_run.side_effect = RuntimeError("connection refused")

        with pytest.raises(HTTPException) as exc_info:
            get_model_info()

    assert exc_info.value.status_code == 503
    assert "Unable to retrieve model metadata" in exc_info.value.detail
    assert "connection refused" in exc_info.value.detail


@pytest.fixture(autouse=True)
def reset_model_cache() -> None:
    """Ensure a clean model cache before every test."""

    prediction_service._model_cache.update(
        {
            "model": None,
            "features": None,
            "name": None,
            "alias": None,
        }
    )


def _metric_value(name: str, labels: dict[str, str]) -> float:
    """Return a Prometheus metric value, or zero if it does not exist yet."""

    value = REGISTRY.get_sample_value(name, labels)
    return value if value is not None else 0.0


def _histogram_count(name: str, labels: dict[str, str]) -> float:
    """Return the number of observations recorded by a Prometheus histogram."""

    value = REGISTRY.get_sample_value(f"{name}_count", labels)
    return value if value is not None else 0.0


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

    model_name = "accident-severity-predictor@production (v7)"

    before = _metric_value(
        "model_loaded",
        {
            "model_version": model_name,
            "alias": "production",
        },
    )

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
    assert prediction_service._model_cache["name"] == model_name
    assert prediction_service._model_cache["alias"] == "production"

    after = _metric_value(
        "model_loaded",
        {
            "model_version": model_name,
            "alias": "production",
        },
    )

    assert after == 1
    assert after >= before


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

    before = _metric_value(
        "model_loaded",
        {
            "model_version": "none",
            "alias": "production",
        },
    )

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

    after = _metric_value(
        "model_loaded",
        {
            "model_version": "none",
            "alias": "production",
        },
    )

    assert after == 0
    assert after == before


# ---------------------------------------------------------------------------
# predict_accident
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    (
        "prediction",
        "proba",
        "expected_severity",
        "expected_code",
        "expected_prob",
    ),
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


@pytest.mark.usefixtures("loaded_model_cache")
def test_predict_records_prometheus_metrics(
    mock_model: MagicMock,
    valid_payload: dict,
) -> None:
    """A prediction increments and observes the corresponding Prometheus metrics."""

    model_name = "accident-severity-predictor@production (v7)"
    severity_code = "1"

    mock_model.predict.return_value = [1]
    mock_model.predict_proba.return_value = [[0.3, 0.7]]

    predictions_before = _metric_value(
        "predictions_total",
        {
            "severity_code": severity_code,
            "model_version": model_name,
        },
    )

    duration_before = _histogram_count(
        "prediction_duration_seconds",
        {
            "model_version": model_name,
        },
    )

    confidence_before = _histogram_count(
        "prediction_confidence",
        {
            "model_version": model_name,
        },
    )

    request = PredictionRequest(**valid_payload)

    result = predict_accident(request)

    assert result.severity_code == 1
    assert result.probability == 0.7

    predictions_after = _metric_value(
        "predictions_total",
        {
            "severity_code": severity_code,
            "model_version": model_name,
        },
    )

    duration_after = _histogram_count(
        "prediction_duration_seconds",
        {
            "model_version": model_name,
        },
    )

    confidence_after = _histogram_count(
        "prediction_confidence",
        {
            "model_version": model_name,
        },
    )

    assert predictions_after == predictions_before + 1
    assert duration_after == duration_before + 1
    assert confidence_after == confidence_before + 1


@pytest.mark.usefixtures("loaded_model_cache")
def test_predict_records_correct_prediction_metric_label(
    mock_model: MagicMock,
    valid_payload: dict,
) -> None:
    """predictions_total uses the actual predicted severity code as a label."""

    model_name = "accident-severity-predictor@production (v7)"

    mock_model.predict.return_value = [0]
    mock_model.predict_proba.return_value = [[0.8, 0.2]]

    code_zero_before = _metric_value(
        "predictions_total",
        {
            "severity_code": "0",
            "model_version": model_name,
        },
    )

    code_one_before = _metric_value(
        "predictions_total",
        {
            "severity_code": "1",
            "model_version": model_name,
        },
    )

    request = PredictionRequest(**valid_payload)

    result = predict_accident(request)

    assert result.severity_code == 0

    code_zero_after = _metric_value(
        "predictions_total",
        {
            "severity_code": "0",
            "model_version": model_name,
        },
    )

    code_one_after = _metric_value(
        "predictions_total",
        {
            "severity_code": "1",
            "model_version": model_name,
        },
    )

    assert code_zero_after == code_zero_before + 1
    assert code_one_after == code_one_before


@pytest.mark.usefixtures("loaded_model_cache")
def test_predict_without_predict_proba_does_not_record_confidence(
    mock_model: MagicMock,
    valid_payload: dict,
) -> None:
    """Models without predict_proba return no probability and don't observe confidence."""

    model_name = "accident-severity-predictor@production (v7)"

    mock_model.predict.return_value = [1]

    # MagicMock normally reports arbitrary attributes as existing, so explicitly
    # remove predict_proba for this test.
    del mock_model.predict_proba

    confidence_before = _histogram_count(
        "prediction_confidence",
        {
            "model_version": model_name,
        },
    )

    request = PredictionRequest(**valid_payload)

    result = predict_accident(request)

    assert result.severity_code == 1
    assert result.probability is None

    confidence_after = _histogram_count(
        "prediction_confidence",
        {
            "model_version": model_name,
        },
    )

    assert confidence_after == confidence_before


@patch("services.backend.src.services.prediction_service.load_model")
def test_predict_lazy_load(
    mock_load_model: MagicMock,
    valid_payload: dict,
) -> None:
    """predict_accident lazily loads a model when none is cached."""

    model = MagicMock()
    model.predict.return_value = [0]
    model.predict_proba.return_value = [[0.9, 0.1]]
    model.classes_ = [0, 1]

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
