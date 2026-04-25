import os
import requests
from loguru import logger
from elevenlabs.client import ElevenLabs
from elevenlabs.conversational_ai.conversation import Conversation, ClientTools
from elevenlabs.conversational_ai.default_audio_interface import DefaultAudioInterface


def log_message(parameters):
    message = parameters.get("message")
    print("Puta", message)

async def check_health(parameters):
    """
    Check the health status of the backend or database.
    Argument: parameters['type'] can be 'server' (default) or 'db'.
    """
    check_type = parameters.get("type", "server")
    print(f"[Client Tool] Checking health for: {check_type}")
    
    url = "http://localhost:8000/health"
    if check_type == "db":
        url += "/db"
    
    try:
        response = await requests.get(url)
        data = response.json()
        print(f"[Client Tool] Output: {data}")
        return str(data)
    except Exception as e:
        error_msg = f"Error checking health: {e}"
        print(f"[Client Tool] {error_msg}")
        return error_msg



async def handle_vibe(parameters):
    vibe = parameters.get("vibe")
    logger.info('obtained vibe:', vibe)
    try:
        response = await requests.post("http://localhost:8000/coordinates/direction", json={"text": vibe})
        data = response.json()
        logger.info(f"[Client Tool] Output: {data}")
        return str(data)
    except Exception as e:
        error_msg = f"Error sending vibe: {e}"
        logger.error(f"[Client Tool] {error_msg}")
        return error_msg
    try:
        response = await requests.post("http://localhost:8000/coordinates/direction", json={"text": vibe})
        data = response.json()
        print(f"[Client Tool] Output: {data}")
        return str(data)
    except Exception as e:
        error_msg = f"Error sending vibe: {e}"
        print(f"[Client Tool] {error_msg}")
        return error_msg


# GET http://127.0.0.1:8000/events/agent
async def get_recommendations(parameters):
    logger.info(f"Getting recommendations...")
    try:
        response = await requests.get("http://localhost:8000/events/agent")
        data = response.json()
        logger.info(f"[Client Tool] Output: {data}")
        return str(data)
    except Exception as e:
        error_msg = f"Error getting recommendations: {e}"
        logger.error(f"[Client Tool] {error_msg}")
        return error_msg



client_tools = ClientTools()
client_tools.register("logMessage", log_message)
client_tools.register("handleVibe", handle_vibe)
client_tools.register("getRecommendations", get_recommendations)    
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