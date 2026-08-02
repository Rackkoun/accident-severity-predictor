"""
mlflow tracking setup, run logging & model registry
"""

from typing import Any, cast

import dagshub
import mlflow
from mlflow import MlflowClient
from mlflow.entities.model_registry import ModelVersion

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
) -> mlflow.models.model.ModelInfo:
    """log training and evaluation outputs, including the model artifact."""

    logger.info("Logging parameters, metrics and artifacts to MLflow...")

    mlflow.set_tag("model_name", train_out["model_name"])
    mlflow.log_params(train_out["parameters"])
    mlflow.log_metrics(eval_out["metrics"])

    for key, path in train_out["artifacts"].items():
        if key == "model" or key == "parameters":
            continue
        mlflow.log_artifact(path)
    for path in eval_out["artifacts"].values():
        mlflow.log_artifact(path)

    model_info = cast(
        mlflow.models.model.ModelInfo,
        mlflow.sklearn.log_model(
            sk_model=train_out["model"],
            artifact_path="model",
            input_example=train_out["input_example"],
        ),
    )

    logger.info("MLflow logging completed.")
    return model_info


def register_model(
    model_info: mlflow.models.model.ModelInfo,
    registry_model_name: str = "accident-severity-predictor",
) -> ModelVersion:
    """register an already-logged model in the MLflow Model Registry."""

    logger.info(f"Registering model at '{model_info.model_uri}' as '{registry_model_name}'...")

    registered_version = mlflow.register_model(
        model_uri=model_info.model_uri,
        name=registry_model_name,
    )

    logger.info(f"Model registered as '{registry_model_name}' version {registered_version.version}.")
    return registered_version


def promote_if_better(
    registered_version: ModelVersion,
    eval_out: dict[str, Any],
    registry_model_name: str = "accident-severity-predictor",
    metric_name: str = "f1_score",
    alias: str = "production",
    higher_is_better: bool = True,
) -> bool:
    """
    Compare the newly registered model version against the current
    production version (by alias) on a given metric, and promote it
    if it performs better. Returns True if promotion happened.
    """

    logger.info("Comparing new model version against current production version...")

    client = MlflowClient()
    new_metric = float(eval_out["metrics"][metric_name])

    try:
        current_prod = client.get_model_version_by_alias(registry_model_name, alias)
    except mlflow.exceptions.MlflowException:
        current_prod = None

    if current_prod is None:
        logger.info(f"No current '{alias}' version found for '{registry_model_name}'. Promoting version {registered_version.version} by default.")
        client.set_registered_model_alias(registry_model_name, alias, registered_version.version)
        return True

    # pull the metric from the run that produced the current production version
    current_run = client.get_run(current_prod.run_id)
    current_metric = current_run.data.metrics.get(metric_name)

    if current_metric is None:
        logger.warning(
            f"Current '{alias}' version (v{current_prod.version}) has no '{metric_name}' logged. Skipping comparison, keeping it in place."
        )
        return False
    current_metric = float(current_metric)

    is_better = new_metric > current_metric if higher_is_better else new_metric < current_metric

    logger.info(
        f"Comparing new version {registered_version.version} ({metric_name}={new_metric:.4f}) "
        f"against current '{alias}' version {current_prod.version} ({metric_name}={current_metric:.4f})"
    )

    if is_better:
        client.set_registered_model_alias(registry_model_name, alias, registered_version.version)
        logger.info(
            f"Version {registered_version.version} outperforms current '{alias}' ({new_metric:.4f} vs {current_metric:.4f}). Promoted to '{alias}'."
        )
    else:
        logger.info(
            f"Version {registered_version.version} does not outperform current '{alias}' "
            f"({new_metric:.4f} vs {current_metric:.4f}). Keeping current version."
        )

    return is_better
