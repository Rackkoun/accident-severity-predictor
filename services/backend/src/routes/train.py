"""
Backend training endpoint.

Triggers the training container asynchronously via BackgroundTasks.
"""

import os

from fastapi import APIRouter, BackgroundTasks

from services.backend.src.schemas.training import TrainRequest, TrainResponse
from services.backend.src.services.prediction_service import load_latest_model
from services.backend.src.services.training_service import run_training_container

router = APIRouter(prefix="/api/v1", tags=["Training"])

# host paths for Docker volume mounts - must be visible to the Docker daemon
HOST_DATA_DIR = os.getenv("HOST_DATA_DIR", "/app/data")
HOST_ARTIFACTS_DIR = os.getenv("HOST_ARTIFACTS_DIR", "/app/artifacts")


@router.post("/train", response_model=TrainResponse)
def train(
    request: TrainRequest,
    background_tasks: BackgroundTasks,
) -> TrainResponse:
    """Trigger model training in a background Docker container.

    The training container is launched asynchronously. It reads
    preprocessed data from data/processed/ and writes artifacts
    (model, metrics, plots) to artifacts/.

    After training completes, the latest model is reloaded into memory.
    """
    background_tasks.add_task(
        _train_and_reload,
        model_name=request.model_name,
    )

    return TrainResponse(
        status="started",
        model_name=request.model_name,
        message="Training container launched in background. Check logs for progress.",
    )


def _train_and_reload(model_name: str) -> None:
    """Internal helper: run training then reload model."""
    try:
        run_training_container(
            model_name=model_name,
            host_data_dir=HOST_DATA_DIR,
            host_artifacts_dir=HOST_ARTIFACTS_DIR,
        )
        # reload the newly trained model
        load_latest_model(force_reload=True)
    except RuntimeError:
        # logged already in training_service
        pass
