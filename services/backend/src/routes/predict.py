from fastapi import APIRouter, HTTPException
from pathlib import Path
import joblib
import json
from contextlib import asynccontextmanager
import pandas as pd
import sys

# project dir
PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.append(str(PROJECT_ROOT))

from services.backend.src.schemas.prediction import PredictionRequest, PredictionResponse

router = APIRouter(tags=["Prediction"], prefix="/api/v1")

# model and features
MODEL = None
FEATURES = None

@asynccontextmanager
async def lifespan(app):

    global MODEL, FEATURES

    try:
        model_dir = PROJECT_ROOT / "artifacts" / "models"
        model_files = list(model_dir.glob("best_model_*.pkl"))

        if not model_files:
            raise FileNotFoundError("No model found in artifacts/models")
        
        latest_model = max(model_files, key=lambda m: m.stat().st_mtime)
        MODEL = joblib.load(latest_model)

        # extract timestamp
        timestamp = "_".join(latest_model.stem.split("_")[-2:])

        features_path = model_dir / f"features_{timestamp}.json"
        # print(f"Model loaded : {latest_model.name}")
        # print(f"Features file: {features_path.name}")

        with open(features_path, "r", encoding="utf-8") as f:
            FEATURES = json.load(f)

        # print("Expected features :", FEATURES)
        print(f"[LOAD MODEL] success - {len(FEATURES)} features loaded!")
    except Exception as e:
        print(f"Error loading model: {e}")
        raise

    yield


router.lifespan_context = lifespan

@router.post("/predict", response_model=PredictionResponse)
async def predict_accident(data: PredictionRequest):

    if MODEL is None:
        raise HTTPException(status_code=500, detail="Model not loaded")
    
    # convert data to df
    df = pd.DataFrame([data.model_dump()])

    # predict
    pred = MODEL.predict(df)[0]
    proba = MODEL.predict_proba(df)[0]

    class_names = ["Indemne", "Blessé léger", "Blessé hospitalisé", "Tué"]

    response = {
        "prediction": int(pred),
        "prediction_name": class_names[pred],
        "confidence": float(proba.max()),
        "probabilities": {name: float(p) for name, p in zip(class_names, proba)}
    }

    return response