"""Stable operation names used when recording authorization decisions."""

from enum import StrEnum


class AuthorizationOperation(StrEnum):
    """Identify the application workflow an actor attempted to perform.

    Operation values use a ``resource.operation`` convention and are
    intentionally distinct from permissions and audit actions. Permissions
    describe what capability was required, while the audit action records the
    outcome, such as ``authorization_denied``.
    """

    # Package workflows.
    PACKAGE_CREATE = "package.create"
    PACKAGE_VIEW = "package.view"
    PACKAGE_LIST = "package.list"
    PACKAGE_LIST_UNASSIGNED = "package.list_unassigned"
    PACKAGE_FIND_SUITABLE_ROUTES = "package.find_suitable_routes"
    PACKAGE_REMOVE = "package.remove"

    # Route workflows.
    ROUTE_CREATE = "route.create"
    ROUTE_VIEW = "route.view"
    ROUTE_LIST = "route.list"
    ROUTE_LIST_IN_PROGRESS = "route.list_in_progress"
    ROUTE_FIND_SUITABLE_TRUCKS = "route.find_suitable_trucks"
    ROUTE_ASSIGN_TRUCK = "route.assign_truck"
    ROUTE_ASSIGN_PACKAGES = "route.assign_packages"
    ROUTE_REMOVE = "route.remove"

    # Truck and customer workflows.
    TRUCK_LIST = "truck.list"
    CUSTOMER_LIST = "customer.list"

    # Authentication and user-management workflows.
    USER_REGISTER = "user.register"
    USER_CHANGE_PASSWORD = "user.change_password"
    USER_RESET_PASSWORD = "user.reset_password"
    SESSION_END = "session.end"

    # World-state and audit workflows.
    WORLD_STATE_EXPORT = "world_state.export"
    WORLD_STATE_IMPORT = "world_state.import"
    AUDIT_LOG_VIEW = "audit_log.view"
