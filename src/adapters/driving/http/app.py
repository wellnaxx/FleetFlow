from fastapi import FastAPI

from src.adapters.driving.http.routers.api.auth_router import auth_router
from src.adapters.driving.http.routers.api.customers_router import customers_router

API_PREFIX = "/api"

app = FastAPI(title="FleetFlow API", description="REST API for managing FleetFlow operations", version="1.0")
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(customers_router, prefix=API_PREFIX)
