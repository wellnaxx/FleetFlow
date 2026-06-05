"""Result models for assigning multiple packages to a route."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PackageAssignmentSuccess:
    """Successful package assignment details."""

    package_id: int
    route_id: int
    eta_text: str


@dataclass(frozen=True, slots=True)
class PackageAssignmentError:
    """Package assignment failure details."""

    package_id: int
    message: str


@dataclass(frozen=True, slots=True)
class AssignPackagesToRouteResult:
    """Batch assignment result split into successes and errors."""

    successes: list[PackageAssignmentSuccess]
    errors: list[PackageAssignmentError]
