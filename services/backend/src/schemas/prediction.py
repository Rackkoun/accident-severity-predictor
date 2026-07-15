from pydantic import BaseModel
from typing import Dict

class PredictionRequest(BaseModel):
    """Prediction features for the ML accident model"""

    atm: int
    surf: int
    lum: int
    infra: int
    situ: int
    plan: int
    catr: int
    agg: int
    vma: int
    hour: int
    mois: int
    age: int
    age_unknown: int

    catv: str

    col: int
    has_safety_equipment: int
    obsm: int
    choc: int
    manv: int


class PredictionResponse(BaseModel):
    """Prediction response"""
    prediction: int
    prediction_name: str
    confidence: float
    probabilities: Dict[str, float]