from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from pymongo.errors import PyMongoError

from app.db import events_col

router = APIRouter(prefix="/recommend", tags=["recommend"])


class RecommendationRequest(BaseModel):
	images_base64: list[str] = Field(
		...,
		min_length=1,
		description="List of input images in base64 format",
	)

@router.post("/")
async def create_recommendation_event(request: RecommendationRequest) -> dict:

  

	# Add here the Gemma recommendation logic using the input images.
	cities = ["Barcelona", "Paris", "New York", "Tokyo", "Sydney"]

  
  
  


	event = {
		"type": "recommendation",
		"destination": "agent",
		"recommendations": cities,
		"received": False,
	}

	try:
		result = await events_col.insert_one(event)
	except PyMongoError as exc:
		raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}")

	return {
		"event_id": str(result.inserted_id),
		"type": event["type"],
		"destination": event["destination"],
		"recommendations": event["recommendations"],
		"received": event["received"],
	}
