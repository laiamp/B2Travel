from fastapi import APIRouter, HTTPException
from pymongo.errors import PyMongoError

from app.db import embeddings_col

router = APIRouter(prefix="/retrieve", tags=["retrieve"])


@router.get("/images")
async def retrieve_images():
	try:
		cursor = embeddings_col.find(
			{"content_type": {"$regex": "^image/"}},
			{"image": 0, "embedding": 0}  # Exclude binary data and embeddings to keep response light
		)
		documents = await cursor.to_list(length=1000)
	except PyMongoError as exc:
		raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}")

	results = []
	for doc in documents:
		results.append({
			"id": str(doc["_id"]),
			"filename": doc.get("filename"),
			"content_type": doc.get("content_type"),
			"size_bytes": doc.get("size_bytes"),
			"model": doc.get("model")
		})

	return results


@router.get("/texts")
async def retrieve_texts():
	try:
		cursor = embeddings_col.find(
			{"content_type": "text/plain"},
			{"embedding": 0}  # Exclude embeddings to keep response light
		)
		documents = await cursor.to_list(length=1000)
	except PyMongoError as exc:
		raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}")

	results = []
	for doc in documents:
		results.append({
			"id": str(doc["_id"]),
			"text": doc.get("text"),
			"content_type": doc.get("content_type"),
			"size_bytes": doc.get("size_bytes"),
			"model": doc.get("model")
		})

	return results
