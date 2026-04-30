"""Typed query registry for all Postgres SQL queries.

All queries are loaded once at import time. Repositories reference
this module rather than constructing or loading SQL themselves.
"""

from dataclasses import dataclass

from src.adapters.driven.persistence.database.loader import load_sql


@dataclass(frozen=True)
class CustomerQueries:
    add: str
    get_by_id: str
    get_by_email: str
    get_by_phone: str
    list_by_name: str
    list_all: str
    remove: str


@dataclass(frozen=True)
class RouteQueries:
    add: str
    add_stop: str
    get_by_id: str
    list_all: str
    remove: str
    update_status: str
    update_truck: str


@dataclass(frozen=True)
class PackageQueries:
    add: str
    get_by_id: str
    list_all: str
    list_by_route: str
    list_unassigned: str
    remove: str
    update_status: str
    update_route: str


@dataclass(frozen=True)
class TruckQueries:
    get_by_id: str
    list_all: str
    update_state: str


@dataclass(frozen=True)
class UserQueries:
    add: str
    get_by_username: str
    get_by_id: str
    list_all: str
    update_password: str
    update_role: str


@dataclass(frozen=True)
class QueryRegistry:
    customers: CustomerQueries
    routes: RouteQueries
    packages: PackageQueries
    trucks: TruckQueries
    users: UserQueries


QUERIES = QueryRegistry(
    customers=CustomerQueries(
        add=load_sql("customers/add.sql"),
        get_by_id=load_sql("customers/get_by_id.sql"),
        get_by_email=load_sql("customers/get_by_email.sql"),
        get_by_phone=load_sql("customers/get_by_phone.sql"),
        list_by_name=load_sql("customers/list_by_name.sql"),
        list_all=load_sql("customers/list_all.sql"),
        remove=load_sql("customers/remove.sql"),
    ),
    routes=RouteQueries(
        add=load_sql("routes/add.sql"),
        add_stop=load_sql("routes/add_stop.sql"),
        get_by_id=load_sql("routes/get_by_id.sql"),
        list_all=load_sql("routes/list_all.sql"),
        remove=load_sql("routes/remove.sql"),
        update_status=load_sql("routes/update_status.sql"),
        update_truck=load_sql("routes/update_truck.sql"),
    ),
    packages=PackageQueries(
        add=load_sql("packages/add.sql"),
        get_by_id=load_sql("packages/get_by_id.sql"),
        list_all=load_sql("packages/list_all.sql"),
        list_by_route=load_sql("packages/list_by_route.sql"),
        list_unassigned=load_sql("packages/list_unassigned.sql"),
        remove=load_sql("packages/remove.sql"),
        update_status=load_sql("packages/update_status.sql"),
        update_route=load_sql("packages/update_route.sql"),
    ),
    trucks=TruckQueries(
        get_by_id=load_sql("trucks/get_by_id.sql"),
        list_all=load_sql("trucks/list_all.sql"),
        update_state=load_sql("trucks/update_state.sql"),
    ),
    users=UserQueries(
        add=load_sql("users/add.sql"),
        get_by_username=load_sql("users/get_by_username.sql"),
        get_by_id=load_sql("users/get_by_id.sql"),
        list_all=load_sql("users/list_all.sql"),
        update_password=load_sql("users/update_password.sql"),
        update_role=load_sql("users/update_role.sql"),
    ),
)