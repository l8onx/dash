from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..config import settings

router = APIRouter()


@router.get("/api/health")
def health_check():
    return JSONResponse({
        "status": "ok",
        "version": "2.0.0",
        "dashUrl": settings.DASH_URL,
        "dataDir": settings.DATA_DIR,
    })
