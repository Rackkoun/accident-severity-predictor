"""
Tests for mlflow helpers.
"""

from pathlib import Path
from unittest.mock import MagicMock, call, patch

from mlflow.exceptions import MlflowException

from common.utils.mlflow import (
    log_run,
    promote_if_better,
    register_model,
    setup_mlflow,
)


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


@patch("mlflow.sklearn.log_model")
@patch("common.utils.mlflow.mlflow.log_artifact")
@patch("common.utils.mlflow.mlflow.log_metrics")
@patch("common.utils.mlflow.mlflow.log_params")
@patch("common.utils.mlflow.mlflow.set_tag")
def test_log_run(
    mock_set_tag,
    mock_log_params,
    mock_log_metrics,
    mock_log_artifact,
    mock_log_model,
) -> None:
    """log_run logs tags, parameters, metrics, non-model artifacts, and the model itself."""

    mock_model = MagicMock()
    mock_input_example = MagicMock()
    mock_model_info = MagicMock()
    mock_log_model.return_value = mock_model_info

    train_out = {
        "model": mock_model,
        "model_name": "rf_20260730153000",
        "parameters": {
            "n_estimators": 100,
            "max_depth": 10,
        },
        "artifacts": {
            "model": Path("artifacts/models/model.joblib"),
            "parameters": Path("artifacts/models/parameters.json"),
            "features": Path("artifacts/models/features.json"),
            "feature_importance": Path("artifacts/reports/feature_importance.png"),
        },
        "input_example": mock_input_example,
    }

    eval_out = {
        "metrics": {
            "accuracy": 0.95,
            "precision": 0.94,
            "recall": 0.93,
            "f1_score": 0.94,
        },
        "artifacts": {
            "confusion_matrix": Path("artifacts/reports/confusion_matrix.png"),
        },
    }

    result = log_run(train_out, eval_out)

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

    # "model" and "parameters" keys in train_out["artifacts"] are skipped
    # (the model is logged separately below), so only "features" and
    # "feature_importance" are logged here, plus the single eval artifact.
    assert mock_log_artifact.call_count == 3

    mock_log_artifact.assert_has_calls(
        [
            call(Path("artifacts/models/features.json")),
            call(Path("artifacts/reports/feature_importance.png")),
            call(Path("artifacts/reports/confusion_matrix.png")),
        ],
        any_order=False,
    )

    mock_log_model.assert_called_once_with(
        sk_model=mock_model,
        artifact_path="model",
        input_example=mock_input_example,
    )

    assert result is mock_model_info


@patch("common.utils.mlflow.mlflow.register_model")
def test_register_model(mock_register_model) -> None:
    """register_model registers the logged model under the default registry name."""

    mock_model_info = MagicMock()
    mock_model_info.model_uri = "runs:/abc123/model"

    mock_registered_version = MagicMock()
    mock_registered_version.version = "3"
    mock_register_model.return_value = mock_registered_version

    result = register_model(mock_model_info)

    mock_register_model.assert_called_once_with(
        model_uri="runs:/abc123/model",
        name="accident-severity-predictor",
    )

    assert result is mock_registered_version


@patch("common.utils.mlflow.mlflow.register_model")
def test_register_model_custom_name(mock_register_model) -> None:
    """register_model respects a custom registry_model_name."""

    mock_model_info = MagicMock()
    mock_model_info.model_uri = "runs:/abc123/model"

    result = register_model(mock_model_info, registry_model_name="custom-model")

    mock_register_model.assert_called_once_with(
        model_uri="runs:/abc123/model",
        name="custom-model",
    )

    assert result is mock_register_model.return_value


@patch("common.utils.mlflow.MlflowClient")
def test_promote_if_better_no_current_production(mock_mlflow_client_cls) -> None:
    """promote_if_better promotes by default when no production version exists yet."""

    mock_client = MagicMock()
    mock_mlflow_client_cls.return_value = mock_client
    mock_client.get_model_version_by_alias.side_effect = MlflowException("not found")

    registered_version = MagicMock()
    registered_version.version = "1"

    eval_out = {"metrics": {"f1_score": 0.9}}

    result = promote_if_better(registered_version, eval_out)

    assert result is True
    mock_client.get_model_version_by_alias.assert_called_once_with(
        "accident-severity-predictor",
        "production",
    )
    mock_client.set_registered_model_alias.assert_called_once_with(
        "accident-severity-predictor",
        "production",
        "1",
    )


