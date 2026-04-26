from bson import ObjectId
from fastapi import APIRouter, HTTPException
from pymongo import DESCENDING, ReturnDocument
from pymongo.errors import PyMongoError

from app.db import events_col

router = APIRouter(prefix="/events", tags=["events"])


def _serialize_event(document: dict) -> dict:
	event = dict(document)
	event["id"] = str(event.pop("_id"))
	return event


async def _get_latest_unreceived(destination: str) -> dict:
	try:
		event = await events_col.find_one_and_update(
			{"destination": destination, "received": False},
			{"$set": {"received": True}},
			sort=[("_id", DESCENDING)],
			return_document=ReturnDocument.BEFORE,
		)
	except PyMongoError as exc:
		raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}")

	if event is None:
		return {"event": None}

	return {"event": _serialize_event(event)}


@router.get("/front")
async def get_front_event() -> dict:
	return await _get_latest_unreceived("front")


@router.get("/agent")
async def get_agent_event() -> dict:
	return await _get_latest_unreceived("agent")


from typing import Any, List, Optional
from pydantic import BaseModel


class FlightRecommendation(BaseModel):
    destination: str
    id: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    stops: Optional[int] = None
    duration_mins: Optional[int] = None
    departure: Optional[str] = None
    arrival: Optional[str] = None
    booking_link: Optional[str] = None
    error: Optional[str] = None


@router.post("/destination")
async def post_destination_event(flight: FlightRecommendation) -> dict:
    """
    Store a single flight recommendation as a 'destination' event for the frontend.
    """
    flight_dict = flight.model_dump(exclude_none=True)
    flight_dest = flight_dict.pop("destination", "Unknown")
    
    event = {
        "type": "destination",
        "destination": "front",
        "received": False,
        "flight_dest": flight_dest,
        **flight_dict,
    }

    try:
        result = await events_col.insert_one(event)
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}")

    return {"event_id": str(result.inserted_id)}


