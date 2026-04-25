import base64
import json
import os
import re
import tempfile

from fastapi import APIRouter, HTTPException
from google import genai
from pydantic import BaseModel, Field
from pymongo.errors import PyMongoError

from app.config import settings
from app.db import events_col

router = APIRouter(prefix="/recommend", tags=["recommend"])

_gemini_client: genai.Client | None = None


def _get_gemini_client() -> genai.Client:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _gemini_client


class RecommendationRequest(BaseModel):
    images_base64: list[str] = Field(
        ...,
        min_length=1,
        description="List of input images in base64 format",
    )


_SYSTEM_PROMPT = (
    "You are a travel recommendation assistant. "
    "Analyze the visual content, style, mood, scenery, and cultural cues in the provided images. "
    "Based on them, recommend exactly 5 real-world cities that match the traveller's implied preferences. "
    "Return ONLY a JSON array of exactly 5 city name strings, nothing else. "
    'Example: ["Kyoto", "Lisbon", "Cape Town", "Reykjavik", "Medellín"]'
)


def _parse_cities(text: str) -> list[str]:
    """Extract a JSON list of strings from the model response."""
    match = re.search(r"\[.*?\]", text, re.DOTALL)
    if match:
        try:
            cities = json.loads(match.group())
            if isinstance(cities, list) and len(cities) > 0:
                return [str(c) for c in cities]
        except json.JSONDecodeError:
            pass
    raise ValueError(f"Could not parse city list from model response: {text!r}")


@router.post("/")
async def create_recommendation_event(request: RecommendationRequest) -> dict:
    client = _get_gemini_client()

    uploaded_files = []
    tmp_paths = []

    try:
        # Upload each base64 image via the Files API
        for img_b64 in request.images_base64:
            # Strip data-URI prefix if present
            if "," in img_b64:
                header, img_b64 = img_b64.split(",", 1)
                ext = "jpg"
                if "png" in header:
                    ext = "png"
                elif "webp" in header:
                    ext = "webp"
            else:
                ext = "jpg"

            raw = base64.b64decode(img_b64)

            # Write to a temp file so we can use client.files.upload(file=path)
            with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
                tmp.write(raw)
                tmp_paths.append(tmp.name)

            uploaded = client.files.upload(file=tmp_paths[-1])
            uploaded_files.append(uploaded)

        # Build contents: all uploaded file references + the prompt
        contents = [*uploaded_files, _SYSTEM_PROMPT]

        response = client.models.generate_content(
            model="gemma-4-26b-a4b-it",
            contents=contents,
        )

        cities = _parse_cities(response.text)

    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Gemini API error: {exc}")
    finally:
        # Clean up temp files
        for path in tmp_paths:
            try:
                os.unlink(path)
            except OSError:
                pass

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
