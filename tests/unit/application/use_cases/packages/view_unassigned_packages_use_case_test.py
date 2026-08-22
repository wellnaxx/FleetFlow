import unittest
from typing import cast
from unittest.mock import MagicMock

from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.authorization_operations import AuthorizationOperation
from src.application.events.auth_events import AuthorizationDenied
from src.application.exceptions.application_errors import ValidationError
from src.application.queries.packages.view_unassigned_packages import ViewUnassignedPackagesQuery
from src.application.services.authorization_service import AuthorizationService
from src.application.use_cases.packages.view_unassigned_packages import ViewUnassignedPackagesUseCase
from src.application.use_cases.pagination import PageQuery
from tests.unit.application.use_cases.authz_helpers import manager_authz


class ViewUnassignedPackagesUseCase_Should(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_packages = MagicMock()
        self.use_case = ViewUnassignedPackagesUseCase(self.mock_packages, manager_authz())

    def test_returns_unassigned_packages(self) -> None:
        package1 = MagicMock()
        package2 = MagicMock()
        self.mock_packages.list_unassigned.return_value = [package1, package2]

        result = self.use_case.execute(ViewUnassignedPackagesQuery())

        self.assertEqual(result.items, (package1, package2))
        self.assertIsNone(result.total)
        self.assertIsNone(result.limit)
        self.assertEqual(result.offset, 0)
        self.assertEqual(result.count, 2)
        self.mock_packages.list_unassigned.assert_called_once_with()

    def test_returns_empty_list_when_no_unassigned_packages(self) -> None:
        self.mock_packages.list_unassigned.return_value = []

        result = self.use_case.execute(ViewUnassignedPackagesQuery())

        self.assertEqual(result.items, ())
        self.assertEqual(result.count, 0)
        self.mock_packages.list_unassigned.assert_called_once_with()

    def test_returns_requested_unassigned_package_page(self) -> None:
        package = MagicMock()
        self.mock_packages.list_unassigned_page.return_value = [package]

        result = self.use_case.execute(ViewUnassignedPackagesQuery(page=PageQuery(limit=10, offset=20)))

        self.assertEqual(result.items, (package,))
        self.assertIsNone(result.total)
        self.assertEqual(result.limit, 10)
        self.assertEqual(result.offset, 20)
        self.assertEqual(result.count, 1)
        self.mock_packages.list_unassigned_page.assert_called_once_with(limit=10, offset=20)
        self.mock_packages.list_unassigned.assert_not_called()

    def test_rejects_invalid_pagination(self) -> None:
        with self.assertRaises(ValidationError):
            self.use_case.execute(ViewUnassignedPackagesQuery(page=PageQuery(limit=0)))

        with self.assertRaises(ValidationError):
            self.use_case.execute(ViewUnassignedPackagesQuery(page=PageQuery(limit=1, offset=-1)))

        with self.assertRaises(ValidationError):
            self.use_case.execute(ViewUnassignedPackagesQuery(page=PageQuery(offset=1)))

        self.mock_packages.list_unassigned_page.assert_not_called()

    def test_returns_requested_unassigned_page_with_total(self) -> None:
        package = MagicMock()
        self.mock_packages.list_unassigned_page_with_total.return_value = ([package], 2)

        result = self.use_case.execute(
            ViewUnassignedPackagesQuery(page=PageQuery(limit=10, offset=20, include_total=True))
        )

        self.assertEqual(result.items, (package,))
        self.assertEqual(result.total, 2)
        self.assertEqual(result.count, 1)
        self.mock_packages.list_unassigned_page_with_total.assert_called_once_with(
            limit=10,
            offset=20,
        )

    def test_requires_package_view_unassigned_permission(self) -> None:
        use_case = ViewUnassignedPackagesUseCase(self.mock_packages, AuthorizationService(None))

        with self.assertRaisesRegex(PermissionError, "Unauthenticated"):
            use_case.execute(ViewUnassignedPackagesQuery())

        self.mock_packages.list_unassigned.assert_not_called()
        self.assertEqual(len(use_case.pending_events), 1)
        event = cast(AuthorizationDenied, use_case.pending_events[0])
        self.assertIsInstance(event, AuthorizationDenied)
        self.assertIs(event.attempted_operation, AuthorizationOperation.PACKAGE_LIST_UNASSIGNED)
        self.assertIs(event.target_resource_type, AuditResourceType.PACKAGE)
        self.assertIsNone(event.target_resource_id)
