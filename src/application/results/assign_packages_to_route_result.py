"""Result models for assigning multiple packages to a route."""

from dataclasses import dataclass


@dataclass
class PackageAssignmentSuccess:
    """Successful package assignment details."""

    package_id: int
    route_id: int
    eta_text: str


@dataclass
class PackageAssignmentError:
    """Package assignment failure details."""

    package_id: int
    message: str


@dataclass
class AssignPackagesToRouteResult:
    """Batch assignment result split into successes and errors."""

    successes: list[PackageAssignmentSuccess]
    errors: list[PackageAssignmentError]
