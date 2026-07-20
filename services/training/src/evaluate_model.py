"""
evaluate model
"""

import json
from pathlib import Path
 
import joblib
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
)

from common.utils.logging import get_logger
from common.data.dataset_io import load_processed_csv

logger = get_logger(__name__)
 
def run_evaluation(
        model_name: str,
        processed_data_dir: str | Path,
        model_dir: str | Path,
        metrics_dir: str | Path,
        reports_dir: str | Path,
    ) -> dict:
    """evaluate a trained model on the test set and save metrics + confusion matrix. Return the metrics dict."""

    model_path = Path(model_dir) / f"{model_name}.joblib"
    logger.info(f"Loading model: {model_path}")
    if not model_path.exists():
        raise FileNotFoundError(f"No trained model found at '{model_path}'")
    model = joblib.load(model_path)
 
    processed_data_dir = Path(processed_data_dir)

    logger.info("Loading test dataset...")
    X_test = load_processed_csv(processed_data_dir / "X_test.csv")
    y_test = load_processed_csv(processed_data_dir / "y_test.csv").squeeze()
 
    logger.info("Running predictions...")
    y_pred = model.predict(X_test)
 
    metrics = {
        "Model": model_name,
        "Accuracy": accuracy_score(y_test, y_pred),
        "Precision": precision_score(y_test, y_pred),
        "Recall": recall_score(y_test, y_pred),
        "F1 Score": f1_score(y_test, y_pred),
    }
 
    metrics_path = Path(metrics_dir) / f"{model_name}_metrics.json"

    logger.info("Saving metrics...")
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=4)
 
    fig, ax = plt.subplots(figsize=(6, 6))
    ConfusionMatrixDisplay.from_predictions(
        y_test, y_pred, cmap="Blues", normalize="true", ax=ax, colorbar=False,
    )
    plt.tight_layout()
 
    confusion_matrix_path = Path(reports_dir) / f"{model_name}_confusion_matrix.png"
    
    logger.info("Generating confusion matrix...")
    plt.savefig(confusion_matrix_path, dpi=300)
    plt.close(fig)
 
    logger.info("Evaluation completed.")
    return metrics