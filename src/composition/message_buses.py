"""Construct fully registered in-process command and query buses.

This module is the composition boundary between typed message contracts,
their handlers, and the use-case instances owned by the application
container. Registration remains explicit so static analysis can verify each
key, handler input, and handler result relationship.

The builders return concrete mutable buses because registration is a startup
concern. The container should expose them to driving adapters through the
dispatch-only ``CommandBus`` and ``QueryBus`` input-port protocols.
"""

from src.application.commands.auth.change_password import CHANGE_OWN_PASSWORD
from src.application.commands.auth.login import LOGIN
from src.application.commands.auth.logout import LOGOUT
from src.application.commands.auth.register_user import REGISTER_USER
from src.application.commands.auth.reset_password import RESET_USER_PASSWORD
from src.application.commands.packages.create_package import CREATE_PACKAGE
from src.application.commands.packages.remove_package import REMOVE_PACKAGE
from src.application.commands.routes.assign_packages_to_route import ASSIGN_PACKAGES_TO_ROUTE
from src.application.commands.routes.assign_truck_to_route import ASSIGN_TRUCK_TO_ROUTE
from src.application.commands.routes.create_route import CREATE_ROUTE
from src.application.commands.routes.remove_route import REMOVE_ROUTE
from src.application.commands.state.load_world import LOAD_WORLD
from src.application.commands.state.save_world import SAVE_WORLD
from src.application.eventing.collector import EventCollector
from src.application.handlers.commands.packages.create_package import CreatePackageCommandHandler
from src.application.handlers.commands.packages.remove_package import RemovePackageCommandHandler
from src.application.handlers.commands.routes.assign_packages_to_route import (
    AssignPackagesToRouteCommandHandler,
)
from src.application.handlers.commands.routes.assign_truck_to_route import AssignTruckToRouteCommandHandler
from src.application.handlers.commands.routes.create_route import CreateRouteCommandHandler
from src.application.handlers.commands.routes.remove_route import RemoveRouteCommandHandler
from src.application.handlers.commands.state.load_world import LoadWorldCommandHandler
from src.application.handlers.commands.state.save_world import SaveWorldCommandHandler
from src.application.handlers.queries.customers.view_all_customers import ViewAllCustomersQueryHandler
from src.application.handlers.queries.fleet.get_fleet_overview import GetFleetOverviewQueryHandler
from src.application.handlers.queries.packages.view_all_packages import ViewAllPackagesQueryHandler
from src.application.handlers.queries.packages.view_package import ViewPackageQueryHandler
from src.application.handlers.queries.packages.view_unassigned_packages import (
    ViewUnassignedPackagesQueryHandler,
)
from src.application.handlers.queries.routes.find_suitable_routes_for_package import (
    FindSuitableRoutesForPackageQueryHandler,
)
from src.application.handlers.queries.routes.find_suitable_trucks_for_route import (
    FindSuitableTrucksForRouteQueryHandler,
)
from src.application.handlers.queries.routes.view_all_routes import ViewAllRoutesQueryHandler
from src.application.handlers.queries.routes.view_route import ViewRouteQueryHandler
from src.application.handlers.queries.routes.view_routes_in_progress import ViewRoutesInProgressQueryHandler
from src.application.handlers.queries.trucks.view_all_trucks import ViewAllTrucksQueryHandler
from src.application.messaging.executors.event_draining import EventDrainingExecutor
from src.application.messaging.in_process_command_bus import InProcessCommandBus
from src.application.messaging.in_process_query_bus import InProcessQueryBus
from src.application.queries.audit.view_audits import VIEW_AUDITS
from src.application.queries.auth.who_am_i import WHO_AM_I
from src.application.queries.customers.view_all_customers import VIEW_ALL_CUSTOMERS
from src.application.queries.fleet.get_fleet_overview import GET_FLEET_OVERVIEW
from src.application.queries.packages.view_all_packages import VIEW_ALL_PACKAGES
from src.application.queries.packages.view_package import VIEW_PACKAGE
from src.application.queries.packages.view_unassigned_packages import VIEW_UNASSIGNED_PACKAGES
from src.application.queries.routes.find_suitable_routes_for_package import FIND_SUITABLE_ROUTES_FOR_PACKAGE
from src.application.queries.routes.find_suitable_trucks_for_route import FIND_SUITABLE_TRUCKS_FOR_ROUTE
from src.application.queries.routes.view_all_routes import VIEW_ALL_ROUTES
from src.application.queries.routes.view_route import VIEW_ROUTE
from src.application.queries.routes.view_routes_in_progress import VIEW_ROUTES_IN_PROGRESS
from src.application.queries.trucks.view_all_trucks import VIEW_ALL_TRUCKS
from src.application.use_cases.use_case_registry import (
    AuditUseCases,
    AuthUseCases,
    CustomerUseCases,
    FleetUseCases,
    PackageUseCases,
    RouteUseCases,
    StateUseCases,
    TruckUseCases,
)


