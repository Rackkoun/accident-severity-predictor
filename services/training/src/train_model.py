"""
Model training
"""
import json
from pathlib import Path
 
import joblib
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from common.utils.logging import get_logger
from common.data.dataset_io import load_processed_csv

from datetime import datetime

logger = get_logger(__name__)

def run_training(
        processed_data_dir: str | Path,
        model_out_dir: str | Path,
        reports_dir: str | Path,
        model_name: str,
        model_parameters: dict,
        top_n_features: int = 20,
        overwrite: bool = False,
    ) -> RandomForestClassifier:
    """train the RandomForest (params from the notebook benchmark) and save artifacts. Return the model."""

    processed_data_dir = Path(processed_data_dir)

    logger.info("Loading processed training dataset...")
    X_train = load_processed_csv(processed_data_dir / "X_train.csv")
    y_train = load_processed_csv(processed_data_dir / "y_train.csv").squeeze()
 
    model = RandomForestClassifier(**model_parameters)

    logger.info("Training RandomForest model...")
    model.fit(X_train, y_train)
 
    logger.info("Saving model artifacts...")
    save_model_artifacts(
        model=model,
        features=list(X_train.columns),
        model_parameters=model_parameters,
        reports_dir=reports_dir,
        model_out_dir=model_out_dir,
        model_name=model_name,
        top_n_features=top_n_features,
        overwrite=overwrite,
    )

    logger.info("Training completed.")
    return model
 
 
def save_model_artifacts(
        model: RandomForestClassifier,
        features: list[str],
        model_parameters: dict,
        model_out_dir: str | Path,
        reports_dir: str | Path,
        model_name: str,
        top_n_features: int = 20,
        overwrite: bool = False,
    ) -> dict[str, Path]:
    """save model, features list, parameters and a feature-importance plot. Return the output paths."""
    
    model_out_dir = Path(model_out_dir)
    reports_dir = Path(reports_dir)
    
    model_out_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    model_path = model_out_dir / f"{model_name}.joblib"
    features_path = model_out_dir / f"{model_name}_features.json"
    params_path = model_out_dir / f"{model_name}_parameters.json"
    importance_path = reports_dir / f"{model_name}_feature_importance.png"
 
    # au lieu de throw une erreur. le premier model est saved avec model.joblib
    # les autres model seraient saved avec suivant la logique model_timestamp.joblib e.g. model_202607201802.joblib
    if model_path.exists() and not overwrite:
        raise FileExistsError(
            f"Model '{model_name}' already exists at '{model_path}'. Use overwrite=True to replace it."
        )
    
    logger.info(f"Saving model: {model_path}")
    joblib.dump(model, model_path)
 
    logger.info(f"Saving features: {features_path}")
    with open(features_path, "w") as f:
        json.dump(features, f, indent=4)
 
    with open(params_path, "w") as f:
        json.dump(model_parameters, f, indent=4)
 
    feature_importance = (
        pd.Series(model.feature_importances_, index=features)
        .sort_values(ascending=False)
        .head(top_n_features)
        .sort_values(ascending=True)
    )
    fig, ax = plt.subplots(figsize=(8, max(4, len(feature_importance) * 0.3)))
    feature_importance.plot.barh(ax=ax)
    ax.set_title(f"{model_name} - Feature Importance")
    ax.set_xlabel("Importance")
    plt.tight_layout()

    logger.info(f"Saving feature importance plot: {importance_path}")
    plt.savefig(importance_path, dpi=300)
    plt.close(fig)
 
    return {
        "model": model_path,
        "features": features_path,
        "parameters": params_path,
        "feature_importance": importance_path,
    }