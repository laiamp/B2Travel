import sys
import requests
import json

def test_vibe(vibe: str):
    print(f"🎙️ Mimicking Voice Agent... Sending vibe: '{vibe}'")
    url = "http://localhost:8000/coordinates/direction"
    payload = {"text": vibe}
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("✅ Success! Event created.")
            data = response.json()
            print(f"Event Data: {json.dumps(data, indent=2)}")
            print("\n👀 Now look at your VR Frontend! You should see a notification and guiding arrows.")
        else:
            print(f"❌ Failed! Status Code: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        print("Make sure your backend is running on http://localhost:8000")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        vibe = " ".join(sys.argv[1:])
    else:
        vibe = "Snowy Mountains"
    
    test_vibe(vibe)
