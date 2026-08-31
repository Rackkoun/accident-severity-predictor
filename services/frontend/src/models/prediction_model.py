"""Prediction API response models."""

from pydantic import BaseModel


class PredictionResponse(BaseModel):
    """prediction result returned by the backend."""

    severity: str
    severity_code: int
    probability: float | None = None
    model_used: str
