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
