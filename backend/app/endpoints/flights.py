"""
1. get all flight options (sorted by price) for a given origin, destination, date, etc.
2. get list with cheapest flight for each destination in a list of destinations (given same origin, date, etc.)
"""

from dataclasses import dataclass
from typing import List
from app.config import settings

import requests
from fastapi import  HTTPException, status, APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/flights")

DEFAULT_ORIGIN_IATA = "BCN"
DEFAULT_CURRENCY = "EUR"
DEFAULT_MARKET = "ES"
DEFAULT_LOCALE = "es-ES"
DEFAULT_CABIN_CLASS = "CABIN_CLASS_ECONOMY"
DEFAULT_YEAR = 2026


# Classes
@dataclass
class SkyscannerInfo:
    origin_iata: str
    destination_iata: str
    year: int
    month: int
    day: int
    currency: str
    market: str
    locale: str
    adults: int = 1
    cabin_class: str = DEFAULT_CABIN_CLASS

class FlightSearcher:
    def __init__(self):
        self.api_key = settings.SKYSCANNER_API_KEY
        if not self.api_key:
            raise ValueError("Missing SKYSCANNER_API_KEY in environment")
        self.headers = {"x-api-key": self.api_key, "Content-Type": "application/json"}

    def _clean_skyscanner_response(self, data, currency_code):
        content = data.get('content', {})
        itineraries = content.get('results', {}).get('itineraries', {})
        legs = content.get('results', {}).get('legs', {})

        clean_flights = []
        for itin_id, itin in itineraries.items():
            pricing = itin.get('pricingOptions', [{}])[0]
            raw_price = pricing.get('price', {}).get('amount', '0')
            formatted_price = float(raw_price) / 1000   # milliunits → actual

            leg_id = itin.get('legIds', [None])[0]
            leg_data = legs.get(leg_id, {})
            dep = leg_data.get('departureDateTime', {})
            arr = leg_data.get('arrivalDateTime', {})

            clean_flights.append({
                "id": itin_id,
                "price": round(formatted_price, 2),
                "currency": currency_code,
                "stops": leg_data.get('stopCount'),
                "duration_mins": leg_data.get('durationInMinutes'),
                "departure": f"{dep.get('hour'):02}:{dep.get('minute'):02}",
                "arrival": f"{arr.get('hour'):02}:{arr.get('minute'):02}",
                "booking_link": pricing.get('items', [{}])[0].get('deepLink')
            })

        # Sort by price ascending
        return sorted(clean_flights, key=lambda x: x["price"])

    def get_all_flight_options(self, info: SkyscannerInfo):
        url = 'https://partners.api.skyscanner.net/apiservices/v3/flights/live/search/create'
        payload = {
            "query": {
                "market": info.market,
                "locale": info.locale,
                "currency": info.currency,
                "queryLegs": [{
                    "originPlaceId": {"iata": info.origin_iata},
                    "destinationPlaceId": {"iata": info.destination_iata},
                    "date": {"year": info.year, "month": info.month, "day": info.day}
                }],
                "adults": info.adults,
                "cabinClass": info.cabin_class
            }
        }

        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            return self._clean_skyscanner_response(response.json(), info.currency)
        except requests.exceptions.RequestException as e:
            # Re-raise with more context (will be caught by FastAPI)
            raise RuntimeError(f"Skyscanner API error: {e}") from e


# Models
class FlightSearchRequest(BaseModel):
    destination_iata: str = Field(..., description="Destination airport IATA code (e.g., SIN)")
    year: int = Field(..., ge=2024, le=2030, description="Departure year")
    month: int = Field(..., ge=1, le=12, description="Departure month (1-12)")
    day: int = Field(..., ge=1, le=31, description="Departure day")
    adults: int = Field(1, ge=1, le=9, description="Number of adult passengers")

class BatchFlightSearchRequest(BaseModel):
    destinations_iata: List[str] = Field(..., description="List of destination IATA codes (e.g., ['SIN', 'LHR', 'JFK'])")
    month: int = Field(..., ge=1, le=12)
    day: int = Field(..., ge=1, le=31)
    adults: int = Field(1, ge=1, le=9)


# Endpoints
@router.post("/search", response_model=list)
def search_flights(request: FlightSearchRequest):
    """
    Search for flights and return sorted options (cheapest first).
    """
    searcher = FlightSearcher()
    info = SkyscannerInfo(
        origin_iata=DEFAULT_ORIGIN_IATA,
        destination_iata=request.destination_iata,
        year=request.year,
        month=request.month,
        day=request.day,
        currency=DEFAULT_CURRENCY,
        market=DEFAULT_MARKET,
        locale=DEFAULT_LOCALE,
        adults=request.adults,
        cabin_class=DEFAULT_CABIN_CLASS
    )
    try:
        flights = searcher.get_all_flight_options(info)
        return flights
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )

@router.post("/search/batch", response_model=List[dict])
def search_flights_batch(request: BatchFlightSearchRequest):
    """
    Search for cheapest flight to each destination in the list.
    Returns a list of objects: each contains destination and cheapest flight info.
    """
    searcher = FlightSearcher()
    results = []

    for dest in request.destinations_iata:
        try:
            # Create a SkyscannerInfo for this destination
            info = SkyscannerInfo(
                origin_iata=DEFAULT_ORIGIN_IATA,
                destination_iata=dest,
                year=DEFAULT_YEAR,
                month=request.month,
                day=request.day,
                currency=DEFAULT_CURRENCY,
                market=DEFAULT_MARKET,
                locale=DEFAULT_LOCALE,
                adults=request.adults,
                cabin_class=DEFAULT_CABIN_CLASS
            )
            # Get all flight options (already sorted by price)
            all_flights = searcher.get_all_flight_options(info)
            # Cheapest is the first element
            cheapest = all_flights[0] if all_flights else None
            results.append({
                "destination": dest,
                "cheapest_flight": cheapest  # will be null if no flights found
            })
        except Exception as e:
            # Log error and continue with next destination
            results.append({
                "destination": dest,
                "error": str(e),
                "cheapest_flight": None
            })
    return results