@patch("common.utils.mlflow.MlflowClient")
def test_promote_if_better_new_version_is_better(mock_mlflow_client_cls) -> None:
    """promote_if_better promotes the new version when it outperforms production."""

    mock_client = MagicMock()
    mock_mlflow_client_cls.return_value = mock_client

    current_prod = MagicMock()
    current_prod.version = "2"
    current_prod.run_id = "run-2"
    mock_client.get_model_version_by_alias.return_value = current_prod

    current_run = MagicMock()
    current_run.data.metrics = {"f1_score": 0.85}
    mock_client.get_run.return_value = current_run

    registered_version = MagicMock()
    registered_version.version = "3"

    eval_out = {"metrics": {"f1_score": 0.9}}

    result = promote_if_better(registered_version, eval_out)

    assert result is True
    mock_client.get_run.assert_called_once_with("run-2")
    mock_client.set_registered_model_alias.assert_called_once_with(
        "accident-severity-predictor",
        "production",
        "3",
    )


@patch("common.utils.mlflow.MlflowClient")
def test_promote_if_better_new_version_is_worse(mock_mlflow_client_cls) -> None:
    """promote_if_better keeps the current production version when the new one underperforms."""

    mock_client = MagicMock()
    mock_mlflow_client_cls.return_value = mock_client

    current_prod = MagicMock()
    current_prod.version = "2"
    current_prod.run_id = "run-2"
    mock_client.get_model_version_by_alias.return_value = current_prod

    current_run = MagicMock()
    current_run.data.metrics = {"f1_score": 0.95}
    mock_client.get_run.return_value = current_run

    registered_version = MagicMock()
    registered_version.version = "3"

    eval_out = {"metrics": {"f1_score": 0.9}}

    result = promote_if_better(registered_version, eval_out)

    assert result is False
    mock_client.set_registered_model_alias.assert_not_called()


@patch("common.utils.mlflow.MlflowClient")
def test_promote_if_better_missing_current_metric(mock_mlflow_client_cls) -> None:
    """promote_if_better keeps the current version when it has no metric logged for comparison."""

    mock_client = MagicMock()
    mock_mlflow_client_cls.return_value = mock_client

    current_prod = MagicMock()
    current_prod.version = "2"
    current_prod.run_id = "run-2"
    mock_client.get_model_version_by_alias.return_value = current_prod

    current_run = MagicMock()
    current_run.data.metrics = {}
    mock_client.get_run.return_value = current_run

    registered_version = MagicMock()
    registered_version.version = "3"

    eval_out = {"metrics": {"f1_score": 0.9}}

    result = promote_if_better(registered_version, eval_out)

    assert result is False
    mock_client.set_registered_model_alias.assert_not_called()


@patch("common.utils.mlflow.MlflowClient")
def test_promote_if_better_lower_is_better(mock_mlflow_client_cls) -> None:
    """promote_if_better honors higher_is_better=False for metrics where lower is better (e.g. log_loss)."""

    mock_client = MagicMock()
    mock_mlflow_client_cls.return_value = mock_client

    current_prod = MagicMock()
    current_prod.version = "2"
    current_prod.run_id = "run-2"
    mock_client.get_model_version_by_alias.return_value = current_prod

    current_run = MagicMock()
    current_run.data.metrics = {"log_loss": 0.5}
    mock_client.get_run.return_value = current_run

    registered_version = MagicMock()
    registered_version.version = "3"

    eval_out = {"metrics": {"log_loss": 0.3}}

    result = promote_if_better(
        registered_version,
        eval_out,
        metric_name="log_loss",
        higher_is_better=False,
    )

    assert result is True
    mock_client.set_registered_model_alias.assert_called_once_with(
        "accident-severity-predictor",
        "production",
        "3",
    )
