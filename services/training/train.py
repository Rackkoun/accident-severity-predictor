"""
training entrypoint
"""
from services.training.src.train_model import run_training
from common.utils.paths import (
    MODEL_CONFIG,
    MODEL_DIR,
    REPORT_DIR,
    PROCESSED_DATA_DIR,
)

if __name__ == "__main__":
    run_training(
        processed_data_dir=PROCESSED_DATA_DIR,
        model_out_dir=MODEL_DIR,
        reports_dir=REPORT_DIR,
        model_name=MODEL_CONFIG["model_name"],
        model_parameters=MODEL_CONFIG["model_parameters"],
        top_n_features=MODEL_CONFIG["top_n_features"]
    )