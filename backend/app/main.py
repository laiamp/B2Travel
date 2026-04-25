from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import close_database
from app.endpoints import health, mflix


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        yield
    finally:
        await close_database()


app = FastAPI(title="HackUPC Backend", version="0.1.0", lifespan=lifespan)
app.include_router(health.router)
app.include_router(mflix.router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "FastAPI backend is running"}
