from pymongo import AsyncMongoClient

from app.config import settings

client = AsyncMongoClient(settings.MONGODB_URL)

db = client.get_database("secondBrain")
embeddings_col = db.get_collection("embeddings")

async def ping_database() -> None:
    await client.admin.command("ping")

async def close_database() -> None:
    await client.close()
