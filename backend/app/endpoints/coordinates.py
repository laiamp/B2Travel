from fastapi import APIRouter, HTTPException
from pymongo import UpdateOne
from pymongo.errors import PyMongoError

from app.db import embeddings_col
from app.utils.projection import compute_projections

router = APIRouter(prefix="/coordinates", tags=["coordinates"])

@router.get("/")
async def get_coordinates():
    """
    Recalculates the UMAP projection for all embeddings, updates the database,
    and returns all documents with their computed 3D projections.
    """
    try:
        # Fetch all records that have an embedding
        cursor = embeddings_col.find(
            {"embedding": {"$exists": True}},
            {"embedding": 1, "filename": 1, "content_type": 1, "text": 1, "model": 1}
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
        results.append({
            "id": str(doc["_id"]),
            "projection": proj,
            "filename": doc.get("filename"),
            "content_type": doc.get("content_type"),
            "text": doc.get("text"),
            "model": doc.get("model")
        })
        
    return results
