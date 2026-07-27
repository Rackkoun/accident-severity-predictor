"""
Backend prediction endpoint
"""

from fastapi import APIRouter

from services.backend.src.schemas.prediction import PredictionRequest, PredictionResponse
from services.backend.src.services.prediction_service import predict_accident

router = APIRouter(prefix="/api/v1", tags=["Prediction"])


@router.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest) -> PredictionResponse:
    """
    predict accident severity from input features.

    Requires a trained model to be available in artifacts/models/.
    """
    return predict_accident(request)
