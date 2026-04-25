import os
from elevenlabs.client import ElevenLabs
from elevenlabs.conversational_ai.conversation import Conversation
from elevenlabs.conversational_ai.default_audio_interface import DefaultAudioInterface

# Initialize the client
client = ElevenLabs(
    # api_key=os.environ.get("ELEVENLABS_API_KEY")# Optional for public agents
)

# Create the conversation
conversation = Conversation(
    client,
    requires_auth=False,
    agent_id="agent_1801kq0ygb73ecmr2nxcnwk9xa4m",
    audio_interface=DefaultAudioInterface(),# Uses system mic/speakers
)

# Start the conversation
conversation.start_session()

# Wait for conversation to end
conversation_id = conversation.wait_for_session_end()
print(f"Conversation ID: {conversation_id}")