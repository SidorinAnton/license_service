from fastapi import FastAPI

from src.api.v1.router import api_router
from src.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def root():
    return {"message": "License Server is running", "docs": "/docs"}
