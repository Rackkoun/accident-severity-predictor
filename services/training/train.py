"""
training entrypoint
"""
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
    run_training(
        processed_data_dir=PROCESSED_DATA_DIR,
        model_out_dir=MODEL_DIR,
        reports_dir=REPORT_DIR,
        model_name=MODEL_CONFIG["model_name"],
        model_parameters=MODEL_CONFIG["model_parameters"],
        top_n_features=MODEL_CONFIG["top_n_features"]
    )

    # eval is used here for docker entrypoint
    run_evaluation(
        model_name=MODEL_CONFIG["model_name"],
        processed_data_dir=PROCESSED_DATA_DIR,
        model_dir=MODEL_DIR,
        metrics_dir=METRIC_DIR,
        reports_dir=REPORT_DIR,
    )
if __name__ == "__main__":
    main()


