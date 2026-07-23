"""
Training schema backend API
"""

from pydantic import BaseModel


class TrainRequest(BaseModel):
    """Request body for training trigger."""

    model_name: str = "model"


class TrainResponse(BaseModel):
    """Training result."""

    status: str
    model_name: str
    message: str