def build_command_bus(
    auth_cases: AuthUseCases,
    package_cases: PackageUseCases,
    route_cases: RouteUseCases,
    state_cases: StateUseCases,
    event_collector: EventCollector,
) -> InProcessCommandBus:
    """Build a command bus containing every application command handler.

    A fresh bus is created for each call. Handlers are constructed around the
    supplied use-case instances and registered under their canonical typed
    keys. Event-producing use cases that have migrated to direct message
    execution are wrapped so each dispatch drains its scoped events.

    Args:
        auth_cases: Authentication and account-management use cases.
        package_cases: Package-facing use cases.
        route_cases: Route-facing use cases.
        state_cases: World-state management use cases.
        event_collector: Collector used by event-aware command executors.

    Returns:
        Fresh in-process command bus with every published command registered.

    Raises:
        DuplicateMessageHandlerError: If two canonical command keys use the
            same routing name. This indicates invalid application composition.
    """

    bus = InProcessCommandBus()

    # Authentication and account management
    bus.register(
        LOGIN,
        EventDrainingExecutor(
            delegate=auth_cases.login,
            event_collector=event_collector,
        ),
    )
    bus.register(
        LOGOUT,
        EventDrainingExecutor(
            delegate=auth_cases.logout,
            event_collector=event_collector,
        ),
    )
    bus.register(
        REGISTER_USER,
        EventDrainingExecutor(
            delegate=auth_cases.register_user,
            event_collector=event_collector,
        ),
    )
    bus.register(
        CHANGE_OWN_PASSWORD,
        EventDrainingExecutor(
            delegate=auth_cases.change_password,
            event_collector=event_collector,
        ),
    )
    bus.register(
        RESET_USER_PASSWORD,
        EventDrainingExecutor(
            delegate=auth_cases.reset_password,
            event_collector=event_collector,
        ),
    )

    # Package management
    bus.register(CREATE_PACKAGE, CreatePackageCommandHandler(package_cases.create))
    bus.register(REMOVE_PACKAGE, RemovePackageCommandHandler(package_cases.remove))

    # Route management
    bus.register(CREATE_ROUTE, CreateRouteCommandHandler(route_cases.create))
    bus.register(REMOVE_ROUTE, RemoveRouteCommandHandler(route_cases.remove))
    bus.register(ASSIGN_PACKAGES_TO_ROUTE, AssignPackagesToRouteCommandHandler(route_cases.assign_packages))
    bus.register(ASSIGN_TRUCK_TO_ROUTE, AssignTruckToRouteCommandHandler(route_cases.assign_truck))

    # World state management
    bus.register(LOAD_WORLD, LoadWorldCommandHandler(state_cases.load))
    bus.register(SAVE_WORLD, SaveWorldCommandHandler(state_cases.save))

    return bus


def build_query_bus(
    audit_cases: AuditUseCases,
    auth_cases: AuthUseCases,
    customer_cases: CustomerUseCases,
    fleet_cases: FleetUseCases,
    package_cases: PackageUseCases,
    route_cases: RouteUseCases,
    truck_cases: TruckUseCases,
    event_collector: EventCollector,
) -> InProcessQueryBus:
    """Build a query bus containing every application query executor.

    A fresh bus is created for each call. Legacy handlers and directly
    registered use cases are bound under their canonical typed keys. Migrated
    event-aware workflows are decorated to drain their execution-local events
    when dispatched; no query executes during construction.

    Args:
        audit_cases: Audit-facing use cases.
        auth_cases: Authentication and account-management use cases.
        customer_cases: Customer-facing use cases.
        fleet_cases: Cross-aggregate fleet reporting use cases.
        package_cases: Package-facing use cases.
        route_cases: Route-facing use cases.
        truck_cases: Truck-facing use cases.
        event_collector: Collector injected into event-aware query executors.

    Returns:
        Fresh in-process query bus with every published query registered.

    Raises:
        DuplicateMessageHandlerError: If two canonical query keys use the
            same routing name. This indicates invalid application composition.
    """

    bus = InProcessQueryBus()

    # Audit queries
    bus.register(
        VIEW_AUDITS,
        EventDrainingExecutor(
            delegate=audit_cases.view_audit_logs,
            event_collector=event_collector,
        ),
    )

    # Authentication and account management
    bus.register(WHO_AM_I, auth_cases.who_am_i)

    # Customer-facing queries
    bus.register(VIEW_ALL_CUSTOMERS, ViewAllCustomersQueryHandler(customer_cases.view_all))

    # Cross-aggregate fleet reporting queries
    bus.register(GET_FLEET_OVERVIEW, GetFleetOverviewQueryHandler(fleet_cases.get_overview))

    # Package-facing queries
    bus.register(VIEW_ALL_PACKAGES, ViewAllPackagesQueryHandler(package_cases.view_all))
    bus.register(VIEW_PACKAGE, ViewPackageQueryHandler(package_cases.view))
    bus.register(VIEW_UNASSIGNED_PACKAGES, ViewUnassignedPackagesQueryHandler(package_cases.view_unassigned))

    # Route-facing queries
    bus.register(VIEW_ALL_ROUTES, ViewAllRoutesQueryHandler(route_cases.view_all))
    bus.register(VIEW_ROUTE, ViewRouteQueryHandler(route_cases.view))
    bus.register(VIEW_ROUTES_IN_PROGRESS, ViewRoutesInProgressQueryHandler(route_cases.view_in_progress))
    bus.register(
        FIND_SUITABLE_TRUCKS_FOR_ROUTE, FindSuitableTrucksForRouteQueryHandler(route_cases.find_suitable_trucks)
    )
    bus.register(
        FIND_SUITABLE_ROUTES_FOR_PACKAGE,
        FindSuitableRoutesForPackageQueryHandler(route_cases.find_suitable_routes),
    )

    # Truck-facing queries
    bus.register(VIEW_ALL_TRUCKS, ViewAllTrucksQueryHandler(truck_cases.view_all))

    return bus
