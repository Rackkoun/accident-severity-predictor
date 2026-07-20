"""
Evaluation entrypoint
"""

from common.utils.paths import (
    METRIC_DIR,
    MODEL_CONFIG,
    MODEL_DIR,
    PROCESSED_DATA_DIR,
    REPORT_DIR,
)
from services.training.src.evaluate_model import run_evaluation

if __name__ == "__main__":
    run_evaluation(
        model_name=MODEL_CONFIG["model_name"],
        processed_data_dir=PROCESSED_DATA_DIR,
        model_dir=MODEL_DIR,
        metrics_dir=METRIC_DIR,
        reports_dir=REPORT_DIR,
    )
