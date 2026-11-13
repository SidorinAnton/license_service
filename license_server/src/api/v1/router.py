from fastapi import APIRouter

from src.api.v1.endpoints import client

api_router = APIRouter()
api_router.include_router(client.router)
