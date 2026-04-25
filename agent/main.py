import os
import asyncio
import threading

import httpx
from loguru import logger
from elevenlabs.client import ElevenLabs
from elevenlabs.conversational_ai.conversation import Conversation, ClientTools
from elevenlabs.conversational_ai.default_audio_interface import DefaultAudioInterface


def log_message(parameters):
    message = parameters.get("message")
    print("Puta", message)

def _run_coro_sync(coro):
    """Run an async coroutine from sync tool callbacks safely."""
    result: dict[str, str] = {}
    error: dict[str, Exception] = {}

    def _runner():
        try:
            result["value"] = asyncio.run(coro)
        except Exception as exc:
            error["exc"] = exc

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()

    if "exc" in error:
        raise error["exc"]
    return result.get("value")


async def _check_health_async(check_type: str) -> str:
    url = "http://localhost:8000/health"
    if check_type == "db":
        url += "/db"

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return str(response.json())

async def _get_flights_async() -> str:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get("http://localhost:8000/search/flights")
        response.raise_for_status()
        return str(response.json())

def check_health(parameters):
    """
    Check the health status of the backend or database.
    Argument: parameters['type'] can be 'server' (default) or 'db'.
    """
    check_type = parameters.get("type", "server")
    print(f"[Client Tool] Checking health for: {check_type}")

    try:
        data = _run_coro_sync(_check_health_async(check_type))
        print(f"[Client Tool] Output: {data}")
        return data
    except Exception as e:
        error_msg = f"Error checking health: {e}"
        print(f"[Client Tool] {error_msg}")
        return error_msg


async def _handle_vibe_async(vibe: str) -> str:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post("http://localhost:8000/coordinates/direction", json={"text": vibe})
        response.raise_for_status()
        return str(response.json())


def handle_vibe(parameters):
    vibe = str(parameters.get("vibe", "")).strip()
    logger.info("obtained vibe: {}", vibe)
    if not vibe:
        return "Error sending vibe: missing vibe"

    try:
        data = _run_coro_sync(_handle_vibe_async(vibe))
        logger.info(f"[Client Tool] Output: {data}")
        return data
    except Exception as e:
        error_msg = f"Error sending vibe: {e}"
        logger.error(f"[Client Tool] {error_msg}")
        return error_msg


# GET http://127.0.0.1:8000/events/agent
async def _get_recommendations_async() -> str:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get("http://localhost:8000/events/agent")
        response.raise_for_status()
        return str(response.json())


def get_recommendations(parameters):
    logger.info(f"Getting recommendations...")
    try:
        data = _run_coro_sync(_get_recommendations_async())
        logger.info(f"[Client Tool] Output: {data}")
        return data
    except Exception as e:
        error_msg = f"Error getting recommendations: {e}"
        logger.error(f"[Client Tool] {error_msg}")
        return error_msg

def get_flights(parameters):
    logger.info(f"Getting flights...")
    try:
        data = _run_coro_sync(_get_flights_async())
        logger.info(f"[Client Tool] Output: {data}")
        return data
    except Exception as e:
        error_msg = f"Error getting flights: {e}"
        logger.error(f"[Client Tool] {error_msg}")
        return error_msg

client_tools = ClientTools()
client_tools.register("logMessage", log_message)
client_tools.register("handleVibe", handle_vibe)
client_tools.register("getRecommendations", get_recommendations)
client_tools.register("getFlights", get_flights)    
client_tools.register("checkHealth", check_health)

# Initialize the client

# Create the conversation
conversation = Conversation(
    client=ElevenLabs(
        # api_key=os.environ.get("ELEVENLABS_API_KEY")# Optional for public agents
    ),
    requires_auth=False,
    agent_id="agent_1801kq0ygb73ecmr2nxcnwk9xa4m",
    audio_interface=DefaultAudioInterface(),# Uses system mic/speakers
    client_tools=client_tools
)

# Start the conversation
conversation.start_session()

# Wait for conversation to end
conversation_id = conversation.wait_for_session_end()
print(f"Conversation ID: {conversation_id}")