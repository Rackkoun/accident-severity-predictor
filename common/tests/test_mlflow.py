"""
Tests for mlflow helpers.
"""

from pathlib import Path
from unittest.mock import call, patch

from common.utils.mlflow import log_run, setup_mlflow


@patch("common.utils.mlflow.mlflow.set_experiment")
@patch("common.utils.mlflow.dagshub.init")
def test_setup_mlflow(
    mock_dagshub_init,
    mock_set_experiment,
) -> None:
    """setup_mlflow initializes DagsHub and selects the experiment."""

    setup_mlflow()

    mock_dagshub_init.assert_called_once_with(
        repo_owner="Rackkoun",
        repo_name="accident-severity-predictor",
        mlflow=True,
    )

    mock_set_experiment.assert_called_once_with("asp-training")


@patch("common.utils.mlflow.mlflow.log_artifact")
@patch("common.utils.mlflow.mlflow.log_metrics")
@patch("common.utils.mlflow.mlflow.log_params")
@patch("common.utils.mlflow.mlflow.set_tag")
def test_log_run(
    mock_set_tag,
    mock_log_params,
    mock_log_metrics,
    mock_log_artifact,
) -> None:
    """log_run logs tags, parameters, metrics and artifacts."""

    train_out = {
        "model_name": "rf_20260730153000",
        "parameters": {
            "n_estimators": 100,
            "max_depth": 10,
        },
        "artifacts": {
            "model": Path("artifacts/models/model.joblib"),
            "features": Path("artifacts/models/features.json"),
            "parameters": Path("artifacts/models/parameters.json"),
            "feature_importance": Path("artifacts/reports/feature_importance.png"),
        },
    }

    eval_out = {
        "metrics": {
            "accuracy": 0.95,
            "precision": 0.94,
            "recall": 0.93,
            "f1_score": 0.94,
        },
        "artifacts": {
            "metrics": Path("artifacts/metrics/metrics.json"),
            "confusion_matrix": Path("artifacts/reports/confusion_matrix.png"),
        },
    }

    log_run(train_out, eval_out)

    mock_set_tag.assert_called_once_with(
        "model_name",
        "rf_20260730153000",
    )

    mock_log_params.assert_called_once_with(
        train_out["parameters"],
    )

    mock_log_metrics.assert_called_once_with(
        eval_out["metrics"],
    )

    assert mock_log_artifact.call_count == 6

    mock_log_artifact.assert_has_calls(
        [
            call(Path("artifacts/models/model.joblib")),
            call(Path("artifacts/models/features.json")),
            call(Path("artifacts/models/parameters.json")),
            call(Path("artifacts/reports/feature_importance.png")),
            call(Path("artifacts/metrics/metrics.json")),
            call(Path("artifacts/reports/confusion_matrix.png")),
        ],
        any_order=False,
    )
