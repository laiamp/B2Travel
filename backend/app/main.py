from fastapi import FastAPI
from backend.app.endpoints import health

app = FastAPI(title="HackUPC Backend", version="0.1.0")
app.include_router(health.router)

@app.get("/")
def root() -> dict[str, str]:
    return {"message": "FastAPI backend is running"}
