"""
evaluate model
"""

import json
from pathlib import Path

import joblib
import matplotlib
import matplotlib.pyplot as plt
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
)

from common.data.dataset_io import load_processed_csv
from common.utils.asp_logging import get_logger

matplotlib.use("Agg")

logger = get_logger(__name__)


def _latest_model_path(model_dir: Path, model_name: str) -> Path:
    """Find the latest model file matching model_name or model_name_*.joblib."""
    model_dir = Path(model_dir)

    # Exact match first
    exact = model_dir / f"{model_name}.joblib"
    if exact.exists():
        return exact

    # Look for versioned models: model_name_*.joblib
    pattern = f"{model_name}_*.joblib"
    files = list(model_dir.glob(pattern))

    if not files:
        raise FileNotFoundError(
            f"No trained model found for '{model_name}' in '{model_dir}'"
        )

    # Sort by modification time (most recent first)
    latest = max(files, key=lambda p: p.stat().st_mtime)
    return latest


def run_evaluation(
        model_name: str,
        processed_data_dir: str | Path,
        model_dir: str | Path,
        metrics_dir: str | Path,
        reports_dir: str | Path,
    ) -> dict:
    """evaluate a trained model on the test set and save metrics + confusion matrix. Return the metrics dict."""

    model_dir = Path(model_dir)
    model_path = _latest_model_path(model_dir, model_name)

    logger.info(f"Loading model: {model_path}")
    model = joblib.load(model_path)


    # Extract actual model name from filename for outputs
    actual_model_name = model_path.stem
    processed_data_dir = Path(processed_data_dir)

    logger.info("Loading test dataset...")
    X_test = load_processed_csv(processed_data_dir / "X_test.csv")
    y_test = load_processed_csv(processed_data_dir / "y_test.csv").squeeze()

    logger.info("Running predictions...")
    y_pred = model.predict(X_test)

    metrics = {
        "Model": actual_model_name,
        "Accuracy": accuracy_score(y_test, y_pred),
        "Precision": precision_score(y_test, y_pred),
        "Recall": recall_score(y_test, y_pred),
        "F1 Score": f1_score(y_test, y_pred),
    }

    metrics_path = Path(metrics_dir) / f"{actual_model_name}_metrics.json"

    logger.info("Saving metrics...")
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=4)

    fig, ax = plt.subplots(figsize=(6, 6))
    ConfusionMatrixDisplay.from_predictions(
        y_test, y_pred, cmap="Blues", normalize="true", ax=ax, colorbar=False,
    )
    plt.tight_layout()

    confusion_matrix_path = Path(reports_dir) / f"{actual_model_name}_confusion_matrix.png"

    logger.info("Generating confusion matrix...")
    plt.savefig(confusion_matrix_path, dpi=300)
    plt.close(fig)

    logger.info("Evaluation completed.")
    return metrics
