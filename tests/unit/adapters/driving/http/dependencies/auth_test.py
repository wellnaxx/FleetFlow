import unittest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException, status

from src.adapters.driven.security.auth_token_service import TokenPayload
from src.adapters.driving.http.dependencies import auth as auth_module
from src.adapters.driving.http.dependencies.auth import (
    _runtime_user_from_record,  # pyright: ignore[reportPrivateUsage]
    principal_from_token,
)
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

    def test_principal_from_token_validates_refresh_token_and_returns_principal(self) -> None:
        user_repo = MagicMock()
        user_repo.get_by_id.return_value = self._record(role="MANAGER")

        with patch.object(auth_module, "decode_token", return_value=self._token_payload(type_="refresh")):
            principal = principal_from_token("refresh-token", user_repo, expected_type="refresh")

        self.assertEqual(principal.record.username, "alice")
        self.assertIsInstance(principal.user, Manager)
        user_repo.get_by_id.assert_called_once_with(1)

    def test_principal_from_token_validates_access_token_and_returns_principal(self) -> None:
        user_repo = MagicMock()
        user_repo.get_by_id.return_value = self._record(role="MANAGER")

        with patch.object(auth_module, "decode_token", return_value=self._token_payload(type_="access")):
            principal = principal_from_token("access-token", user_repo, expected_type="access")

        self.assertEqual(principal.record.username, "alice")
        self.assertIsInstance(principal.user, Manager)
        user_repo.get_by_id.assert_called_once_with(1)

    def test_principal_from_token_raises_refresh_specific_message_for_invalid_refresh_token(self) -> None:
        user_repo = MagicMock()

        with (
            patch.object(auth_module, "decode_token", return_value=None),
            self.assertRaises(HTTPException) as ctx,
        ):
            principal_from_token("refresh-token", user_repo, expected_type="refresh")

        self.assertEqual(ctx.exception.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(ctx.exception.detail, "Invalid or expired refresh token.")

    def test_principal_from_token_raises_generic_message_for_invalid_access_token(self) -> None:
        user_repo = MagicMock()

        with (
            patch.object(auth_module, "decode_token", return_value=None),
            self.assertRaises(HTTPException) as ctx,
        ):
            principal_from_token("access-token", user_repo, expected_type="access")

        self.assertEqual(ctx.exception.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(ctx.exception.detail, "Invalid or expired token.")

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

    def _token_payload(self, *, type_: str = "access") -> TokenPayload:
        return TokenPayload(
            sub="1",
            iat=1,
            exp=2,
            jti="token-id",
            type=type_,  # type: ignore[arg-type]
            username="alice",
            role="MANAGER",
            token_version=1,
        )
