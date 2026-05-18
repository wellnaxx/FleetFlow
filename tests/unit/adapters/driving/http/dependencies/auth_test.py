import unittest

from fastapi import HTTPException, status

from src.adapters.driving.http.dependencies.auth import _runtime_user_from_record
from src.application.models.user_record import UserRecord
from src.domain.entities.users.employee import Employee
from src.domain.entities.users.manager import Manager


class HttpAuthDependencyShould(unittest.TestCase):
    def test_runtime_user_from_record_returns_manager(self) -> None:
        record = self._record(role="MANAGER")

        user = _runtime_user_from_record(record)  # type: ignore[reportPrivateUsage]

        self.assertIsInstance(user, Manager)
        self.assertEqual(user.user_id, record.user_id)

    def test_runtime_user_from_record_returns_employee(self) -> None:
        record = self._record(role="EMPLOYEE")

        user = _runtime_user_from_record(record)  # type: ignore[reportPrivateUsage]

        self.assertIsInstance(user, Employee)
        self.assertEqual(user.user_id, record.user_id)

    def test_runtime_user_from_record_raises_unauthorized_for_invalid_role(self) -> None:
        record = self._record(role="OWNER")

        with self.assertRaises(HTTPException) as ctx:
            _runtime_user_from_record(record)  # type: ignore[reportPrivateUsage]

        self.assertEqual(ctx.exception.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(ctx.exception.detail, "Invalid user role")

    def _record(self, *, role: str) -> UserRecord:
        return UserRecord(
            user_id=1,
            username="alice",
            role=role,
            name="Alice",
            email="alice@example.com",
            phone_number="0412345678",
            password="hash",
            token_version=1,
        )
