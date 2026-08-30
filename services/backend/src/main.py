"""
Backend service entrypoint with model lifecycle management.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from common.utils.asp_logging import get_logger
from services.backend.src.routes import auth, health, model_info, predict, reload, train
from services.backend.src.services.prediction_service import load_model

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[Any]:
    """load latest model on startup if available."""
    try:
        load_model()
    except Exception as e:
        logger.exception(f"Unable to load model at startup: {e}")
    yield
    logger.info("Shutting down backend...")


app = FastAPI(
    title="Accident Severity Predictor API",
    description="""
    ML API for predicting French road accident severity (BAAC dataset).

    Endpoints:
    - **POST /api/v1/login** — Authenticate and get access token
    - **POST /api/v1/train** — Trigger model training (launches Docker container)
    - **POST /api/v1/predict** — Predict severity from accident features
    - **POST /api/v1/model/reload** — Reload the current 'production' model (used after retraining promotes a new champion)
    - **GET /api/v1/health** — Check service and model status
    - **GET /api/v1/model/info** – Get current production model metadata
    """,
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(health.router)
app.include_router(train.router)
app.include_router(predict.router)
app.include_router(reload.router)
app.include_router(model_info.router)


@app.get("/")
async def root() -> dict:
    return {
        "message": "Accident Severity Predictor API",
        "docs": "/docs",
        "auth": "/api/v1/login",
        "health": "/api/v1/health",
        "train": "/api/v1/train",
        "predict": "/api/v1/predict",
        "reload": "/api/v1/model/reload",
    }
