import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi import HTTPException, status

from src.adapters.driven.security.auth_token_service import TokenPayload
from src.adapters.driving.http.dependencies import auth as auth_module
from src.adapters.driving.http.dependencies.auth import (
    AuthenticatedHTTPPrincipal,
    _runtime_user_from_record,  # pyright: ignore[reportPrivateUsage]
    get_current_user,
    get_optional_user,
    principal_from_token,
)
from src.application.enums.event_sources import EventSource
from src.application.eventing.context import EventContext
from src.application.eventing.current_context import (
    bind_event_context,
    get_event_context,
    get_optional_event_context,
)
from src.application.models.current_user_principal import CurrentUserPrincipal
from src.application.models.user_record import UserRecord
from src.application.services.authorization_service import AuthorizationService
from src.application.services.current_authorization import (
    get_authorization_context,
    get_optional_authorization_context,
)
from src.domain.enums.auth import Role


class HttpAuthDependencyShould(unittest.IsolatedAsyncioTestCase):
    def test_runtime_user_from_record_returns_manager(self) -> None:
        record = self._record(role="MANAGER")

        user = _runtime_user_from_record(record)  # type: ignore[reportPrivateUsage]

        self.assertIsInstance(user, CurrentUserPrincipal)
        self.assertEqual(user.user_id, record.user_id)
        self.assertIs(user.role, Role.MANAGER)

    def test_runtime_user_from_record_returns_employee(self) -> None:
        record = self._record(role="EMPLOYEE")

        user = _runtime_user_from_record(record)  # type: ignore[reportPrivateUsage]

        self.assertIsInstance(user, CurrentUserPrincipal)
        self.assertEqual(user.user_id, record.user_id)
        self.assertIs(user.role, Role.EMPLOYEE)

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
        self.assertIsInstance(principal.current_user, CurrentUserPrincipal)
        self.assertIs(principal.current_user.role, Role.MANAGER)
        user_repo.get_by_id.assert_called_once_with(1)

    def test_principal_from_token_validates_access_token_and_returns_principal(self) -> None:
        user_repo = MagicMock()
        user_repo.get_by_id.return_value = self._record(role="MANAGER")

        with patch.object(auth_module, "decode_token", return_value=self._token_payload(type_="access")):
            principal = principal_from_token("access-token", user_repo, expected_type="access")

        self.assertEqual(principal.record.username, "alice")
        self.assertIsInstance(principal.current_user, CurrentUserPrincipal)
        self.assertIs(principal.current_user.role, Role.MANAGER)
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

    def test_get_optional_user_returns_none_when_no_token_is_supplied(self) -> None:
        user_repo = MagicMock()

        with patch.object(auth_module, "principal_from_token") as principal_from_token_mock:
            principal = get_optional_user(None, user_repo)

        self.assertIsNone(principal)
        principal_from_token_mock.assert_not_called()

    def test_get_optional_user_returns_principal_for_valid_supplied_token(self) -> None:
        user_repo = MagicMock()
        expected_principal = object()

        with patch.object(
            auth_module, "principal_from_token", return_value=expected_principal
        ) as principal_from_token_mock:
            principal = get_optional_user("access-token", user_repo)

        self.assertIs(principal, expected_principal)
        principal_from_token_mock.assert_called_once_with("access-token", user_repo)

    def test_get_optional_user_reraises_unauthorized_for_invalid_supplied_token(self) -> None:
        user_repo = MagicMock()
        unauthorized = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked.")

        with (
            patch.object(auth_module, "principal_from_token", side_effect=unauthorized),
            self.assertRaises(HTTPException) as ctx,
        ):
            get_optional_user("revoked-token", user_repo)

        self.assertIs(ctx.exception, unauthorized)

    async def test_get_current_user_binds_authenticated_actor_to_request_context(self) -> None:
        user_repo = MagicMock()
        principal = self._principal()
        request_context = self._request_context()
        container_authorization = AuthorizationService(None)

        with (
            bind_event_context(request_context),
            patch.object(auth_module, "principal_from_token", return_value=principal) as from_token,
        ):
            dependency = get_current_user("access-token", user_repo)
            resolved_principal = await anext(dependency)
            actor_context = get_event_context()

            self.assertIs(resolved_principal, principal)
            self.assertIsNot(actor_context, request_context)
            self.assertEqual(actor_context.correlation_id, request_context.correlation_id)
            self.assertIs(actor_context.source, EventSource.HTTP)
            self.assertIsNotNone(actor_context.actor)
            assert actor_context.actor is not None
            self.assertEqual(actor_context.actor.user_id, 1)
            self.assertEqual(actor_context.actor.username, "alice")
            self.assertIs(get_authorization_context().current_user, principal.current_user)
            self.assertIs(container_authorization.current_user, principal.current_user)

            await dependency.aclose()
            self.assertIs(get_event_context(), request_context)
            self.assertIsNone(get_optional_authorization_context())
            self.assertIsNone(container_authorization.current_user)

        from_token.assert_called_once_with("access-token", user_repo)
        self.assertIsNone(get_optional_event_context())
        self.assertIsNone(get_optional_authorization_context())

    async def test_get_current_user_restores_request_context_when_endpoint_fails(self) -> None:
        user_repo = MagicMock()
        request_context = self._request_context()

        with (
            bind_event_context(request_context),
            patch.object(auth_module, "principal_from_token", return_value=self._principal()),
        ):
            dependency = get_current_user("access-token", user_repo)
            await anext(dependency)

            with self.assertRaisesRegex(RuntimeError, "endpoint failed"):
                await dependency.athrow(RuntimeError("endpoint failed"))

            self.assertIs(get_event_context(), request_context)
            self.assertIsNone(get_optional_authorization_context())

        self.assertIsNone(get_optional_event_context())
        self.assertIsNone(get_optional_authorization_context())

    async def test_get_current_user_leaves_request_context_unchanged_when_token_validation_fails(self) -> None:
        user_repo = MagicMock()
        request_context = self._request_context()
        failure = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked.")

        with (
            bind_event_context(request_context),
            patch.object(auth_module, "principal_from_token", side_effect=failure),
            self.assertRaises(HTTPException) as ctx,
        ):
            dependency = get_current_user("access-token", user_repo)
            await anext(dependency)

        self.assertIs(ctx.exception, failure)
        self.assertIsNone(get_optional_event_context())
        self.assertIsNone(get_optional_authorization_context())

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

    def _principal(self) -> AuthenticatedHTTPPrincipal:
        record = self._record(role="MANAGER")
        user = CurrentUserPrincipal(
            user_id=record.user_id,
            username=record.username,
            name=record.name,
            email=record.email,
            phone_number=record.phone_number,
            role=Role.MANAGER,
        )
        return AuthenticatedHTTPPrincipal(
            record=record,
            current_user=user,
            authz=AuthorizationService(current_user=user),
            token=self._token_payload(),
        )

    @staticmethod
    def _request_context() -> EventContext:
        return EventContext(
            correlation_id=uuid4(),
            source=EventSource.HTTP,
        )
