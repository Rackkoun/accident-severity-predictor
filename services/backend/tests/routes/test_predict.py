"""
Integration tests for backend predict route
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@patch("services.backend.src.routes.predict.predict_accident")
def test_predict_success(mock_predict: MagicMock, client: TestClient, valid_payload: dict) -> None:
    """prediction returns valid response."""
    mock_predict.return_value = MagicMock(
        severity="Injured (hospitalized) / Killed",
        severity_code=1,
        probability=0.85,
        model_used="model_20260723000000",
    )

    response = client.post("/api/v1/predict", json=valid_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["severity_code"] == 1
    assert data["probability"] == 0.85
    assert data["model_used"] == "model_20260723000000"


@pytest.mark.parametrize(
    "bad_payload",
    [
        {},  # empty
        {"invalid": "data"},  # unknown fields
        {"place": 999},  # out of range
    ],
)
def test_predict_validation_error(client: TestClient, bad_payload: dict) -> None:
    """invalid payloads return 422."""
    response = client.post("/api/v1/predict", json=bad_payload)
    assert response.status_code == 422
