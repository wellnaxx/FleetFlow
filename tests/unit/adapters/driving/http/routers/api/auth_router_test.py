import unittest
from collections.abc import Generator
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.adapters.driven.persistence.database.errors import DatabaseError
from src.adapters.driven.security.auth_token_service import TokenPayload
from src.adapters.driving.http.dependencies.auth import AuthenticatedPrincipal
from src.adapters.driving.http.exception_handlers import register_exception_handlers
from src.adapters.driving.http.routers.api import auth_router as auth_router_module
from src.adapters.driving.http.routers.api.auth_router import (
    _token_response,  # pyright: ignore[reportPrivateUsage]
    auth_router,
)
from src.application.exceptions.application_errors import AuthenticationError, ValidationError
from src.application.models.user_record import UserRecord
from src.application.services.authorization_service import AuthorizationService
from src.domain.entities.users.manager import Manager
from src.domain.enums.auth import Role


class AuthRouterShould(unittest.TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(auth_router)
        register_exception_handlers(self.app)
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_login_returns_token_pair(self) -> None:
        auth_service = MagicMock()
        auth_service.authenticate.return_value = (self._record(), object())
        self.app.dependency_overrides[auth_router_module.get_auth_service] = lambda: auth_service

        with self._patched_tokens():
            response = self.client.post(
                "/auth/login",
                data={"username": "alice", "password": "Secret123!"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "access_token": "access-token",
                "refresh_token": "refresh-token",
                "token_type": "bearer",
            },
        )
        auth_service.authenticate.assert_called_once_with("alice", "Secret123!")

    def test_login_returns_unauthorized_for_invalid_credentials(self) -> None:
        auth_service = MagicMock()
        auth_service.authenticate.side_effect = AuthenticationError("bad credentials")
        self.app.dependency_overrides[auth_router_module.get_auth_service] = lambda: auth_service

        response = self.client.post(
            "/auth/login",
            data={"username": "alice", "password": "wrong"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Invalid username or password.")

    def test_login_returns_bad_request_for_invalid_persisted_role_before_token_creation(self) -> None:
        auth_service = MagicMock()
        auth_service.authenticate.return_value = (self._record(role="OWNER"), object())
        self.app.dependency_overrides[auth_router_module.get_auth_service] = lambda: auth_service

        with self._patched_tokens() as token_mocks:
            response = self.client.post(
                "/auth/login",
                data={"username": "alice", "password": "Secret123!"},
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Invalid persisted user role.")
        token_mocks["create_access_token"].assert_not_called()
        token_mocks["create_refresh_token"].assert_not_called()

    def test_register_returns_created_user(self) -> None:
        use_case = MagicMock()
        use_case.execute.return_value = self._record(user_id=2, username="bob", role=Role.EMPLOYEE.value)
        self.app.dependency_overrides[auth_router_module.get_register_user_use_case] = lambda: use_case

        response = self.client.post(
            "/auth/register",
            json={
                "username": "bob",
                "role": "employee",
                "name": "Bob",
                "email": None,
                "phone_number": None,
                "password": "Secret123!",
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["username"], "bob")
        use_case.execute.assert_called_once_with(
            username="bob",
            role=Role.EMPLOYEE,
            name="Bob",
            email="",
            phone_number="",
            password="Secret123!",
        )

    def test_register_returns_forbidden_for_permission_error(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = PermissionError("Missing permission: ADMIN_USER")
        self.app.dependency_overrides[auth_router_module.get_register_user_use_case] = lambda: use_case

        response = self.client.post(
            "/auth/register",
            json={
                "username": "bob",
                "role": "EMPLOYEE",
                "name": "Bob",
                "password": "Secret123!",
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Missing permission: ADMIN_USER")

    def test_change_password_changes_current_user_password(self) -> None:
        principal = self._principal()
        use_case = MagicMock()
        self.app.dependency_overrides[auth_router_module.get_current_user] = lambda: principal
        self.app.dependency_overrides[auth_router_module.get_change_password_use_case] = lambda: use_case

        response = self.client.post(
            "/auth/change-password",
            json={
                "current_password": "OldSecret123!",
                "new_password": "NewSecret123!",
            },
        )

        self.assertEqual(response.status_code, 204)
        use_case.execute_current_user.assert_called_once_with(
            username="alice",
            new_password="NewSecret123!",
            old_password="OldSecret123!",
        )

    def test_change_password_returns_bad_request_for_invalid_password(self) -> None:
        principal = self._principal()
        use_case = MagicMock()
        use_case.execute_current_user.side_effect = AuthenticationError("Old password incorrect.")
        self.app.dependency_overrides[auth_router_module.get_current_user] = lambda: principal
        self.app.dependency_overrides[auth_router_module.get_change_password_use_case] = lambda: use_case

        response = self.client.post(
            "/auth/change-password",
            json={
                "current_password": "OldSecret123!",
                "new_password": "NewSecret123!",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Old password incorrect.")

    def test_change_password_returns_forbidden_for_permission_error(self) -> None:
        principal = self._principal()
        use_case = MagicMock()
        use_case.execute_current_user.side_effect = PermissionError("Unauthenticated")
        self.app.dependency_overrides[auth_router_module.get_current_user] = lambda: principal
        self.app.dependency_overrides[auth_router_module.get_change_password_use_case] = lambda: use_case

        response = self.client.post(
            "/auth/change-password",
            json={
                "current_password": "OldSecret123!",
                "new_password": "NewSecret123!",
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Unauthenticated")

    def test_reset_password_resets_target_password(self) -> None:
        use_case = MagicMock()
        self.app.dependency_overrides[auth_router_module.get_change_password_use_case] = lambda: use_case

        response = self.client.post(
            "/auth/users/bob/reset-password",
            json={"new_password": "ResetSecret123!"},
        )

        self.assertEqual(response.status_code, 204)
        use_case.execute.assert_called_once_with(username="bob", new_password="ResetSecret123!")

    def test_reset_password_returns_bad_request_for_invalid_password(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = ValidationError("Password must be at least 8 characters.")
        self.app.dependency_overrides[auth_router_module.get_change_password_use_case] = lambda: use_case

        response = self.client.post(
            "/auth/users/bob/reset-password",
            json={"new_password": "ResetSecret123!"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Password must be at least 8 characters.")

    def test_reset_password_returns_forbidden_for_permission_error(self) -> None:
        use_case = MagicMock()
        use_case.execute.side_effect = PermissionError("Missing permission: ADMIN_USER")
        self.app.dependency_overrides[auth_router_module.get_change_password_use_case] = lambda: use_case

        response = self.client.post(
            "/auth/users/bob/reset-password",
            json={"new_password": "ResetSecret123!"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Missing permission: ADMIN_USER")

    def test_refresh_returns_new_token_pair(self) -> None:
        user_repo = MagicMock()
        self.app.dependency_overrides[auth_router_module.get_user_repository] = lambda: user_repo

        with (
            patch.object(
                auth_router_module,
                "principal_from_token",
                return_value=self._principal(),
            ) as principal_from_token,
            self._patched_tokens(),
        ):
            response = self.client.post("/auth/refresh", json={"refresh_token": "refresh-token"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["access_token"], "access-token")
        principal_from_token.assert_called_once_with("refresh-token", user_repo, expected_type="refresh")

    def test_refresh_rejects_revoked_token(self) -> None:
        user_repo = MagicMock()
        self.app.dependency_overrides[auth_router_module.get_user_repository] = lambda: user_repo

        with patch.object(
            auth_router_module,
            "principal_from_token",
            side_effect=auth_router_module.HTTPException(status_code=401, detail="Token revoked."),
        ):
            response = self.client.post("/auth/refresh", json={"refresh_token": "refresh-token"})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Token revoked.")

    def test_refresh_rejects_invalid_persisted_role_without_issuing_tokens(self) -> None:
        user_repo = MagicMock()
        principal = self._principal(record=self._record(role="OWNER"))
        self.app.dependency_overrides[auth_router_module.get_user_repository] = lambda: user_repo

        with (
            patch.object(auth_router_module, "principal_from_token", return_value=principal),
            self._patched_tokens() as token_mocks,
        ):
            response = self.client.post("/auth/refresh", json={"refresh_token": "refresh-token"})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Invalid or expired refresh token.")
        token_mocks["create_access_token"].assert_not_called()
        token_mocks["create_refresh_token"].assert_not_called()

    def test_token_response_serializes_valid_role_enum_value(self) -> None:
        record = self._record(role=Role.EMPLOYEE.value)

        with self._patched_tokens() as token_mocks:
            response = _token_response(record)  # pyright: ignore[reportPrivateUsage]

        self.assertEqual(response.access_token, "access-token")
        token_input = token_mocks["create_access_token"].call_args.args[0]
        self.assertEqual(token_input["role"], Role.EMPLOYEE.value)
        token_mocks["create_refresh_token"].assert_called_once_with(token_input)

    def test_logout_increments_token_version(self) -> None:
        principal = self._principal()
        user_repo = MagicMock()
        user_repo.increment_token_version_by_id.return_value = self._record(token_version=2)
        auth_service = MagicMock()
        auth_service.user_repository = user_repo
        self.app.dependency_overrides[auth_router_module.get_current_user] = lambda: principal
        self.app.dependency_overrides[auth_router_module.get_auth_service] = lambda: auth_service

        response = self.client.post("/auth/logout")

        self.assertEqual(response.status_code, 204)
        user_repo.increment_token_version_by_id.assert_called_once_with(1)
        auth_service.logout.assert_called_once_with()

    def test_logout_is_idempotent_when_user_record_is_already_missing(self) -> None:
        principal = self._principal()
        user_repo = MagicMock()
        user_repo.increment_token_version_by_id.return_value = None
        auth_service = MagicMock()
        auth_service.user_repository = user_repo
        self.app.dependency_overrides[auth_router_module.get_current_user] = lambda: principal
        self.app.dependency_overrides[auth_router_module.get_auth_service] = lambda: auth_service

        response = self.client.post("/auth/logout")

        self.assertEqual(response.status_code, 204)
        user_repo.increment_token_version_by_id.assert_called_once_with(1)
        auth_service.logout.assert_called_once_with()

    def test_logout_returns_generic_error_for_database_failure(self) -> None:
        principal = self._principal()
        user_repo = MagicMock()
        user_repo.increment_token_version_by_id.side_effect = DatabaseError.write_failed(Exception("boom"))
        auth_service = MagicMock()
        auth_service.user_repository = user_repo
        self.app.dependency_overrides[auth_router_module.get_current_user] = lambda: principal
        self.app.dependency_overrides[auth_router_module.get_auth_service] = lambda: auth_service

        response = self.client.post("/auth/logout")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["detail"], "Database operation failed.")
        user_repo.increment_token_version_by_id.assert_called_once_with(1)
        auth_service.logout.assert_not_called()

    def test_me_returns_null_for_absent_contact_fields(self) -> None:
        principal = self._principal(
            self._record(
                email="",
                phone_number="",
            )
        )
        self.app.dependency_overrides[auth_router_module.get_current_user] = lambda: principal

        response = self.client.get("/auth/me")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["username"], "alice")
        self.assertIsNone(response.json()["email"])
        self.assertIsNone(response.json()["phone_number"])

    def test_me_returns_populated_contact_fields(self) -> None:
        principal = self._principal(
            self._record(
                email="alice@example.com",
                phone_number="0412345678",
            )
        )
        self.app.dependency_overrides[auth_router_module.get_current_user] = lambda: principal

        response = self.client.get("/auth/me")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["email"], "alice@example.com")
        self.assertEqual(response.json()["phone_number"], "0412345678")

    @contextmanager
    def _patched_tokens(self) -> Generator[dict[str, MagicMock]]:
        token_mocks = {
            "create_access_token": MagicMock(return_value="access-token"),
            "create_refresh_token": MagicMock(return_value="refresh-token"),
        }
        with patch.multiple(auth_router_module, **token_mocks):
            yield token_mocks

    def _principal(self, record: UserRecord | None = None) -> AuthenticatedPrincipal:
        record = record or self._record()
        user = Manager(record.user_id, record.name, record.email, record.phone_number)
        return AuthenticatedPrincipal(
            record=record,
            user=user,
            authz=AuthorizationService(user),
            token=self._token_payload(),
        )

    def _record(
        self,
        *,
        user_id: int = 1,
        username: str = "alice",
        role: str = Role.MANAGER.value,
        email: str = "alice@example.com",
        phone_number: str = "0412345678",
        token_version: int = 1,
    ) -> UserRecord:
        return UserRecord(
            user_id=user_id,
            username=username,
            role=role,
            name=username.title(),
            email=email,
            phone_number=phone_number,
            password="hash",
            token_version=token_version,
        )

    def _token_payload(self, *, token_version: int = 1) -> TokenPayload:
        return TokenPayload(
            sub="1",
            iat=1,
            exp=2,
            jti="token-id",
            type="refresh",
            username="alice",
            role=Role.MANAGER.value,
            token_version=token_version,
        )
