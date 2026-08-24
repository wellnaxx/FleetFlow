"""FastAPI dependency builders for application use cases."""

from typing import Annotated

from fastapi import Depends

from src.adapters.driving.http.dependencies.auth import AuthenticatedHTTPPrincipal, get_current_user
from src.application.use_cases.routes.view_all_routes import ViewAllRoutesUseCase
from src.application.use_cases.routes.view_route import ViewRouteUseCase
from src.application.use_cases.routes.view_routes_in_progress import ViewRoutesInProgressUseCase
from src.application.use_cases.state.advance_world_state import AdvanceWorldStateUseCase
from src.application.use_cases.state.load_world import LoadWorldStateUseCase
from src.application.use_cases.state.save_world import SaveWorldStateUseCase
from src.application.use_cases.trucks.view_all_trucks import ViewAllTrucksUseCase
from src.composition.container import Container
from src.composition.runtime import get_container


def get_view_all_routes_use_case(
    principal: Annotated[AuthenticatedHTTPPrincipal, Depends(get_current_user)],
    container: Annotated[Container, Depends(get_container)],
) -> ViewAllRoutesUseCase:
    """Build the route-listing use case for the authenticated request.

    Args:
        principal: Authenticated HTTP principal carrying request-scoped authorization.
        container: Application dependency container.

    Returns:
        Route-listing use case bound to the route repository.

    Raises:
        HTTPException: Raised by `get_current_user` when authentication fails.
    """
    return ViewAllRoutesUseCase(container.route_repo, authz=principal.authz)


def get_view_routes_in_progress_use_case(
    principal: Annotated[AuthenticatedHTTPPrincipal, Depends(get_current_user)],
    container: Annotated[Container, Depends(get_container)],
) -> ViewRoutesInProgressUseCase:
    """Build the in-progress route listing use case for the authenticated request.

    Args:
        principal: Authenticated HTTP principal carrying request-scoped authorization.
        container: Application dependency container.

    Returns:
        In-progress route listing use case bound to the route repository.

    Raises:
        HTTPException: Raised by `get_current_user` when authentication fails.
    """
    return ViewRoutesInProgressUseCase(container.route_repo, authz=principal.authz)


def get_view_route_use_case(
    principal: Annotated[AuthenticatedHTTPPrincipal, Depends(get_current_user)],
    container: Annotated[Container, Depends(get_container)],
) -> ViewRouteUseCase:
    """Build the route-detail use case for the authenticated request.

    Args:
        principal: Authenticated HTTP principal carrying request-scoped authorization.
        container: Application dependency container.

    Returns:
        Route-detail use case bound to the route repository.

    Raises:
        HTTPException: Raised by `get_current_user` when authentication fails.
    """
    return ViewRouteUseCase(container.route_repo, authz=principal.authz)


def get_view_all_trucks_use_case(
    principal: Annotated[AuthenticatedHTTPPrincipal, Depends(get_current_user)],
    container: Annotated[Container, Depends(get_container)],
) -> ViewAllTrucksUseCase:
    """Build the truck-listing use case for the authenticated request.

    Args:
        principal: Authenticated HTTP principal carrying request-scoped authorization.
        container: Application dependency container.

    Returns:
        Truck-listing use case bound to the vehicle manager.

    Raises:
        HTTPException: Raised by `get_current_user` when authentication fails.
    """
    return ViewAllTrucksUseCase(container.vehicle_manager, authz=principal.authz)


def get_advance_world_state_use_case(
    container: Annotated[Container, Depends(get_container)],
) -> AdvanceWorldStateUseCase:
    """Build the world-state advancement use case for an HTTP request.

    Args:
        container: Application dependency container.

    Returns:
        World-state advancement use case bound to the heartbeat service.
    """
    return AdvanceWorldStateUseCase(container.heartbeat_service)


def get_save_world_state_use_case(
    principal: Annotated[AuthenticatedHTTPPrincipal, Depends(get_current_user)],
    container: Annotated[Container, Depends(get_container)],
) -> SaveWorldStateUseCase:
    """Build the world-state save use case for the authenticated request.

    Args:
        principal: Authenticated HTTP principal carrying request-scoped authorization.
        container: Application dependency container.

    Returns:
        World-state save use case bound to snapshot gateway and persistence.

    Raises:
        HTTPException: Raised by `get_current_user` when authentication fails.
    """
    return SaveWorldStateUseCase(
        container.world_state_gateway,
        container.world_state_persistence,
        authz=principal.authz,
    )


def get_load_world_state_use_case(
    principal: Annotated[AuthenticatedHTTPPrincipal, Depends(get_current_user)],
    container: Annotated[Container, Depends(get_container)],
) -> LoadWorldStateUseCase:
    """Build the world-state load use case for the authenticated request.

    Args:
        principal: Authenticated HTTP principal carrying request-scoped authorization.
        container: Application dependency container.

    Returns:
        World-state load use case bound to snapshot gateway and persistence.

    Raises:
        HTTPException: Raised by `get_current_user` when authentication fails.
    """
    return LoadWorldStateUseCase(
        container.world_state_gateway,
        container.world_state_persistence,
        authz=principal.authz,
    )
