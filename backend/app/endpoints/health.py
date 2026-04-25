from fastapi import APIRouter, HTTPException
from pymongo.errors import PyMongoError

from app.db import ping_database

router = APIRouter(prefix="/health")


@router.get("/")
async def get_health():
    return {"status": "healthy"}


@router.get("/db")
async def get_database_health() -> dict:
    try:
        await ping_database()
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}")

    return {"status": "healthy", "database": "connected"}