import unittest
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

from src.adapters.driven.persistence.application_data.package_repository import (
    ApplicationDataPackageRepository,
)
from src.application.use_cases.packages.remove_package import RemovePackageUseCase
from src.core.application_data import ApplicationData


def _allow_all(*_args: Any, **_kwargs: Any) -> bool:
    return True


def _mk_app() -> Any:
    app = ApplicationData(current_user=None)
    app.authz = MagicMock()  # type: ignore[assignment]
    app.authz.has.side_effect = _allow_all
    app.authz.has_all.side_effect = _allow_all
    app.vehicle_manager = MagicMock()  # type: ignore[assignment]
    app.vehicle_manager.vehicles = []
    return app


def make_remove_package_uc(app: ApplicationData) -> RemovePackageUseCase:
    package_repo = ApplicationDataPackageRepository(app)
    return RemovePackageUseCase(package_repo)


class _FakeRoute:
    def __init__(self, route_id: int, locations: list[str]) -> None:
        self.route_id = route_id
        self.locations = list(locations)
        self.start_location = locations[0]
        self.end_location = locations[-1]
        self.packages: list[Any] = []

    def detach_package(self, package: Any) -> None:
        for i, existing in enumerate(self.packages):
            if existing.package_id == package.package_id:
                self.packages.pop(i)
                if getattr(package, "route", None) is self:
                    package.route = None
                return
        raise ValueError(f"Package with id {package.package_id} is not assigned to this route.")


class _FakePackage:
    def __init__(
        self,
        package_id: int,
        start: str,
        end: str,
        weight: float = 1.0,
        customer: Any = None,
    ) -> None:
        self.package_id = package_id
        self.start_location = start
        self.end_location = end
        self.weight = weight
        self.customer: Any = customer or SimpleNamespace(customer_id=1)
        self.route: Any = None
        self.status: str | None = None


class ApplicationDataBackedPackageRemovalIntegration_Should(unittest.TestCase):
    def test_remove_unassigned_package(self) -> None:
        app = _mk_app()
        pkg = _FakePackage(1, "A", "B")
        app._packages.append(pkg)

        remove_uc = make_remove_package_uc(app)
        removed = remove_uc.execute(pkg.package_id)

        self.assertIs(removed, pkg)
        self.assertEqual(len(app._packages), 0)

    def test_remove_assigned_clears_route_list(self) -> None:
        app = _mk_app()
        route = _FakeRoute(10, ["A", "B"])
        pkg = _FakePackage(1, "A", "B")
        route.packages.append(pkg)
        pkg.route = route
        app._routes.append(route)
        app._packages.append(pkg)

        remove_uc = make_remove_package_uc(app)
        remove_uc.execute(pkg.package_id)

        self.assertNotIn(pkg, route.packages)

    def test_remove_assigned_sets_route_to_none(self) -> None:
        app = _mk_app()
        route = _FakeRoute(10, ["A", "B"])
        pkg = _FakePackage(1, "A", "B")
        route.packages.append(pkg)
        pkg.route = route
        app._routes.append(route)
        app._packages.append(pkg)

        remove_uc = make_remove_package_uc(app)
        remove_uc.execute(pkg.package_id)

        self.assertIsNone(pkg.route)

    def test_remove_leaves_other_packages_on_route(self) -> None:
        app = _mk_app()
        route = _FakeRoute(10, ["A", "B"])
        pkg1 = _FakePackage(1, "A", "B")
        pkg2 = _FakePackage(2, "A", "B")
        route.packages.extend([pkg1, pkg2])
        pkg1.route = route
        pkg2.route = route
        app._routes.append(route)
        app._packages.extend([pkg1, pkg2])

        remove_uc = make_remove_package_uc(app)
        remove_uc.execute(pkg1.package_id)

        self.assertIn(pkg2, route.packages)
        self.assertIs(pkg2.route, route)
