"""
Model evaluation script
"""

from pathlib import Path
import joblib
import json

import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score
)
from sklearn.metrics import ConfusionMatrixDisplay


def run_evaluation(
        model_name: str | Path,
        processed_data_dir: str | Path = "./data/processed",
        model_dir: str | Path = ".artifacts/models/",
        metrics_dir: str | Path = "./artifacts/metrics",
        reports_dir: str | Path = "./artifacts/reports"
        ) -> None:
    """Run the evaluation and save results to metrics dir"""

    # Load model 
    model_path = Path(model_dir) / f"{model_name}.joblib"
    model = joblib.load(model_path)

    # Load data
    processed_data_dir = Path(processed_data_dir)
    X_test = pd.read_csv(processed_data_dir / "X_test.csv")
    y_test = pd.read_csv(processed_data_dir / "y_test.csv")

    # Run prediction
    y_pred = model.predict(X_test)

    # Get metrics
    metrics = {
        "Model": model_name,
        "Accuracy": accuracy_score(y_test, y_pred),
        "Precision": precision_score(y_test, y_pred),
        "Recall": recall_score(y_test, y_pred),
        "F1 Score": f1_score(y_test, y_pred),
    }

    # Save metrics
    metrics_dir = Path(metrics_dir)
    metrics_path = metrics_dir / f"{model_name}_metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=4)

    # Get confusion matrix
    fig, ax = plt.subplots(figsize=(6, 6))
    ConfusionMatrixDisplay.from_predictions(
        y_test,
        y_pred,
        cmap="Blues",
        normalize="true",
        ax=ax,
        colorbar=False,
    )
    plt.tight_layout()

    # Save confusion matrix
    reports_dir = Path(reports_dir)
    confusion_matrix_path = reports_dir / f"{model_name}_confusion_matrix.png"
    plt.savefig(confusion_matrix_path, dpi=300)
    plt.close(fig)

    print("Evaluation finished.")
    print(f"Saved metrics at '{metrics_path}'")
    print(f"Saved confusion matrix at '{confusion_matrix_path}'")
