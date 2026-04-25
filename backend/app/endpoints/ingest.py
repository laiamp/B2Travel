from io import BytesIO

from bson.binary import Binary
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from pymongo.errors import PyMongoError

from app.db import embeddings_col
from app.utils.clip_embeddings import MODEL_NAME, embed_image, embed_text

router = APIRouter(prefix="/ingest", tags=["ingest"])


async def _save_to_db(document: dict) -> str:
    try:
        result = await embeddings_col.insert_one(document)
        return str(result.inserted_id)
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}")


@router.post("/image")
async def ingest_image(image: UploadFile = File(...)) -> dict:
    if not (image.content_type and image.content_type.startswith("image/")):
        raise HTTPException(status_code=400, detail="Uploaded file must be an image")

    raw_bytes = await image.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Uploaded image is empty")

    try:
        pil_image = Image.open(BytesIO(raw_bytes)).convert("RGB")
    except UnidentifiedImageError:
        raise HTTPException(status_code=400, detail="Invalid image format")

    try:
        embedding = embed_image(pil_image)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate image embedding: {exc}")

    doc_id = await _save_to_db({
        "filename": image.filename,
        "content_type": image.content_type,
        "size_bytes": len(raw_bytes),
        "model": MODEL_NAME,
        "image": Binary(raw_bytes),
        "embedding": embedding,
				"projection": None
    })

    return {
        "id": doc_id,
        "filename": image.filename,
        "embedding_dim": len(embedding),
        "collection": "embeddings",
    }


@router.post("/text")
async def ingest_text(text: str = Form(...)) -> dict:
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    try:
        embedding = embed_text(text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate text embedding: {exc}")

    doc_id = await _save_to_db({
        "text": text,
        "content_type": "text/plain",
        "size_bytes": len(text.encode()),
        "model": MODEL_NAME,
        "embedding": embedding,
    })

    preview = text[:50] + ("..." if len(text) > 50 else "")
    return {
        "id": doc_id,
        "text_preview": preview,
        "embedding_dim": len(embedding),
        "collection": "embeddings",
    }