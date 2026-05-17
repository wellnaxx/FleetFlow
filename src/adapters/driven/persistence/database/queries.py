"""Typed query registry for all Postgres SQL queries.


Query groups are loaded lazily on first access and cached afterward.
Repositories reference this module rather than constructing or loading SQL
themselves.
"""

from dataclasses import dataclass
from functools import cached_property

from src.adapters.driven.persistence.database.loader import load_sql


@dataclass(frozen=True)
class CustomerQueries:
    add: str
    add_snapshot: str
    get_by_id: str
    get_by_email: str
    get_by_phone: str
    list_by_name: str
    list_all: str
    remove: str


@dataclass(frozen=True)
class RouteQueries:
    add: str
    add_snapshot: str
    add_stop: str
    get_by_id: str
    list_all: str
    remove: str
    update_state: str


@dataclass(frozen=True)
class PackageQueries:
    add: str
    add_snapshot: str
    get_by_id: str
    get_by_id_with_customer: str
    list_all: str
    list_all_with_customers: str
    list_by_route: str
    list_assigned: str
    list_unassigned: str
    remove: str
    update_state: str


@dataclass(frozen=True)
class TruckQueries:
    add: str
    get_by_id: str
    get_by_route_id: str
    get_by_id_with_route: str
    list_all: str
    list_all_with_route: str
    list_assigned: str
    update_state: str


@dataclass(frozen=True)
class UserQueries:
    add: str
    get_by_username: str
    get_by_id: str
    list_all: str
    update_password: str
    update_role: str
    increment_token_version_by_username: str
    increment_token_version_by_id: str


@dataclass(frozen=True)
class WorldStateQueries:
    clear_world: str
    get_snapshot_counters: str
    reset_customer_sequence: str
    reset_package_sequence: str
    reset_route_sequence: str


class QueryRegistry:
    """Lazy SQL query registry.

    SQL files are loaded when a repository first accesses that query group.
    This keeps one incomplete repository area from breaking unrelated imports.
    """

    @cached_property
    def customers(self) -> CustomerQueries:
        """Load customer SQL queries.

        Returns:
            Customer query collection.

        Raises:
            FileNotFoundError: If a customer SQL file is missing.
        """
        return CustomerQueries(
            add=load_sql("customers/add.sql"),
            add_snapshot=load_sql("customers/add_snapshot.sql"),
            get_by_id=load_sql("customers/get_by_id.sql"),
            get_by_email=load_sql("customers/get_by_email.sql"),
            get_by_phone=load_sql("customers/get_by_phone.sql"),
            list_by_name=load_sql("customers/list_by_name.sql"),
            list_all=load_sql("customers/list_all.sql"),
            remove=load_sql("customers/remove.sql"),
        )

    @cached_property
    def routes(self) -> RouteQueries:
        """Load route SQL queries.

        Returns:
            Route query collection.

        Raises:
            FileNotFoundError: If a route SQL file is missing.
        """
        return RouteQueries(
            add=load_sql("routes/add.sql"),
            add_snapshot=load_sql("routes/add_snapshot.sql"),
            add_stop=load_sql("routes/add_stop.sql"),
            get_by_id=load_sql("routes/get_by_id.sql"),
            list_all=load_sql("routes/list_all.sql"),
            remove=load_sql("routes/remove.sql"),
            update_state=load_sql("routes/update_state.sql"),
        )

    @cached_property
    def packages(self) -> PackageQueries:
        """Load package SQL queries.

        Returns:
            Package query collection.

        Raises:
            FileNotFoundError: If a package SQL file is missing.
        """
        return PackageQueries(
            add=load_sql("packages/add.sql"),
            add_snapshot=load_sql("packages/add_snapshot.sql"),
            get_by_id=load_sql("packages/get_by_id.sql"),
            get_by_id_with_customer=load_sql("packages/get_by_id_with_customer.sql"),
            list_all=load_sql("packages/list_all.sql"),
            list_all_with_customers=load_sql("packages/list_all_with_customers.sql"),
            list_by_route=load_sql("packages/list_by_route.sql"),
            list_assigned=load_sql("packages/list_assigned.sql"),
            list_unassigned=load_sql("packages/list_unassigned.sql"),
            remove=load_sql("packages/remove.sql"),
            update_state=load_sql("packages/update_state.sql"),
        )

    @cached_property
    def trucks(self) -> TruckQueries:
        """Load truck SQL queries.

        Returns:
            Truck query collection.

        Raises:
            FileNotFoundError: If a truck SQL file is missing.
        """
        return TruckQueries(
            add=load_sql("trucks/add.sql"),
            get_by_id=load_sql("trucks/get_by_id.sql"),
            get_by_route_id=load_sql("trucks/get_by_route_id.sql"),
            get_by_id_with_route=load_sql("trucks/get_by_id_with_route.sql"),
            list_all=load_sql("trucks/list_all.sql"),
            list_all_with_route=load_sql("trucks/list_all_with_route.sql"),
            list_assigned=load_sql("trucks/list_assigned.sql"),
            update_state=load_sql("trucks/update_state.sql"),
        )

    @cached_property
    def users(self) -> UserQueries:
        """Load user SQL queries.

        Returns:
            User query collection.

        Raises:
            FileNotFoundError: If a user SQL file is missing.
        """
        return UserQueries(
            add=load_sql("users/add.sql"),
            get_by_username=load_sql("users/get_by_username.sql"),
            get_by_id=load_sql("users/get_by_id.sql"),
            list_all=load_sql("users/list_all.sql"),
            update_password=load_sql("users/update_password.sql"),
            update_role=load_sql("users/update_role.sql"),
            increment_token_version_by_username=load_sql("users/increment_token_version_by_username.sql"),
            increment_token_version_by_id=load_sql("users/increment_token_version_by_id.sql"),
        )

    @cached_property
    def world_state(self) -> WorldStateQueries:
        """Load world-state SQL queries.

        Returns:
            World-state query collection.

        Raises:
            FileNotFoundError: If a world-state SQL file is missing.
        """
        return WorldStateQueries(
            clear_world=load_sql("world_state/clear_world.sql"),
            get_snapshot_counters=load_sql("world_state/get_snapshot_counters.sql"),
            reset_customer_sequence=load_sql("world_state/reset_customer_sequence.sql"),
            reset_package_sequence=load_sql("world_state/reset_package_sequence.sql"),
            reset_route_sequence=load_sql("world_state/reset_route_sequence.sql"),
        )


QUERIES = QueryRegistry()
