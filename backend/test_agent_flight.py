import asyncio
from pymongo import MongoClient

# Use synchronous PyMongo client for a quick script
client = MongoClient('mongodb+srv://hackupc26:OeM6ZZ66fYKX9rE5@hackupc26.na0owh9.mongodb.net/?tlsInsecure=true')
db = client.secondBrain

flight_event = {
    'type': 'results',
    'destination': 'front',  # DO NOT OVERWRITE THIS KEY!
    'received': False,
    'origin': ['Barcelona', 'BCN'],
    'flight_dest': ['Reykjavik', 'KEF'], # renamed from 'destination' to avoid dictionary key clash
    'stops': [0, 1, 1],
    'time_go': ['4h 30m', '6h 15m', '8h 00m'],
    'time_return': ['4h 45m', '7h 20m', '9h 10m'],
    'price': ['345', '180', '210'],
    'time_go_1': ['10:00', '08:30', '14:00'],
    'time_go_2': ['14:30', '14:45', '22:00'],
    'time_return_1': ['15:30', '09:00', '18:00'],
    'time_return_2': ['20:15', '16:20', '03:10']
}

print("Pushing flight results to VR...")
db.events.insert_one(flight_event)
print("Done! Look at your VR view!")
