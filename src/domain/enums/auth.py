"""Authentication roles, permissions, and role-permission mapping."""

from enum import Enum, auto


class Role(Enum):
    """Runtime authorization roles."""

    EMPLOYEE = "EMPLOYEE"
    MANAGER = "MANAGER"


class Permission(Enum):
    """Enumerates app capabilities used by RBAC checks."""

    PACKAGE_CREATE = auto()
    PACKAGE_VIEW = auto()
    PACKAGE_VIEW_ALL = auto()
    PACKAGE_FIND_ROUTE_FOR = auto()
    PACKAGE_VIEW_UNASSIGNED = auto()
    PACKAGE_REMOVE = auto()

    ROUTE_CREATE = auto()
    ROUTE_VIEW_IN_PROGRESS = auto()
    ROUTE_VIEW = auto()
    ROUTE_VIEW_ALL = auto()
    ROUTE_FIND_TRUCK_FOR = auto()
    ROUTE_ASSIGN_TRUCK = auto()
    ROUTE_ASSIGN_PACKAGE = auto()
    ROUTE_REMOVE = auto()

    TRUCK_VIEW = auto()

    CUSTOMER_VIEW = auto()

    ADMIN_USER = auto()
    APP_SAVE_STATE = auto()
    APP_LOAD_STATE = auto()


_EMPLOYEE_PERMISSIONS: frozenset[Permission] = frozenset(
    {
        Permission.PACKAGE_CREATE,
        Permission.PACKAGE_VIEW,
        Permission.PACKAGE_VIEW_ALL,
        Permission.PACKAGE_VIEW_UNASSIGNED,
        Permission.PACKAGE_FIND_ROUTE_FOR,
        Permission.PACKAGE_REMOVE,
        Permission.ROUTE_CREATE,
        Permission.ROUTE_VIEW,
        Permission.ROUTE_VIEW_ALL,
        Permission.ROUTE_VIEW_IN_PROGRESS,
        Permission.ROUTE_FIND_TRUCK_FOR,
        Permission.ROUTE_ASSIGN_TRUCK,
        Permission.ROUTE_ASSIGN_PACKAGE,
        Permission.ROUTE_REMOVE,
        Permission.TRUCK_VIEW,
        Permission.CUSTOMER_VIEW,
    }
)

_MANAGER_PERMISSIONS: frozenset[Permission] = _EMPLOYEE_PERMISSIONS | frozenset(
    {
        Permission.ADMIN_USER,
        Permission.APP_SAVE_STATE,
        Permission.APP_LOAD_STATE,
    }
)

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.EMPLOYEE: _EMPLOYEE_PERMISSIONS,
    Role.MANAGER: _MANAGER_PERMISSIONS,
}
