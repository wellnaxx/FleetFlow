"""Use case for listing all routes."""

from src.application.services.authorization_service import AuthorizationService, requires
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.application.use_cases.pagination import (
    PageQuery,
    PageResult,
    validate_page,
    validate_unpaginated_offset,
)
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.enums.auth import Permission
from src.ports.output.route_repository import RouteRepositoryPort


class ViewAllRoutesUseCase(AuthorizedUseCase[PageResult[DeliveryRoute]]):
    """List all routes from the repository."""

    def __init__(self, routes: RouteRepositoryPort, authz: AuthorizationService) -> None:
        """Initialize the use case.

        Args:
            routes: Repository used to list routes.
            authz: Service used for authorization checks.
        """
        super().__init__(authz)
        self._routes = routes

    @requires(Permission.ROUTE_VIEW_ALL)
    def execute(self, query: PageQuery = PageQuery()) -> PageResult[DeliveryRoute]:
        """Return all persisted routes.

        Args:
            query: Pagination request. Defaults to a full uncounted list.

        Returns:
            Route page result.

        Raises:
            PermissionError: If the caller lacks routes view permission.
            DatabaseError: If the route listing persistence fails.
            ValidationError: If pagination arguments are invalid.
        """
        if query.limit is None:
            validate_unpaginated_offset(query.offset)
            return PageResult(
                items=tuple(self._routes.list_all()),
                total=None,
                limit=None,
                offset=query.offset,
            )

        validate_page(query.limit, query.offset)
        if query.include_total:
            routes, total = self._routes.list_page_with_total(limit=query.limit, offset=query.offset)
        else:
            routes = self._routes.list_page(limit=query.limit, offset=query.offset)
            total = None

        return PageResult(
            items=tuple(routes),
            total=total,
            limit=query.limit,
            offset=query.offset,
        )
