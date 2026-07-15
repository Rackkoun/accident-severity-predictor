from fastapi import FastAPI

from src.routes.health import router as health_router
from src.routes.predict import router as predict_router

app = FastAPI(
    title="Accident Severity Predictor API",
    version="0.1.0",
)

app.include_router(health_router)
app.include_router(predict_router)

@app.get("/")
def root():
    return {"message": "Accident Severity Predictor API is running"}