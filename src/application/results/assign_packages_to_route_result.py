from dataclasses import dataclass


@dataclass
class PackageAssignmentSuccess:
    package_id: int
    route_id: int
    eta_text: str


@dataclass
class PackageAssignmentError:
    package_id: int
    message: str


@dataclass
class AssignPackagesToRouteResult:
    successes: list[PackageAssignmentSuccess]
    errors: list[PackageAssignmentError]
