from fastapi import FastAPI

from src.adapters.driven.persistence.database.errors import DatabaseError
from src.adapters.driving.http.exception_handlers import (
    authentication_error_handler,
    business_rule_violation_error_handler,
    conflict_error_handler,
    database_error_handler,
    domain_conflict_error_handler,
    domain_validation_error_handler,
    entity_not_found_error_handler,
    not_found_error_handler,
    permission_error_handler,
    validation_error_handler,
    world_state_corruption_error_handler,
    world_state_file_not_found_error_handler,
    world_state_persistence_error_handler,
    world_state_runtime_swap_error_handler,
)
from src.adapters.driving.http.routers.api.auth_router import auth_router
from src.adapters.driving.http.routers.api.customers_router import customers_router
from src.adapters.driving.http.routers.api.packages_router import packages_router
from src.adapters.driving.http.routers.api.routes_router import routes_router
from src.adapters.driving.http.routers.api.state_router import state_router
from src.adapters.driving.http.routers.api.trucks_router import trucks_router
from src.application.exceptions.application_errors import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from src.application.exceptions.world_state_errors import (
    WorldStateCorruptionError,
    WorldStateFileNotFoundError,
    WorldStatePersistenceError,
    WorldStateRuntimeSwapError,
)
from src.domain.exceptions import (
    BusinessRuleViolationError,
    DomainConflictError,
    DomainValidationError,
    EntityNotFoundError,
)

API_PREFIX = "/api"

app = FastAPI(title="FleetFlow API", description="REST API for managing FleetFlow operations", version="1.0")
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(customers_router, prefix=API_PREFIX)
app.include_router(packages_router, prefix=API_PREFIX)
app.include_router(routes_router, prefix=API_PREFIX)
app.include_router(trucks_router, prefix=API_PREFIX)
app.include_router(state_router, prefix=API_PREFIX)

app.add_exception_handler(AuthenticationError, authentication_error_handler)
app.add_exception_handler(BusinessRuleViolationError, business_rule_violation_error_handler)
app.add_exception_handler(ConflictError, conflict_error_handler)
app.add_exception_handler(DatabaseError, database_error_handler)
app.add_exception_handler(DomainConflictError, domain_conflict_error_handler)
app.add_exception_handler(DomainValidationError, domain_validation_error_handler)
app.add_exception_handler(EntityNotFoundError, entity_not_found_error_handler)
app.add_exception_handler(NotFoundError, not_found_error_handler)
app.add_exception_handler(PermissionError, permission_error_handler)
app.add_exception_handler(ValidationError, validation_error_handler)
app.add_exception_handler(WorldStateCorruptionError, world_state_corruption_error_handler)
app.add_exception_handler(WorldStateFileNotFoundError, world_state_file_not_found_error_handler)
app.add_exception_handler(WorldStatePersistenceError, world_state_persistence_error_handler)
app.add_exception_handler(WorldStateRuntimeSwapError, world_state_runtime_swap_error_handler)
