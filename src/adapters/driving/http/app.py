from fastapi import FastAPI

from src.adapters.driving.http.routers.api.auth_router import auth_router

API_PREFIX = "/api"

app = FastAPI(title="FleetFlow API", description="REST API for managing FleetFlow operations", version="1.0")
app.include_router(auth_router, prefix=API_PREFIX)
