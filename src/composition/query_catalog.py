"""Authoritative catalog of concrete queries accepted by the application.

Composition tests compare this catalog with query-bus registrations so a new
query cannot silently remain undispatchable. Runtime dispatch continues to
use each query's typed key; this catalog is not a service locator.
"""

from src.application.messaging.query import Query
from src.application.models.audit_log_query import AuditLogQuery
from src.application.queries.auth.who_am_i import WhoAmIQuery
from src.application.queries.customers.view_all_customers import ViewAllCustomersQuery
from src.application.queries.fleet.get_fleet_overview import GetFleetOverviewQuery
from src.application.queries.packages.view_all_packages import ViewAllPackagesQuery
from src.application.queries.packages.view_package import ViewPackageQuery
from src.application.queries.packages.view_unassigned_packages import ViewUnassignedPackagesQuery
from src.application.queries.routes.find_suitable_routes_for_package import FindSuitableRoutesForPackageQuery
from src.application.queries.routes.find_suitable_trucks_for_route import FindSuitableTrucksForRouteQuery
from src.application.queries.routes.view_all_routes import ViewAllRoutesQuery
from src.application.queries.routes.view_route import ViewRouteQuery
from src.application.queries.routes.view_routes_in_progress import ViewRoutesInProgressQuery
from src.application.queries.trucks.view_all_trucks import ViewAllTrucksQuery

# Keep this tuple synchronized with the explicit bindings in message_buses.
PUBLISHED_QUERY_TYPES: tuple[type[Query], ...] = (
    AuditLogQuery,
    WhoAmIQuery,
    ViewAllCustomersQuery,
    GetFleetOverviewQuery,
    ViewAllPackagesQuery,
    ViewPackageQuery,
    ViewUnassignedPackagesQuery,
    ViewAllRoutesQuery,
    ViewRouteQuery,
    ViewRoutesInProgressQuery,
    FindSuitableTrucksForRouteQuery,
    FindSuitableRoutesForPackageQuery,
    ViewAllTrucksQuery,
)
