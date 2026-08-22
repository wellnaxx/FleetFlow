from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.adapters.driving.http.dependencies.eventing import execute_and_drain_events, get_event_collector
from src.adapters.driving.http.dependencies.message_buses import (
    get_authenticated_command_bus,
    get_authenticated_query_bus,
)
from src.adapters.driving.http.dependencies.use_cases import (
    get_find_suitable_routes_for_package_use_case,
)
from src.adapters.driving.http.schemas.packages import (
    PackageCreateRequest,
    PackagePageResponse,
    PackageResponse,
    PackageSuitableRouteResponse,
)
from src.application.commands.packages.create_package import CREATE_PACKAGE, CreatePackageCommand
from src.application.commands.packages.remove_package import REMOVE_PACKAGE, RemovePackageCommand
from src.application.eventing.collector import EventCollector
from src.application.exceptions.application_errors import ConflictError
from src.application.queries.packages.view_all_packages import VIEW_ALL_PACKAGES, ViewAllPackagesQuery
from src.application.queries.packages.view_package import VIEW_PACKAGE, ViewPackageQuery
from src.application.queries.packages.view_unassigned_packages import (
    VIEW_UNASSIGNED_PACKAGES,
    ViewUnassignedPackagesQuery,
)
from src.application.use_cases.pagination import PageQuery
from src.application.use_cases.routes.find_suitable_routes_for_package import (
    FindSuitableRoutesForPackageUseCase,
)
from src.domain.exceptions import DomainConflictError, EntityNotFoundError
from src.ports.input.command_bus import CommandBus
from src.ports.input.query_bus import QueryBus

packages_router = APIRouter(prefix="/packages", tags=["packages"])


@packages_router.post("", status_code=status.HTTP_201_CREATED)
def create_package(
    request: PackageCreateRequest,
    command_bus: Annotated[CommandBus, Depends(get_authenticated_command_bus)],
) -> PackageResponse:
    """Create a new package delivery request.

    Args:
        request: The package creation request data.
        command_bus: Authenticated command bus injected by FastAPI. The
            registered executor owns application and domain-event publication.

    Returns:
        A response model representing the newly created package.

    Raises:
        HTTPException: Raised with:
            * 400 - Invalid package creation input.
            * 403 - Insufficient permissions.
            * 409 - Conflicting package/customer information or inconsistent ownership state.
            * 500 - Database operation failure.
    """
    try:
        package = command_bus.dispatch(
            key=CREATE_PACKAGE,
            command=CreatePackageCommand(
                start=request.start_location,
                end=request.end_location,
                weight=request.weight,
                name=request.customer_name,
                email=request.customer_email or "",
                phone=request.customer_phone_number or "",
            ),
        )
    except (ConflictError, DomainConflictError, EntityNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return PackageResponse.from_package(package)


@packages_router.get("", status_code=status.HTTP_200_OK)
def list_packages(
    query_bus: Annotated[QueryBus, Depends(get_authenticated_query_bus)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    include_total: bool = False,
) -> PackagePageResponse:
    """List all packages.

    Args:
        query_bus: Authenticated query bus injected by FastAPI. The registered
            executor owns authorization-event publication.
        limit: Maximum number of packages to return.
        offset: Number of packages to skip.
        include_total: Whether to include the total package count.

    Returns:
        A paginated package response.

    Raises:
        HTTPException: Raised with:
            * 400 - Invalid pagination input.
            * 403 - Insufficient permissions.
            * 500 - Database operation failure.
    """
    result = query_bus.dispatch(
        key=VIEW_ALL_PACKAGES,
        query=ViewAllPackagesQuery(page=PageQuery(limit=limit, offset=offset, include_total=include_total)),
    )
    return PackagePageResponse.from_page(result)


@packages_router.get("/unassigned", status_code=status.HTTP_200_OK)
def list_unassigned_packages(
    query_bus: Annotated[QueryBus, Depends(get_authenticated_query_bus)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    include_total: bool = False,
) -> PackagePageResponse:
    """List all unassigned packages.

    Args:
        query_bus: Authenticated query bus injected by FastAPI. The registered
            executor owns authorization-event publication.
        limit: Maximum number of packages to return.
        offset: Number of packages to skip.
        include_total: Whether to include the total package count.

    Returns:
        A paginated package response.

    Raises:
        HTTPException: Raised with:
            * 400 - Invalid pagination input.
            * 403 - Insufficient permissions.
            * 500 - Database operation failure.
    """
    result = query_bus.dispatch(
        key=VIEW_UNASSIGNED_PACKAGES,
        query=ViewUnassignedPackagesQuery(
            page=PageQuery(limit=limit, offset=offset, include_total=include_total)
        ),
    )
    return PackagePageResponse.from_page(result)


@packages_router.get("/{package_id}", status_code=status.HTTP_200_OK)
def get_package(
    package_id: int,
    query_bus: Annotated[QueryBus, Depends(get_authenticated_query_bus)],
) -> PackageResponse:
    """Get a specific package by its ID.

    Args:
        package_id: The ID of the package to retrieve.
        query_bus: Authenticated query bus injected by FastAPI. The registered
            executor owns authorization-event publication.

    Returns:
        A response model representing the requested package.

    Raises:
        HTTPException: Raised with:
            * 403 - Insufficient permissions.
            * 404 - Package not found.
            * 500 - Database operation failure.
    """
    package = query_bus.dispatch(
        key=VIEW_PACKAGE,
        query=ViewPackageQuery(package_id=package_id),
    )
    return PackageResponse.from_package(package)


@packages_router.get("/{package_id}/suitable-routes", status_code=status.HTTP_200_OK)
def find_suitable_routes_for_package(
    package_id: int,
    use_case: Annotated[
        FindSuitableRoutesForPackageUseCase, Depends(get_find_suitable_routes_for_package_use_case)
    ],
    event_collector: Annotated[EventCollector, Depends(get_event_collector)],
) -> list[PackageSuitableRouteResponse]:
    """Return routes that can currently carry the requested package.

    Args:
        package_id: Identifier of the package to place on a route.
        use_case: Use case for finding suitable routes, injected by FastAPI.
        event_collector: Collector used to publish authorization events.

    Returns:
        Routes that can accept the requested package.

    Raises:
        HTTPException: Raised with:
            * 403 - Insufficient permissions.
            * 404 - Package not found.
            * 500 - Database operation failure.
    """
    results = execute_and_drain_events(
        recorder=use_case,
        event_collector=event_collector,
        action=lambda: use_case.execute(package_id=package_id),
    )
    return [PackageSuitableRouteResponse.from_match(result) for result in results]


@packages_router.delete("/{package_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_package(
    package_id: int,
    command_bus: Annotated[CommandBus, Depends(get_authenticated_command_bus)],
) -> None:
    """Delete a package by its ID.

    Args:
        package_id: The ID of the package to delete.
        command_bus: Authenticated command bus injected by FastAPI. The
            registered executor owns authorization and domain-event
            publication.

    Returns:
        None

    Raises:
        HTTPException: Raised with:
            * 403 - Insufficient permissions.
            * 404 - Package not found.
            * 409 - Inconsistent package ownership or route assignment state.
            * 500 - Database operation failure.
    """
    try:
        command_bus.dispatch(
            key=REMOVE_PACKAGE,
            command=RemovePackageCommand(package_id=package_id),
        )
    except (DomainConflictError, EntityNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
