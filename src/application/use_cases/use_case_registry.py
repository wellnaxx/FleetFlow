"""Typed groups of application use cases exposed by the composition root."""

from dataclasses import dataclass

from src.application.use_cases.auth.change_password import ChangePasswordUseCase
from src.application.use_cases.auth.login import LoginUseCase
from src.application.use_cases.auth.logout import LogoutUseCase
from src.application.use_cases.auth.register_user import RegisterUserUseCase
from src.application.use_cases.auth.who_am_i import WhoAmIUseCase
from src.application.use_cases.customers.view_all_customers import ViewAllCustomersUseCase
from src.application.use_cases.packages.create_package import CreatePackageUseCase
from src.application.use_cases.packages.remove_package import RemovePackageUseCase
from src.application.use_cases.packages.view_all_packages import ViewAllPackagesUseCase
from src.application.use_cases.packages.view_package import ViewPackageUseCase
from src.application.use_cases.packages.view_unassigned_packages import ViewUnassignedPackagesUseCase
from src.application.use_cases.routes.assign_packages_to_route import AssignPackagesToRouteUseCase
from src.application.use_cases.routes.assign_truck_to_route import AssignTruckToRouteUseCase
from src.application.use_cases.routes.create_route import CreateRouteUseCase
from src.application.use_cases.routes.find_suitable_routes_for_package import (
    FindSuitableRoutesForPackageUseCase,
)
from src.application.use_cases.routes.find_suitable_trucks_for_route import FindSuitableTrucksForRouteUseCase
from src.application.use_cases.routes.remove_route import RemoveRouteUseCase
from src.application.use_cases.routes.view_all_routes import ViewAllRoutesUseCase
from src.application.use_cases.routes.view_route import ViewRouteUseCase
from src.application.use_cases.routes.view_routes_in_progress import ViewRoutesInProgressUseCase
from src.application.use_cases.state.advance_world_state import AdvanceWorldStateUseCase
from src.application.use_cases.state.load_world import LoadWorldStateUseCase
from src.application.use_cases.state.save_world import SaveWorldStateUseCase
from src.application.use_cases.trucks.view_all_trucks import ViewAllTrucksUseCase


@dataclass(frozen=True)
class AuthUseCases:
    """Authentication and account-management use cases."""

    login: LoginUseCase
    logout: LogoutUseCase
    who_am_i: WhoAmIUseCase
    register_user: RegisterUserUseCase
    change_password: ChangePasswordUseCase


@dataclass(frozen=True)
class CustomerUseCases:
    """Customer-facing use cases."""

    view_all: ViewAllCustomersUseCase


@dataclass(frozen=True)
class PackageUseCases:
    """Package-facing use cases."""

    create: CreatePackageUseCase
    view: ViewPackageUseCase
    view_all: ViewAllPackagesUseCase
    remove: RemovePackageUseCase
    view_unassigned: ViewUnassignedPackagesUseCase


@dataclass(frozen=True)
class RouteUseCases:
    """Route-facing use cases."""

    create: CreateRouteUseCase
    view: ViewRouteUseCase
    view_all: ViewAllRoutesUseCase
    view_in_progress: ViewRoutesInProgressUseCase
    remove: RemoveRouteUseCase
    assign_packages: AssignPackagesToRouteUseCase
    assign_truck: AssignTruckToRouteUseCase
    find_suitable_trucks: FindSuitableTrucksForRouteUseCase
    find_suitable_routes: FindSuitableRoutesForPackageUseCase


@dataclass(frozen=True)
class TruckUseCases:
    """Truck-facing use cases."""

    view_all: ViewAllTrucksUseCase


@dataclass(frozen=True)
class StateUseCases:
    """World-state use cases."""

    advance: AdvanceWorldStateUseCase
    save: SaveWorldStateUseCase
    load: LoadWorldStateUseCase
