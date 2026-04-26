import sys
import requests
import json

def test_destination(destination_name: str):
    print(f"✈️ Mimicking Voice Agent... Recommending destination: '{destination_name}'")
    url = "http://localhost:8000/events/destination"
    
    # Mocking a single flight recommendation
    payload = {
        "destination": destination_name,
        "price": 85.50,
        "currency": "EUR",
        "stops": 0,
        "duration_mins": 135,
        "departure": "08:30",
        "arrival": "10:45",
        "booking_link": "https://skyscanner.com/book"
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("✅ Success! Event created.")
            data = response.json()
            print(f"Event Data: {json.dumps(data, indent=2)}")
            print("\n👀 Now look at your VR Frontend! You should see the single flight recommendation popup.")
        else:
            print(f"❌ Failed! Status Code: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        print("Make sure your backend is running on http://localhost:8000")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        dest = " ".join(sys.argv[1:])
    else:
        dest = "Paris, France"
    
    test_destination(dest)
