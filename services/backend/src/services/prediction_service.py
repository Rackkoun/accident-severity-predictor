"""
Backend prediction service.

Loads the latest trained model from shared artifacts volume
and makes predictions on incoming requests.
"""

import json
from pathlib import Path

import joblib
import pandas as pd
from fastapi import HTTPException

from common.utils.asp_logging import get_logger
from common.utils.paths import MODEL_DIR
from services.backend.src.schemas.prediction import PredictionRequest, PredictionResponse

logger = get_logger(__name__)

# in-memory cache for loaded model
_model_cache: dict = {
    "model": None,
    "features": None,
    "name": None,
}


def _latest_model_path(model_dir: Path, model_name: str) -> Path:
    """return the latest model file matching model_name_*.joblib."""
    files = list(model_dir.glob(f"{model_name}_*.joblib"))
    if not files:
        raise FileNotFoundError(f"No trained model found for '{model_name}_*.joblib' in {model_dir}")
    return max(files, key=lambda p: p.stat().st_mtime)


def _latest_feature_path(model_dir: Path, model_name: str) -> Path:
    """return the latest features JSON matching model_name_*_features.json."""
    files = list(model_dir.glob(f"{model_name}_*_features.json"))
    if not files:
        raise FileNotFoundError(f"No feature file found for '{model_name}' in {model_dir}")
    return max(files, key=lambda p: p.stat().st_mtime)


def load_latest_model(force_reload: bool = False) -> None:
    """load the latest trained model and its feature list into cache.

    Args:
        force_reload: If True, reload even if a model is already cached.
    """
    global _model_cache

    if _model_cache["model"] is not None and not force_reload:
        logger.debug("Model already loaded, skipping.")
        return

    logger.info("Loading latest trained model...")

    try:
        model_path = _latest_model_path(MODEL_DIR, "model")
        feature_path = _latest_feature_path(MODEL_DIR, "model")

        _model_cache["model"] = joblib.load(model_path)
        with open(feature_path) as f:
            _model_cache["features"] = json.load(f)
        _model_cache["name"] = model_path.stem

        logger.info(f"Loaded model: {_model_cache['name']} ({len(_model_cache['features'])} features)")

    except FileNotFoundError as exc:
        logger.warning(f"No model found in {MODEL_DIR}: {exc}")
        _model_cache = {"model": None, "features": None, "name": None}
        raise HTTPException(
            status_code=503,
            detail=f"No trained model available. Run training first: {exc}",
        ) from exc


def predict_accident(request: PredictionRequest) -> PredictionResponse:
    """make a severity prediction from input features.

    Args:
        request: Validated Pydantic model with all required features.

    Returns:
        PredictionResponse with severity label, code, and probability.

    Raises:
        HTTPException: If model is not loaded or prediction fails.
    """
    global _model_cache

    # lazy load model if not cached
    if _model_cache["model"] is None:
        load_latest_model()

    model = _model_cache["model"]
    features = _model_cache["features"]
    model_name = _model_cache["name"]

    # build DataFrame from request - alias "int" instead of "int_"
    input_data = request.model_dump(by_alias=True)

    # id_usager appears in exported features...
    # add id_usager if missing (model expects it but it's an internal ID)
    if "id_usager" in features and "id_usager" not in input_data:
        input_data["id_usager"] = 0  # placeholder, not used for prediction

    df = pd.DataFrame([input_data])

    # ensure correct column order and presence
    try:
        df = df[features]
    except KeyError as exc:
        missing = set(features) - set(input_data.keys())
        extra = set(input_data.keys()) - set(features)
        logger.error(f"Feature mismatch. Missing: {missing}, Extra: {extra}")
        raise HTTPException(
            status_code=422,
            detail=f"Feature mismatch with trained model. Missing: {missing}, Extra: {extra}",
        ) from exc

    # predict
    prediction = int(model.predict(df)[0])

    # probability (RandomForest supports predict_proba)
    probability = None
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(df)[0]
        probability = float(proba[prediction])

    severity_map = {
        0: "Unharmed / Lightly injured",
        1: "Injured (hospitalized) / Killed",
    }

    return PredictionResponse(
        severity=severity_map.get(prediction, "Unknown"),
        severity_code=prediction,
        probability=probability,
        model_used=model_name or "unknown",
    )


def get_model_status() -> dict:
    """return current model loading status (for health checks)."""
    return {
        "loaded": _model_cache["model"] is not None,
        "name": _model_cache["name"],
        "features_count": len(_model_cache["features"]) if _model_cache["features"] else 0,
    }
