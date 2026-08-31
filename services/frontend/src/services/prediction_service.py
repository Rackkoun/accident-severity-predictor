"""Frontend prediction service."""

import requests

from common.utils.asp_logging import get_logger
from services.frontend.src.models.prediction_model import PredictionResponse
from services.frontend.src.services.api import api_client

logger = get_logger(__name__)


def predict(payload: dict, token: str) -> PredictionResponse | None:
    """send prediction request to the backend."""

    try:
        response = api_client.post(
            "/predict",
            json=payload,
            token=token,
        )

        response.raise_for_status()

        return PredictionResponse.model_validate(response.json())

    except requests.exceptions.HTTPError as exc:
        logger.error(
            "Prediction request failed with HTTP %s",
            exc.response.status_code if exc.response else "unknown",
        )
        return None

    except requests.exceptions.RequestException as exc:
        logger.error("Prediction request failed: %s", exc)
        return None
