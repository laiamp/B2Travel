from io import BytesIO

import torch
from bson.binary import Binary
from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
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


@router.post("/image")
async def ingest_image(image: UploadFile = File(...)) -> dict:
	if image.content_type is None or not image.content_type.startswith("image/"):
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
		embedding_tensor = model.get_image_features(**inputs)
		normalized = embedding_tensor / embedding_tensor.norm(dim=-1, keepdim=True)
		embedding = normalized[0].cpu().tolist()

	document = {
		"filename": image.filename,
		"content_type": image.content_type,
		"size_bytes": len(raw_bytes),
		"model": _MODEL_NAME,
		"image": Binary(raw_bytes),
		"embedding": embedding,
	}

	try:
		result = await embeddings_col.insert_one(document)
	except PyMongoError as exc:
		raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}")

	return {
		"id": str(result.inserted_id),
		"filename": image.filename,
		"embedding_dim": len(embedding),
		"collection": "embeddings",
	}
