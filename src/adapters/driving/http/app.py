import logging

from fastapi import FastAPI

from src.adapters.driving.http.exception_handlers import register_exception_handlers
from src.adapters.driving.http.middleware import RequestLoggingMiddleware
from src.adapters.driving.http.routers.api.audit_router import audit_router
from src.adapters.driving.http.routers.api.auth_router import auth_router
from src.adapters.driving.http.routers.api.customers_router import customers_router
from src.adapters.driving.http.routers.api.packages_router import packages_router
from src.adapters.driving.http.routers.api.routes_router import routes_router
from src.adapters.driving.http.routers.api.state_router import state_router
from src.adapters.driving.http.routers.api.trucks_router import trucks_router

API_PREFIX = "/api"
logger = logging.getLogger(__name__)

app = FastAPI(title="FleetFlow API", description="REST API for managing FleetFlow operations", version="1.0")
app.add_middleware(RequestLoggingMiddleware)
app.include_router(audit_router, prefix=API_PREFIX)
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(customers_router, prefix=API_PREFIX)
app.include_router(packages_router, prefix=API_PREFIX)
app.include_router(routes_router, prefix=API_PREFIX)
app.include_router(trucks_router, prefix=API_PREFIX)
app.include_router(state_router, prefix=API_PREFIX)
register_exception_handlers(app)
logger.info("FleetFlow FastAPI app configured with API prefix %s.", API_PREFIX)
