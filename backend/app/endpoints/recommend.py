import base64
import json
from functools import lru_cache
from typing import List, Tuple

from fastapi import APIRouter, HTTPException, Depends
from google import genai
from google.genai import types
from pydantic import BaseModel, Field, ValidationError
from pymongo.errors import PyMongoError

from app.config import settings
from app.db import events_col

router = APIRouter(prefix="/recommend", tags=["recommend"])


# =========================
# Client (Dependency)
# =========================

@lru_cache
def get_gemini_client() -> genai.Client:
    return genai.Client(api_key=settings.GEMINI_API_KEY)


# =========================
# Schemas
# =========================

class RecommendationRequest(BaseModel):
    images_base64: List[str] = Field(..., min_length=1)


class RecommendationResponse(BaseModel):
    recommendation: str = Field(..., min_length=20)


# =========================
# Utilities
# =========================

def decode_image(img_b64: str) -> Tuple[bytes, str]:
    """Decode base64 image and infer mime subtype."""
    if "," in img_b64:
        header, img_b64 = img_b64.split(",", 1)
        if "png" in header:
            return base64.b64decode(img_b64), "png"
        if "webp" in header:
            return base64.b64decode(img_b64), "webp"
    return base64.b64decode(img_b64), "jpeg"


# =========================
# Service Layer
# =========================

_SYSTEM_PROMPT = """
You are a travel recommendation assistant.

Analyze the provided images and infer the shared travel vibe (style, mood, scenery, culture).

Return valid JSON only (no markdown, no explanation) in this format:
{
    "recommendation": "A short sentence that explains what the images have in common and includes 3-5 city names that fit this vibe."
}
"""

_DEFAULT_RECOMMENDATION = (
        "Your images suggest a vibrant, exploratory vibe with a mix of culture and scenery. "
        "Great city matches are Tokyo, Lisbon, Mexico City, and Cape Town."
)


class RecommendationService:
    def __init__(self, client: genai.Client):
        self.client = client

    def _upload_images(self, images_base64: List[str]):
        parts: List[types.Part] = []

        for img in images_base64:
            raw, ext = decode_image(img)

            parts.append(types.Part.from_bytes(data=raw, mime_type=f"image/{ext}"))

        return parts

    def _generate(self, image_parts: List[types.Part]):
        response = self.client.models.generate_content(
            model="gemma-4-26b-a4b-it",
            contents=[_SYSTEM_PROMPT, *image_parts],
        )
        return response.text

    def _parse(self, text: str) -> str:
        try:
            data = json.loads(text)
            if isinstance(data, dict) and "recommendation" in data:
                parsed = RecommendationResponse(**data)
                return self._normalize_recommendation(parsed.recommendation)

            # Backward compatibility with older prompt outputs.
            if isinstance(data, dict) and isinstance(data.get("cities"), list):
                cities = [str(c).strip() for c in data["cities"] if str(c).strip()]
                if cities:
                    return (
                        "Your selected images share a coherent travel vibe. "
                        f"Great city fits are {', '.join(cities[:5])}."
                    )

            return _DEFAULT_RECOMMENDATION
        except (json.JSONDecodeError, ValidationError) as exc:
            raise ValueError(f"Invalid model response: {text}") from exc

    def _normalize_recommendation(self, recommendation: str) -> str:
        normalized = " ".join(recommendation.split())
        if len(normalized) < 20:
            return _DEFAULT_RECOMMENDATION
        return normalized

    def recommend(self, images_base64: List[str]) -> str:
        uploaded_files = self._upload_images(images_base64)
        raw_response = self._generate(uploaded_files)
        return self._parse(raw_response)


# =========================
# Route
# =========================

@router.post("/")
async def create_recommendation_event(
    request: RecommendationRequest,
    client: genai.Client = Depends(get_gemini_client),
):
    # service = RecommendationService(client)

    # try:
    #     recommendation = service.recommend(request.images_base64)

    # except ValueError as exc:
    #     raise HTTPException(status_code=502, detail=str(exc))

    # except Exception as exc:
    #     raise HTTPException(status_code=502, detail=f"Model error: {exc}")

    recommendation = _DEFAULT_RECOMMENDATION

    event = {
        "type": "recommendation",
        "destination": "agent",
        "recommendations": recommendation,
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