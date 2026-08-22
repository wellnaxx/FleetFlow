import unittest
from typing import cast
from unittest.mock import MagicMock

from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.authorization_operations import AuthorizationOperation
from src.application.events.auth_events import AuthorizationDenied
from src.application.exceptions.application_errors import NotFoundError
from src.application.queries.packages.view_package import ViewPackageQuery
from src.application.services.authorization_service import AuthorizationService
from src.application.use_cases.packages.view_package import ViewPackageUseCase
from tests.unit.application.use_cases.authz_helpers import manager_authz


class ViewPackageUseCase_Should(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_packages = MagicMock()
        self.use_case = ViewPackageUseCase(self.mock_packages, manager_authz())

    def test_returns_package_when_found(self) -> None:
        package = MagicMock()
        package.package_id = 123
        self.mock_packages.get_by_id.return_value = package

        result = self.use_case.execute(ViewPackageQuery(package_id=123))

        self.assertIs(result, package)
        self.mock_packages.get_by_id.assert_called_once_with(123)

    def test_raises_when_package_not_found(self) -> None:
        self.mock_packages.get_by_id.return_value = None

        with self.assertRaises(NotFoundError) as ctx:
            self.use_case.execute(ViewPackageQuery(package_id=999))

        self.assertIn("Package with ID 999 not found", str(ctx.exception))
        self.mock_packages.get_by_id.assert_called_once_with(999)

    def test_unauthenticated_request_records_target_before_lookup(self) -> None:
        use_case = ViewPackageUseCase(self.mock_packages, AuthorizationService(None))

        with self.assertRaisesRegex(PermissionError, "Unauthenticated"):
            use_case.execute(ViewPackageQuery(package_id=321))

        self.mock_packages.get_by_id.assert_not_called()
        self.assertEqual(len(use_case.pending_events), 1)
        event = cast(AuthorizationDenied, use_case.pending_events[0])
        self.assertIsInstance(event, AuthorizationDenied)
        self.assertIs(event.attempted_operation, AuthorizationOperation.PACKAGE_VIEW)
        self.assertIs(event.target_resource_type, AuditResourceType.PACKAGE)
        self.assertEqual(event.target_resource_id, "321")
