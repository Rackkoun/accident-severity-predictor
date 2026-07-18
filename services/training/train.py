"""
Training and evaluation entrypoint
"""

import argparse
from pathlib import Path

from src.train_model import run_training
from src.evaluate_model import run_evaluation


def main():

    # Basic argparser
    parser = argparse.ArgumentParser(description="Train argument parser")
    parser.add_argument("--mode", choices=["train", "eval"], default="train",
                        help="Switch between train and eval mode")
    parser.add_argument("--model_name", default="model",
                    help="Name of the model (for evaluation only!)")
    args = parser.parse_args()

    # Config
    PROCESSED_DATA_DIR = "./data/processed"
    MODEL_DIR = "./artifacts/models"
    METRIC_DIR = "./artifacts/metrics"
    REPORTS_DIR = "./artifacts/reports"
    MODEL_PARAMETERS = {
        "random_state": 42,
        "n_estimators": 200
    }

    # Start training or evaluation
    if args.mode == "train":
        print("Training model...")
        run_training(
            processed_data_dir=PROCESSED_DATA_DIR,
            model_out_dir=MODEL_DIR,
            model_parameters=MODEL_PARAMETERS,
            reports_dir=REPORTS_DIR
        )
    elif args.mode == "eval":
        print(f"Evaluating model '{args.model_name}'...")
        model_path = Path(MODEL_DIR) / f"{args.model_name}.joblib"
        
        if not model_path.exists():
            raise FileNotFoundError(f"No trained model found at '{model_path}'")
        else:
            run_evaluation(
                model_name=args.model_name,
                processed_data_dir=PROCESSED_DATA_DIR,
                model_dir=MODEL_DIR,
                metrics_dir=METRIC_DIR,
                reports_dir=REPORTS_DIR
            )


if __name__ == "__main__":
    main()