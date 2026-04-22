import unittest
from types import SimpleNamespace
from typing import Any

from src.adapters.driven.persistence.memory.package_repository import InMemoryPackageRepository
from src.application.use_cases.packages.remove_package import RemovePackageUseCase


class _FakeRoute:
    def __init__(self) -> None:
        self.packages: list[Any] = []

    def detach_package(self, package: Any) -> None:
        for index, existing in enumerate(self.packages):
            if existing.package_id == package.package_id:
                self.packages.pop(index)
                if getattr(package, "route", None) is self:
                    package.route = None
                return
        raise ValueError(f"Package with id {package.package_id} is not assigned to this route.")


class _FakePackage:
    def __init__(self, package_id: int) -> None:
        self.package_id = package_id
        self.start_location = "A"
        self.end_location = "B"
        self.weight = 1.0
        self.customer: Any = SimpleNamespace(customer_id=1)
        self.route: Any = None
        self.status: str | None = None


class RuntimePackageRemovalIntegrationTests(unittest.TestCase):
    def test_remove_assigned_package_updates_repo_and_route(self) -> None:
        package_repo = InMemoryPackageRepository()
        route = _FakeRoute()
        package = _FakePackage(1)
        route.packages.append(package)
        package.route = route
        package_repo.add(package)

        removed = RemovePackageUseCase(package_repo).execute(package.package_id)

        self.assertIs(removed, package)
        self.assertIsNone(package_repo.get_by_id(package.package_id))
        self.assertEqual(route.packages, [])
        self.assertIsNone(package.route)
