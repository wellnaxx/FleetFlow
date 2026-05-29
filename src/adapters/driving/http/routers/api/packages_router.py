from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.adapters.driven.persistence.database.errors import DatabaseError
from src.adapters.driving.http.dependencies.use_cases import (
    get_create_package_use_case,
    get_find_suitable_routes_for_package_use_case,
    get_remove_package_use_case,
    get_view_all_packages_use_case,
    get_view_package_use_case,
    get_view_unassigned_packages_use_case,
)
from src.adapters.driving.http.schemas.customers import CustomerResponse
from src.adapters.driving.http.schemas.packages import (
    PackageCreateRequest,
    PackagePageResponse,
    PackageResponse,
    PackageSuitableRouteResponse,
)
from src.application.exceptions.application_errors import ConflictError, NotFoundError, ValidationError
from src.application.use_cases.packages.create_package import CreatePackageUseCase
from src.application.use_cases.packages.remove_package import RemovePackageUseCase
from src.application.use_cases.packages.view_all_packages import ViewAllPackagesUseCase
from src.application.use_cases.packages.view_package import ViewPackageUseCase
from src.application.use_cases.packages.view_unassigned_packages import ViewUnassignedPackagesUseCase
from src.application.use_cases.pagination import PageQuery, PageResult
from src.application.use_cases.routes.find_suitable_routes_for_package import (
    FindSuitableRoutesForPackageUseCase,
)
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.exceptions import DomainConflictError, DomainValidationError, EntityNotFoundError

packages_router = APIRouter(prefix="/packages", tags=["packages"])


def _package_response(package: DeliveryPackage) -> PackageResponse:
    """Convert a DeliveryPackage entity to a PackageResponse model.

    Args:
        package: The DeliveryPackage entity to convert.

    Returns:
        A PackageResponse model representing the given package.

    Note:
        This function centralizes the mapping logic from the domain entity to the API response model,
        ensuring consistency across different endpoints that return package data.
    """
    return PackageResponse(
        start_location=str(package.start_location),
        end_location=str(package.end_location),
        weight=package.weight,
        package_id=package.package_id,
        status=package.status,
        current_location=str(package.current_location) if package.current_location else None,
        expected_arrival=package.expected_arrival,
        customer=CustomerResponse(
            customer_id=package.customer.customer_id,
            name=package.customer.name,
            email=package.customer.email,
            phone_number=package.customer.phone_number,
        ),
        route_id=package.route.route_id if package.route is not None else None,
    )


type PackagePageUseCase = ViewAllPackagesUseCase | ViewUnassignedPackagesUseCase


def _package_page_response(
    use_case: PackagePageUseCase,
    mapper: Callable[[DeliveryPackage], PackageResponse],
    limit: int,
    offset: int,
    include_total: bool,
) -> PackagePageResponse:
    """Build one paginated package response from a package listing use case."""
    try:
        result: PageResult[DeliveryPackage] = use_case.execute(
            PageQuery(limit=limit, offset=offset, include_total=include_total)
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database operation failed."
        ) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    items = [mapper(package) for package in result.items]
    return PackagePageResponse(
        items=items,
        total=result.total,
        count=result.count,
        limit=result.limit or limit,
        offset=result.offset,
    )


@packages_router.post("", status_code=status.HTTP_201_CREATED)
def create_package(
    request: PackageCreateRequest,
    use_case: Annotated[CreatePackageUseCase, Depends(get_create_package_use_case)],
) -> PackageResponse:
    """Create a new package delivery request.

    Args:
        request: The package creation request data.
        use_case: The use case for creating a package, injected by FastAPI.

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
        package = use_case.execute(
            start=request.start_location,
            end=request.end_location,
            weight=request.weight,
            name=request.customer_name,
            email=request.customer_email or "",
            phone=request.customer_phone_number or "",
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database operation failed."
        ) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except (ConflictError, DomainConflictError, EntityNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _package_response(package)


@packages_router.get("", status_code=status.HTTP_200_OK)
def list_packages(
    use_case: Annotated[ViewAllPackagesUseCase, Depends(get_view_all_packages_use_case)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    include_total: bool = False,
) -> PackagePageResponse:
    """List all packages.

    Args:
        use_case: Use case for listing packages, injected by FastAPI.
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
    return _package_page_response(use_case, _package_response, limit, offset, include_total)


@packages_router.get("/unassigned", status_code=status.HTTP_200_OK)
def list_unassigned_packages(
    use_case: Annotated[ViewUnassignedPackagesUseCase, Depends(get_view_unassigned_packages_use_case)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    include_total: bool = False,
) -> PackagePageResponse:
    """List all unassigned packages.

    Args:
        use_case: Use case for listing unassigned packages, injected by FastAPI.
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
    return _package_page_response(use_case, _package_response, limit, offset, include_total)


@packages_router.get("/{package_id}", status_code=status.HTTP_200_OK)
def get_package(
    package_id: int,
    use_case: Annotated[ViewPackageUseCase, Depends(get_view_package_use_case)],
) -> PackageResponse:
    """Get a specific package by its ID.

    Args:
        package_id: The ID of the package to retrieve.
        use_case: The use case for viewing a specific package, injected by FastAPI.

    Returns:
        A response model representing the requested package.

    Raises:
        HTTPException: Raised with:
            * 403 - Insufficient permissions.
            * 404 - Package not found.
            * 500 - Database operation failure.
    """
    try:
        package = use_case.execute(package_id=package_id)
        return _package_response(package)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database operation failed."
        ) from exc


@packages_router.get("/{package_id}/suitable-routes", status_code=status.HTTP_200_OK)
def find_suitable_routes_for_package(
    package_id: int,
    use_case: Annotated[
        FindSuitableRoutesForPackageUseCase, Depends(get_find_suitable_routes_for_package_use_case)
    ],
) -> list[PackageSuitableRouteResponse]:
    """Return routes that can currently carry the requested package.

    Args:
        package_id: Identifier of the package to place on a route.
        use_case: Use case for finding suitable routes, injected by FastAPI.

    Returns:
        Routes that can accept the requested package.

    Raises:
        HTTPException: Raised with:
            * 403 - Insufficient permissions.
            * 404 - Package not found.
            * 500 - Database operation failure.
    """
    try:
        results = use_case.execute(package_id=package_id)
        return [
            PackageSuitableRouteResponse(
                route_id=result.route_id,
                start_location=str(result.start_location),
                end_location=str(result.end_location),
                eta=result.eta,
                capacity_left=result.capacity_left,
                end_city=str(result.end_city),
            )
            for result in results
        ]
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database operation failed."
        ) from exc


@packages_router.delete("/{package_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_package(
    package_id: int,
    use_case: Annotated[RemovePackageUseCase, Depends(get_remove_package_use_case)],
) -> None:
    """Delete a package by its ID.

    Args:
        package_id: The ID of the package to delete.

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
        use_case.execute(package_id=package_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (DomainConflictError, EntityNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database operation failed."
        ) from exc
