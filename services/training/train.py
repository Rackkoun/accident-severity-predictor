"""
training entrypoint
"""

import mlflow

from common.utils.mlflow import (
    log_run,
    promote_if_better,
    register_model,
    setup_mlflow,
)
from common.utils.paths import (
    METRIC_DIR,
    MODEL_CONFIG,
    MODEL_DIR,
    PROCESSED_DATA_DIR,
    REPORT_DIR,
)
from services.training.src.evaluate_model import run_evaluation
from services.training.src.train_model import run_training


def main() -> None:

    setup_mlflow()

    with mlflow.start_run():
        train_out = run_training(
            processed_data_dir=PROCESSED_DATA_DIR,
            model_out_dir=MODEL_DIR,
            reports_dir=REPORT_DIR,
            model_name=MODEL_CONFIG["model_name"],
            model_parameters=MODEL_CONFIG["model_parameters"],
            top_n_features=MODEL_CONFIG["top_n_features"],
        )

        # eval is used here for docker entrypoint
        eval_out = run_evaluation(
            model_name=MODEL_CONFIG["model_name"],
            processed_data_dir=PROCESSED_DATA_DIR,
            model_dir=MODEL_DIR,
            metrics_dir=METRIC_DIR,
            reports_dir=REPORT_DIR,
        )

        # mlflow: log run -> register model -> promote model if better
        model_info = log_run(train_out, eval_out)
        registered_version = register_model(model_info)
        promote_if_better(registered_version, eval_out)


if __name__ == "__main__":
    main()
