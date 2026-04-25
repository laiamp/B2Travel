from pymongo import AsyncMongoClient

from app.config import settings


client = AsyncMongoClient(settings.MONGODB_URL)

sample_mflix_db = client.get_database("sample_mflix")
comments_collection = sample_mflix_db.get_collection("comments")

async def ping_database() -> None:
    await client.admin.command("ping")


async def close_database() -> None:
    await client.close()
