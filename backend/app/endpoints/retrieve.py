import base64
from fastapi import APIRouter, HTTPException
from pymongo.errors import PyMongoError

from app.db import embeddings_col

router = APIRouter(prefix="/retrieve", tags=["retrieve"])


@router.get("/images")
async def retrieve_images():
	try:
		cursor = embeddings_col.find({"content_type": {"$regex": "^image/"}})
		documents = await cursor.to_list(length=1000)
	except PyMongoError as exc:
		raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}")

	results = []
	for doc in documents:
		image_data = None
		if "image" in doc:
			image_data = base64.b64encode(doc["image"]).decode("utf-8")

		results.append({
			"id": str(doc["_id"]),
			"filename": doc.get("filename"),
			"content_type": doc.get("content_type"),
			"size_bytes": doc.get("size_bytes"),
			"model": doc.get("model"),
			"image_base64": image_data,
			"embedding": doc.get("embedding")
		})

	return results


@router.get("/texts")
async def retrieve_texts():
	try:
		cursor = embeddings_col.find({"content_type": "text/plain"})
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
			"model": doc.get("model"),
			"embedding": doc.get("embedding")
		})

	return results


@router.get("/songs")
async def retrieve_songs():
	try:
		cursor = embeddings_col.find({"content_type": "audio/mpeg"})
		documents = await cursor.to_list(length=1000)
	except PyMongoError as exc:
		raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}")

	results = []
	for doc in documents:
		results.append({
			"id": str(doc["_id"]),
			"title": doc.get("title"),
			"channel": doc.get("channel"),
			"videoId": doc.get("videoId"),
			"description": doc.get("description"),
			"content_type": doc.get("content_type"),
			"size_bytes": doc.get("size_bytes"),
			"model": doc.get("model"),
			"embedding": doc.get("embedding")
		})

	return results
