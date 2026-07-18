"""
Model training script
"""

from pathlib import Path
import joblib
import json

import pandas as pd 
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier


def run_training(
        processed_data_dir: str | Path = "./data/processed",
        model_out_dir: str | Path = "./artifacts/models",
        model_parameters: dict | None = None,
        reports_dir: str | Path = "./artifacts/reports"
        ) -> None:
    """Run the training and save model to output dir"""

    # Get training data
    processed_data_dir = Path(processed_data_dir)
    X_train = pd.read_csv(processed_data_dir / "X_train.csv")
    y_train = pd.read_csv(processed_data_dir / "y_train.csv").squeeze()

    # Define model
    model =  RandomForestClassifier(
                **model_parameters,
                n_jobs=-1,
            )

    # Train model
    model.fit(X_train, y_train)

    # Save model
    save_model_artifacts(
        model=model, 
        features=list(X_train.columns), 
        model_parameters=model_parameters,
        reports_dir=reports_dir,
        model_out_dir=model_out_dir)


def save_model_artifacts(
        model: RandomForestClassifier,
        features: list[str],
        model_parameters: dict | None = None,
        reports_dir: str | Path = "./artifacts/reports",
        model_out_dir: str | Path = "./artifacts/models",
        ) -> None:
    """Save model, features and feature importance."""

    # Specify model name
    model_name = "model"
    model_out_dir = Path(model_out_dir)
    model_path = model_out_dir / f"{model_name}.joblib"  
    
    while model_path.exists():
        print(f"Model with name '{model_name}' already exists under '{model_out_dir}'.")
        model_name = input("Choose another name: ")
        model_path = model_out_dir / f"{model_name}.joblib" 
    
    # Save model
    joblib.dump(model, model_path)

    # Save features
    features_path = model_out_dir / f"{model_name}_features.json"
    with open(features_path, "w") as f:
        json.dump(features, f, indent=4)

    # Save model paramaters
    params_path = model_out_dir / f"{model_name}_parameters.json"
    with open(params_path, "w") as f:
        json.dump(model_parameters, f, indent=4)

    # Get feature importance
    top_n = 20
    feature_importance = (
        pd.Series(model.feature_importances_, index=features)
        .sort_values(ascending=False)
        .head(top_n)
        .sort_values(ascending=True)
    )
    fig, ax = plt.subplots(figsize=(8, max(4, len(feature_importance) * 0.3)))
    feature_importance.plot.barh(ax=ax)
    ax.set_title(f"{model_name} - Feature Importance")
    ax.set_xlabel("Importance")
    plt.tight_layout()

    # Save feature importance fig
    reports_dir = Path(reports_dir)
    importance_path = reports_dir / f"{model_name}_feature_importance.png"
    plt.savefig(importance_path, dpi=300)
    plt.close(fig)

    print("Model trained successfully.")
    print(f"Saved model at '{model_path}'")
    print(f"Saved features at '{features_path}'")
    print(f"Saved parameters at '{params_path}'")
    print(f"Saved feature importance fig at '{importance_path}'")