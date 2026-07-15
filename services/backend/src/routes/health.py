from fastapi import APIRouter


router = APIRouter(tags=["Healthy"], prefix="/api/v1")

@router.get("/health", status_code=200)
def health():
    return {
        "status": "healthy",
        "service": "accident-severity-predictor"
    }