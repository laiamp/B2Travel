from io import BytesIO

from bson.binary import Binary
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Depends
from PIL import Image, UnidentifiedImageError
from pymongo.errors import PyMongoError
from google import genai
import torch

from app.db import embeddings_col
from app.utils.clip_embeddings import MODEL_NAME, embed_image, embed_text
from app.config import settings

router = APIRouter(prefix="/ingest", tags=["ingest"])


def get_gemini_client() -> genai.Client:
    return genai.Client(api_key=settings.GEMINI_API_KEY)


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
        "projection": None
    })

    preview = text[:50] + ("..." if len(text) > 50 else "")
    return {
        "id": doc_id,
        "text_preview": preview,
        "embedding_dim": len(embedding),
        "collection": "embeddings",
    }


@router.post("/song")
async def ingest_song(
    title: str = Form(...),
    channel: str = Form(...),
    videoId: str = Form(...),
    client: genai.Client = Depends(get_gemini_client)
) -> dict:
    prompt = f"Given the song title '{title}' and channel '{channel}', create a short, evocative travel-themed description of the mood and vibe this song evokes. The description should be suitable for a travel recommendation system, focusing on locations or atmospheres (e.g., 'A sunset beach in Ibiza', 'Busy streets of Tokyo at night'). Return only the description text."

    try:
        response = client.models.generate_content(
            model="gemma-4-26b-a4b-it",
            contents=[prompt],
        )
        description = response.text.strip()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Model error: {exc}")

    try:
        embedding = embed_text(description)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate embedding for song description: {exc}")

    doc_id = await _save_to_db({
        "title": title,
        "channel": channel,
        "videoId": videoId,
        "description": description,
        "content_type": "audio/mpeg",  # Using this to identify songs
        "size_bytes": len(description.encode()),
        "model": f"Gemma + {MODEL_NAME}",
        "embedding": embedding,
        "projection": None
    })

    return {
        "id": doc_id,
        "title": title,
        "description": description,
        "embedding_dim": len(embedding),
        "collection": "embeddings",
    }