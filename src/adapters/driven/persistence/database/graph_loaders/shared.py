"""Shared graph hydration helpers for Postgres loaders."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.adapters.driven.persistence.database.mappers import (
    as_package_row,
    as_route_row,
    as_route_stop_row,
    map_customer,
    map_customer_from_package_row,
    map_package,
    map_route,
    map_truck,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from src.adapters.driven.persistence.database.executor import RowDict
    from src.domain.entities.customer import Customer
    from src.domain.entities.delivery_package import DeliveryPackage
    from src.domain.entities.delivery_route import DeliveryRoute
    from src.domain.entities.truck import Truck


def map_customers(rows: list[RowDict]) -> dict[int, Customer]:
    """Map customer rows into canonical customer objects.

    Args:
        rows: Customer rows returned by the database.

    Returns:
        Customers keyed by customer id.

    Raises:
        KeyError: If a required customer column is missing.
        TypeError: If a required customer column has an unexpected type.
        ValueError: If duplicate customer ids or invalid contact data are found.
    """
    customers: dict[int, Customer] = {}

    for row in rows:
        customer = map_customer(row)

        if customer.customer_id in customers:
            raise ValueError(f"Duplicate customer_id {customer.customer_id} in persisted data.")

        customers[customer.customer_id] = customer

    return customers


def map_routes(rows: list[RowDict]) -> tuple[dict[int, DeliveryRoute], dict[int, int | None]]:
    """Map route/stop rows into route objects and remembered truck ids.

    Args:
        rows: Route rows joined with route stop rows.

    Returns:
        Routes keyed by route id and assigned truck ids keyed by route id.

    Raises:
        KeyError: If a required route or stop column is missing.
        TypeError: If a required route or stop column has an unexpected type.
        ValueError: If repeated route rows contain inconsistent truck ids.
    """
    rows_by_route_id: dict[int, list[RowDict]] = {}
    truck_ids_by_route_id: dict[int, int | None] = {}

    for row in rows:
        route_row = as_route_row(row)
        route_id = route_row["route_id"]
        truck_vehicle_id = route_row["truck_vehicle_id"]

        rows_by_route_id.setdefault(route_id, []).append(row)

        if route_id in truck_ids_by_route_id and truck_ids_by_route_id[route_id] != truck_vehicle_id:
            raise ValueError(
                f"Route {route_id} has inconsistent truck_vehicle_id values: "
                f"{truck_ids_by_route_id[route_id]!r} and {truck_vehicle_id!r}."
            )

        truck_ids_by_route_id[route_id] = truck_vehicle_id

    routes = {
        route_id: map_route(sorted(route_rows, key=route_stop_order))
        for route_id, route_rows in rows_by_route_id.items()
    }

    return routes, truck_ids_by_route_id


def route_stop_order(row: RowDict) -> int:
    """Return a validated route stop order.

    Args:
        row: Route/stop row returned by the database.

    Returns:
        Stop order.

    Raises:
        KeyError: If the stop_order column is missing.
        TypeError: If stop_order is not an integer.
    """
    return as_route_stop_row(row)["stop_order"]


def map_trucks(rows: list[RowDict]) -> dict[int, Truck]:
    """Map truck rows into canonical truck objects.

    Args:
        rows: Truck rows returned by the database.

    Returns:
        Trucks keyed by vehicle id.

    Raises:
        KeyError: If a required truck column is missing.
        TypeError: If a required truck column has an unexpected type.
        ValueError: If duplicate truck ids or invalid truck data are found.
    """
    trucks: dict[int, Truck] = {}

    for row in rows:
        truck = map_truck(row)

        if truck.vehicle_id in trucks:
            raise ValueError(f"Duplicate vehicle_id {truck.vehicle_id} in persisted data.")

        trucks[truck.vehicle_id] = truck

    return trucks


def map_packages_with_existing_customers(
    rows: list[RowDict],
    customers: dict[int, Customer],
) -> tuple[dict[int, DeliveryPackage], dict[int, int | None]]:
    """Map package rows using already-mapped canonical customers.

    Args:
        rows: Package rows returned by the database.
        customers: Previously mapped customers keyed by customer id.

    Returns:
        Packages keyed by package id and route ids keyed by package id.

    Raises:
        KeyError: If a required package column is missing.
        TypeError: If a required package column has an unexpected type.
        ValueError: If a package references a missing customer or duplicate package ids exist.
    """
    packages: dict[int, DeliveryPackage] = {}
    route_ids_by_package_id: dict[int, int | None] = {}

    for row in rows:
        package_row = as_package_row(row)
        package_id = package_row["package_id"]
        customer_id = package_row["customer_id"]
        route_id = package_row["route_id"]

        customer = customers.get(customer_id)
        if customer is None:
            raise ValueError(f"Package {package_id} references missing customer {customer_id}.")

        package = map_package(row, customer)

        if package.package_id in packages:
            raise ValueError(f"Duplicate package_id {package.package_id} in persisted data.")

        customer.restore_package_link(package)
        packages[package.package_id] = package
        route_ids_by_package_id[package.package_id] = route_id

    return packages, route_ids_by_package_id


def map_joined_package_rows(
    rows: list[RowDict],
    *,
    expected_route_id: int | None = None,
) -> tuple[dict[int, DeliveryPackage], dict[int, Customer], dict[int, int]]:
    """Map assigned package/customer rows into canonical objects.

    Args:
        rows: Package rows joined with customer columns.
        expected_route_id: Required route id for every package row, or `None`
            when loading packages for multiple routes.

    Returns:
        Packages keyed by package id, customers keyed by customer id, and
        route ids keyed by package id.

    Raises:
        KeyError: If a required package or customer column is missing.
        TypeError: If a required package or customer column has an unexpected type.
        ValueError: If duplicate package ids, missing route ids, wrong route ids,
            or inconsistent customer rows are found.
    """
    packages: dict[int, DeliveryPackage] = {}
    customers: dict[int, Customer] = {}
    route_ids_by_package_id: dict[int, int] = {}

    for row in rows:
        package_row = as_package_row(row)
        package_id = package_row["package_id"]
        route_id = package_row["route_id"]

        if route_id is None:
            raise ValueError(f"Assigned package {package_id} has no route_id in persisted data.")

        if expected_route_id is not None and route_id != expected_route_id:
            raise ValueError(
                f"Package {package_id} belongs to route {route_id}, "
                f"but route {expected_route_id} was requested."
            )

        if package_id in packages:
            raise ValueError(f"Duplicate package_id {package_id} in persisted data.")

        row_customer = map_customer_from_package_row(row)
        customer = customers.get(row_customer.customer_id)

        if customer is None:
            customer = row_customer
            customers[customer.customer_id] = customer
        else:
            validate_same_customer(customer, row_customer)

        package = map_package(row, customer)
        customer.restore_package_link(package)

        packages[package.package_id] = package
        route_ids_by_package_id[package.package_id] = route_id

    return packages, customers, route_ids_by_package_id


def validate_same_customer(existing: Customer, incoming: Customer) -> None:
    """Validate that two customer objects represent the same persisted customer.

    Args:
        existing: Previously mapped customer.
        incoming: Newly mapped customer from another joined package row.

    Returns:
        None.

    Raises:
        ValueError: If the customer rows conflict.
    """
    if existing.customer_id != incoming.customer_id:
        raise ValueError(f"Customer id mismatch: {existing.customer_id} and {incoming.customer_id}.")

    if (
        existing.contact.name != incoming.contact.name
        or existing.contact.email != incoming.contact.email
        or existing.contact.phone_number != incoming.contact.phone_number
    ):
        raise ValueError(f"Customer {existing.customer_id} has inconsistent data in persisted packages.")


def link_route_truck(route: DeliveryRoute, truck: Truck | None) -> None:
    """Restore one route/truck bidirectional link.

    Args:
        route: Route being hydrated.
        truck: Assigned truck, or `None`.

    Returns:
        None.
    """
    if truck is None:
        return

    route.truck = truck
    truck.route = route


def link_route_trucks(
    routes: dict[int, DeliveryRoute],
    trucks: dict[int, Truck],
    route_truck_ids: Mapping[int, int | None],
) -> None:
    """Restore route/truck links for many routes.

    Args:
        routes: Routes keyed by route id.
        trucks: Trucks keyed by vehicle id.
        route_truck_ids: Assigned truck ids keyed by route id.

    Returns:
        None.

    Raises:
        ValueError: If a truck mapping references a missing route or truck.
    """
    for route_id, vehicle_id in route_truck_ids.items():
        if vehicle_id is None:
            continue

        route = routes.get(route_id)
        if route is None:
            raise ValueError(f"Route truck mapping references missing route {route_id}.")

        truck = trucks.get(vehicle_id)
        if truck is None:
            raise ValueError(f"Route {route_id} references missing truck {vehicle_id}.")

        link_route_truck(route, truck)


def link_route_packages(route: DeliveryRoute, packages: dict[int, DeliveryPackage]) -> None:
    """Restore package links for one route.

    Args:
        route: Route being hydrated.
        packages: Packages assigned to the route.

    Returns:
        None.
    """
    for package in packages.values():
        route.restore_package_link(package, refresh_expected_arrival=False)


def link_packages_to_routes(
    routes: dict[int, DeliveryRoute],
    packages: dict[int, DeliveryPackage],
    package_route_ids: Mapping[int, int | None],
) -> None:
    """Restore route/package bidirectional links.

    Args:
        routes: Routes keyed by route id.
        packages: Packages keyed by package id.
        package_route_ids: Assigned route ids keyed by package id.

    Returns:
        None.

    Raises:
        ValueError: If a package references a missing route.
    """
    for package_id, route_id in package_route_ids.items():
        if route_id is None:
            continue

        route = routes.get(route_id)
        if route is None:
            raise ValueError(f"Package {package_id} references missing route {route_id}.")

        route.restore_package_link(packages[package_id], refresh_expected_arrival=False)
