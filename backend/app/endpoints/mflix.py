from bson import ObjectId
from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from pymongo.errors import PyMongoError

from app.db import comments_collection, sample_mflix_db

router = APIRouter(prefix="/mflix", tags=["mflix"])


@router.get("/comments/preview")
async def get_comments_preview() -> dict:
    try:
        collections = await sample_mflix_db.list_collection_names()
        comments = await comments_collection.find().limit(10).to_list(length=10)
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}")

    return {
        "database": "sample_mflix",
        "collections": collections,
        "table": "comments",
        "count": len(comments),
        "records": jsonable_encoder(comments, custom_encoder={ObjectId: str}),
    }
