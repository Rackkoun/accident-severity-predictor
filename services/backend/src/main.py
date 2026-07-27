"""
Backend service entrypoint with model lifecycle management.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from common.utils.asp_logging import get_logger
from services.backend.src.routes import health, predict, train
from services.backend.src.services.prediction_service import load_latest_model

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[Any]:
    """load latest model on startup if available."""
    try:
        load_latest_model()
    except Exception:
        logger.warning("No model available at startup. Use /api/v1/train to train one.")
    yield
    logger.info("Shutting down backend...")


app = FastAPI(
    title="Accident Severity Predictor API",
    description="""
    ML API for predicting French road accident severity (BAAC dataset).

    Endpoints:
    - **POST /api/v1/train** — Trigger model training (launches Docker container)
    - **POST /api/v1/predict** — Predict severity from accident features
    - **GET /api/v1/health** — Check service and model status
    """,
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(train.router)
app.include_router(predict.router)


@app.get("/")
async def root() -> dict:
    return {
        "message": "Accident Severity Predictor API",
        "docs": "/docs",
        "health": "/api/v1/health",
        "train": "/api/v1/train",
        "predict": "/api/v1/predict",
    }
