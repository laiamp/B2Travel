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
        # Fetch all records that have an embedding (images, songs, text)
        cursor = embeddings_col.find(
            {"embedding": {"$exists": True}},
            {"embedding": 1, "filename": 1, "content_type": 1, "text": 1, "model": 1, "image": 1, "title": 1, "videoId": 1}
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
            "title": doc.get("title"),
            "videoId": doc.get("videoId"),
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
        # Instead of projecting the text embedding directly via UMAP, we find the closest
        # existing document by cosine similarity in the high-dimensional CLIP space,
        # and then return THAT document's already-calculated UMAP projection.
        # This completely bridges the text-to-image modality gap!
        cursor = embeddings_col.find({"projection": {"$exists": True}, "embedding": {"$exists": True}})
        documents = await cursor.to_list(length=100000)
        
        if not documents:
            raise HTTPException(status_code=404, detail="No projected documents found in DB.")
            
        import numpy as np
        target_emb = np.array(embedding)
        target_emb = target_emb / (np.linalg.norm(target_emb) + 1e-9)
        
        best_doc = None
        best_sim = -float('inf')
        
        for doc in documents:
            doc_emb = np.array(doc["embedding"])
            doc_emb = doc_emb / (np.linalg.norm(doc_emb) + 1e-9)
            sim = np.dot(target_emb, doc_emb)
            if sim > best_sim:
                best_sim = sim
                best_doc = doc
                
        position = best_doc["projection"]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to find closest semantic match: {exc}")

    event = {
        "type": "redirect",
        "vibe": text,
        "destination": "front",
        "position": [float(v) for v in position],
        "received": False,
    }

    try:
        result = await events_col.insert_one(event)
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}")

    return {
        "event_id": str(result.inserted_id),
        "position": event["position"],
        "type": event["type"],
        "vibe": event["vibe"],
        "destination": event["destination"],
        "received": event["received"],
    }
