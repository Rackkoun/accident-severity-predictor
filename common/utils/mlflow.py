"""
mlflow tracking setup & run logging
"""

from typing import Any

import dagshub
import mlflow

from common.utils.asp_logging import get_logger

logger = get_logger(__name__)


def setup_mlflow(
    experiment_name: str = "asp-training",
) -> None:
    """setup mlflow for dagshub."""

    logger.info("Initializing DagsHub MLflow tracking...")
    dagshub.init(
        repo_owner="Rackkoun",
        repo_name="accident-severity-predictor",
        mlflow=True,
    )

    logger.info(f"Using MLflow experiment '{experiment_name}'")
    mlflow.set_experiment(experiment_name)


def log_run(
    train_out: dict[str, Any],
    eval_out: dict[str, Any],
) -> None:
    """log trainining and evaluation outputs."""

    logger.info("Logging parameters, metrics and artifacts to MLflow...")

    mlflow.set_tag("model_name", train_out["model_name"])
    mlflow.log_params(train_out["parameters"])
    mlflow.log_metrics(eval_out["metrics"])
    for path in train_out["artifacts"].values():
        mlflow.log_artifact(path)
    for path in eval_out["artifacts"].values():
        mlflow.log_artifact(path)

    logger.info("MLflow logging completed.")
