from bson import ObjectId
from fastapi import APIRouter, HTTPException
from pymongo.errors import PyMongoError

from app.db import embeddings_col

router = APIRouter(prefix="/delete", tags=["delete"])


def _parse_object_id(record_id: str) -> ObjectId:
    try:
        return ObjectId(record_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid record id") from exc


async def _delete_record(content_type_filter: dict, record_id: str) -> dict:
    object_id = _parse_object_id(record_id)

    try:
        result = await embeddings_col.delete_one({"_id": object_id, **content_type_filter})
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Record not found")

    return {"deleted": True, "id": record_id}


@router.delete("/images/{record_id}")
async def delete_image(record_id: str) -> dict:
    return await _delete_record({"content_type": {"$regex": "^image/"}}, record_id)


@router.delete("/texts/{record_id}")
async def delete_text(record_id: str) -> dict:
    return await _delete_record({"content_type": "text/plain"}, record_id)