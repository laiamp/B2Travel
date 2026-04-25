from io import BytesIO

import torch
from bson.binary import Binary
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel
from pymongo.errors import PyMongoError
from transformers import CLIPModel, CLIPProcessor

from app.db import embeddings_col

router = APIRouter(prefix="/ingest", tags=["ingest"])

_MODEL_NAME = "openai/clip-vit-base-patch32"
_processor: CLIPProcessor | None = None
_model: CLIPModel | None = None


def _get_clip_components() -> tuple[CLIPProcessor, CLIPModel]:
    global _processor, _model
    if _processor is None or _model is None:
        _processor = CLIPProcessor.from_pretrained(_MODEL_NAME)
        _model = CLIPModel.from_pretrained(_MODEL_NAME)
        _model.eval()
    return _processor, _model


def _extract_embedding(raw_output: torch.Tensor, modality: str) -> list[float]:
    """Resolve CLIP output to a normalised 1-D embedding list."""
    embed_attr = "image_embeds" if modality == "image" else "text_embeds"

    if isinstance(raw_output, torch.Tensor):
        tensor = raw_output
    elif hasattr(raw_output, "pooler_output"):
        tensor = raw_output.pooler_output
    elif hasattr(raw_output, embed_attr):
        tensor = getattr(raw_output, embed_attr)
    else:
        raise HTTPException(status_code=500, detail="Unexpected CLIP output format")

    normalized = tensor / tensor.norm(dim=-1, keepdim=True)
    return normalized[0].cpu().tolist()


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

    processor, model = _get_clip_components()
    inputs = processor(images=pil_image, return_tensors="pt")

    with torch.no_grad():
        embedding = _extract_embedding(model.get_image_features(**inputs), "image")

    doc_id = await _save_to_db({
        "filename": image.filename,
        "content_type": image.content_type,
        "size_bytes": len(raw_bytes),
        "model": _MODEL_NAME,
        "image": Binary(raw_bytes),
        "embedding": embedding,
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

    processor, model = _get_clip_components()
    inputs = processor(text=[text], return_tensors="pt", padding=True, truncation=True)

    with torch.no_grad():
        embedding = _extract_embedding(model.get_text_features(**inputs), "text")

    doc_id = await _save_to_db({
        "text": text,
        "content_type": "text/plain",
        "size_bytes": len(text.encode()),
        "model": _MODEL_NAME,
        "embedding": embedding,
    })

    preview = text[:50] + ("..." if len(text) > 50 else "")
    return {
        "id": doc_id,
        "text_preview": preview,
        "embedding_dim": len(embedding),
        "collection": "embeddings",
    }