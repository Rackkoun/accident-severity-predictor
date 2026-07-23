"""
Shared fixtures for backend tests
"""

from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from services.backend.src.main import app
from services.backend.src.services import prediction_service


@pytest.fixture(autouse=True)
def reset_cache() -> Iterator[None]:
    """reset global model cache before every test to avoid state leakage."""
    prediction_service._model_cache.update({"model": None, "features": None, "name": None})
    yield


@pytest.fixture
def client() -> TestClient:
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture
def mock_model() -> MagicMock:
    """mocked sklearn model with predict/prodict_proba"""
    model = MagicMock()
    model.predict.return_value = [1]
    model.predict_proba.return_value = [[0.3, 0.7]]

    return model


@pytest.fixture
def mock_features() -> list[str]:
    """sample feature list matching the trained model."""
    return [
        "id_usager",
        "place",
        "catu",
        "sexe",
        "secu1",
        "year_acc",
        "victim_age",
        "nb_victim",
        "catv",
        "obsm",
        "motor",
        "nb_vehicles",
        "catr",
        "circ",
        "surf",
        "situ",
        "vma",
        "jour",
        "mois",
        "lum",
        "dep",
        "com",
        "agg",
        "int",
        "atm",
        "col",
        "lat",
        "long",
        "hour",
    ]


@pytest.fixture
def loaded_model_cache(mock_model: MagicMock, mock_features: list[str]) -> Iterator[None]:
    """Fixture that loads a mock model into the global cache."""
    prediction_service._model_cache.update(
        {
            "model": mock_model,
            "features": mock_features,
            "name": "model_test",
        }
    )
    yield


@pytest.fixture
def valid_payload() -> dict:
    """valid prediction request payload."""
    return {
        "place": 1,
        "catu": 1,
        "sexe": 1,
        "secu1": 1,
        "year_acc": 2023,
        "victim_age": 30.0,
        "nb_victim": 1,
        "catv": 2,
        "obsm": 0,
        "motor": 1,
        "nb_vehicles": 1,
        "catr": 1,
        "circ": 1,
        "surf": 1,
        "situ": 1,
        "vma": 50,
        "jour": 1,
        "mois": 1,
        "lum": 1,
        "dep": 75,
        "com": 101,
        "agg": 1,
        "int": 1,
        "atm": 0,
        "col": 1,
        "lat": 48.85,
        "long": 2.35,
        "hour": 14,
    }


@pytest.fixture
def severe_payload() -> dict:
    """payload simulating a severe accident (night, highway, bad weather)."""
    return {
        "place": 10,
        "catu": 1,
        "sexe": 1,
        "secu1": 0,
        "year_acc": 2024,
        "victim_age": 45.0,
        "nb_victim": 3,
        "catv": 4,
        "obsm": 2,
        "motor": 3,
        "nb_vehicles": 2,
        "catr": 3,
        "circ": 4,
        "surf": 2,
        "situ": 2,
        "vma": 130,
        "jour": 15,
        "mois": 12,
        "lum": 4,
        "dep": 13,
        "com": 13001,
        "agg": 2,
        "int": 3,
        "atm": 1,
        "col": 6,
        "lat": 43.3,
        "long": 5.4,
        "hour": 2,
    }


@pytest.fixture
def light_payload() -> dict:
    """payload simulating a light accident (day, city, good weather, bike)."""
    return {
        "place": 1,
        "catu": 3,
        "sexe": 2,
        "secu1": 2,
        "year_acc": 2025,
        "victim_age": 25.0,
        "nb_victim": 1,
        "catv": 1,
        "obsm": 0,
        "motor": 1,
        "nb_vehicles": 1,
        "catr": 1,
        "circ": 2,
        "surf": 1,
        "situ": 1,
        "vma": 30,
        "jour": 20,
        "mois": 6,
        "lum": 1,
        "dep": 75,
        "com": 75056,
        "agg": 2,
        "int": 1,
        "atm": 0,
        "col": 1,
        "lat": 48.86,
        "long": 2.35,
        "hour": 14,
    }
