from fastapi import FastAPI

from src.routes.health import router as health_router

app = FastAPI(
    title="Accident Severity Predictor API",
    version="0.1.0",
)

app.include_router(health_router)

@app.get("/")
def root():
    return {"message": "Accident Severity Predictor API is running"}