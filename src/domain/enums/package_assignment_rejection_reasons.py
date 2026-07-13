"""Normalized reasons why package assignment policy rejects a candidate."""

from enum import StrEnum


class PackageAssignmentRejectionReason(StrEnum):
    """Machine-readable package-to-route assignment rejection categories."""

    LOCATIONS_NOT_ON_ROUTE = "LOCATIONS_NOT_ON_ROUTE"
    LOCATIONS_OUT_OF_ORDER = "LOCATIONS_OUT_OF_ORDER"
    PICKUP_ALREADY_PASSED = "PICKUP_ALREADY_PASSED"
    TRUCK_CAPACITY_EXCEEDED = "TRUCK_CAPACITY_EXCEEDED"
    TRUCK_RANGE_INSUFFICIENT = "TRUCK_RANGE_INSUFFICIENT"

    # Reserved for domain rules that are not enforced yet.
    PACKAGE_ALREADY_ASSIGNED = "PACKAGE_ALREADY_ASSIGNED"
    ROUTE_ALREADY_COMPLETED = "ROUTE_ALREADY_COMPLETED"
