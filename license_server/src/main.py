import logging

from fastapi import FastAPI

from src.api.v1.handlers import register_exception_handlers
from src.api.v1.router import api_router
from src.core.config import settings
from src.core.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
)

app.include_router(api_router, prefix="/api/v1")

register_exception_handlers(app)


@app.get("/")
def root():
    return {"message": "License Server is running", "docs": "/docs"}


@app.get("/health")
def health_check():
    logger.info("Health check endpoint accessed.")
    return {"status": "ok"}
