from fastapi import FastAPI

from src.adapters.driving.http.routers.api.auth_router import auth_router
from src.adapters.driving.http.routers.api.customers_router import customers_router
from src.adapters.driving.http.routers.api.packages_router import packages_router
from src.adapters.driving.http.routers.api.routes_router import routes_router
from src.adapters.driving.http.routers.api.state_router import state_router
from src.adapters.driving.http.routers.api.trucks_router import trucks_router

API_PREFIX = "/api"

app = FastAPI(title="FleetFlow API", description="REST API for managing FleetFlow operations", version="1.0")
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(customers_router, prefix=API_PREFIX)
app.include_router(packages_router, prefix=API_PREFIX)
app.include_router(routes_router, prefix=API_PREFIX)
app.include_router(trucks_router, prefix=API_PREFIX)
app.include_router(state_router, prefix=API_PREFIX)
