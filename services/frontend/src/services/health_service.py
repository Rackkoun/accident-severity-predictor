"""
frontend api health check
"""

from services.frontend.src.models.health_model import HealthResponse
from services.frontend.src.services.api import api_client


def get_health() -> HealthResponse:

    response = api_client.get("/health")
    response.raise_for_status()

    return HealthResponse.model_validate(response.json())
