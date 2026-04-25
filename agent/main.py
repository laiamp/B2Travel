import os
import requests
from elevenlabs.client import ElevenLabs
from elevenlabs.conversational_ai.conversation import Conversation, ClientTools
from elevenlabs.conversational_ai.default_audio_interface import DefaultAudioInterface


def log_message(parameters):
    message = parameters.get("message")
    print("Puta", message)

def check_health(parameters):
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
        response = requests.get(url)
        data = response.json()
        print(f"[Client Tool] Output: {data}")
        return str(data)
    except Exception as e:
        error_msg = f"Error checking health: {e}"
        print(f"[Client Tool] {error_msg}")
        return error_msg


# TODO: POST http://127.0.0.1:8000/coordinates/direction 
# {
#     "text": "Summer"
# }

from loguru import logger

def handle_vibe(parameters):
    vibe = parameters.get("vibe")
    print('obtained vibe:', vibe)
    print('sending to VR...')
    try:
        response = requests.post("http://localhost:8000/coordinates/direction", json={"text": vibe})
        data = response.json()
        logger.info(f"[Client Tool] Output: {data}")
        return str(data)
    except Exception as e:
        error_msg = f"Error sending vibe: {e}"
        logger.error(f"[Client Tool] {error_msg}")
        return error_msg
    try:
        response = requests.post("http://localhost:8000/coordinates/direction", json={"text": vibe})
        data = response.json()
        print(f"[Client Tool] Output: {data}")
        return str(data)
    except Exception as e:
        error_msg = f"Error sending vibe: {e}"
        print(f"[Client Tool] {error_msg}")
        return error_msg

# def handle_date(date):
#     print('Getting flights for that date...')

# def handle_budget(budget):
#     print('Getting all destinations with prices...')
#     print('Selecting subset of cities for that budget..')



client_tools = ClientTools()
client_tools.register("logMessage", log_message)
client_tools.register("handleVibe", handle_vibe)
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