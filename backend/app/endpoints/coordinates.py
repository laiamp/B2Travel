import base64
import json

from fastapi import APIRouter, HTTPException, Request
from pymongo import UpdateOne
from pymongo.errors import PyMongoError
from pydantic import BaseModel, Field

from app.db import embeddings_col, events_col
from app.utils.clip_embeddings import embed_text
from app.utils.projection import compute_projections, project_with_existing_model

router = APIRouter(prefix="/coordinates", tags=["coordinates"])


class DirectionRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Text to embed and project")


async def _extract_direction_text(request: Request) -> str:
    """Accept JSON object, raw text, or stringified JSON body."""
    try:
        payload = await request.json()
    except Exception:
        payload = (await request.body()).decode("utf-8", errors="ignore")

    text: str | None = None

    if isinstance(payload, dict):
        text_value = payload.get("text")
        if text_value is not None:
            text = str(text_value)
    elif isinstance(payload, str):
        candidate = payload.strip()
        if candidate:
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                parsed = None

            if isinstance(parsed, dict) and parsed.get("text") is not None:
                text = str(parsed["text"])
            else:
                text = candidate

    if text is None or not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    return text.strip()

@router.get("/")
async def get_coordinates():
    """
    Recalculates the UMAP projection for all embeddings, updates the database,
    and returns all documents with their computed 3D projections.
    """
    try:
        # Fetch only image records that have an embedding
        cursor = embeddings_col.find(
            {"embedding": {"$exists": True}, "content_type": {"$regex": "^image/"}},
            {"embedding": 1, "filename": 1, "content_type": 1, "text": 1, "model": 1, "image": 1}
        )
        documents = await cursor.to_list(length=100000)
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}")

    if not documents:
        return []

    # Prepare inputs for projection
    doc_ids = [doc["_id"] for doc in documents]
    embeddings = [doc["embedding"] for doc in documents]
    
    try:
        projections = compute_projections(embeddings, n_components=3)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to compute projections: {exc}")
        
    # Build bulk writes to update the database
    operations = [
        UpdateOne({"_id": doc_id}, {"$set": {"projection": proj}})
        for doc_id, proj in zip(doc_ids, projections)
    ]
    
    if operations:
        try:
            await embeddings_col.bulk_write(operations)
        except PyMongoError as exc:
            raise HTTPException(status_code=503, detail=f"Database update failed: {exc}")
            
    # Format the results to return
    results = []
    for doc, proj in zip(documents, projections):
        image_data = None
        if "image" in doc and doc["image"] is not None:
            image_data = base64.b64encode(doc["image"]).decode("utf-8")

        results.append({
            "id": str(doc["_id"]),
            "projection": proj,
            "filename": doc.get("filename"),
            "content_type": doc.get("content_type"),
            "text": doc.get("text"),
            "model": doc.get("model"),
            "image_base64": image_data,
        })
        
    return results


@router.post("/direction")
async def direction(request: Request):
    text = await _extract_direction_text(request)

    try:
        embedding = embed_text(text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate embedding: {exc}")

    try:
        position = project_with_existing_model(embedding)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to project embedding: {exc}")

    event = {
        "type": "redirect",
        "destination": "front",
        "position": [float(v) for v in position],
        "recieved": False,
    }

    try:
        result = await events_col.insert_one(event)
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}")

    return {
        "event_id": str(result.inserted_id),
        "position": event["position"],
        "type": event["type"],
        "destination": event["destination"],
        "recieved": event["recieved"],
    }
