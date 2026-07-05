import unittest
from typing import Annotated
from unittest.mock import MagicMock, patch
from uuid import UUID

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.responses import Response

from src.adapters.driven.security.auth_token_service import TokenPayload
from src.adapters.driving.http.dependencies import auth as auth_module
from src.adapters.driving.http.dependencies.auth import AuthenticatedHTTPPrincipal, get_current_user
from src.adapters.driving.http.middleware import RequestLoggingMiddleware
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
from src.domain.enums.auth import Role


class HttpRequestLoggingMiddlewareShould(unittest.IsolatedAsyncioTestCase):
    async def test_bind_http_context_for_downstream_request_and_clear_it_after_response(self) -> None:
        middleware = RequestLoggingMiddleware(app=self._unused_app)
        observed_contexts: list[EventContext] = []

        async def call_next(_request: Request) -> Response:
            observed_contexts.append(get_event_context())
            return Response(status_code=204)

        response = await middleware.dispatch(self._request(), call_next)

        self.assertEqual(response.status_code, 204)
        self.assertEqual(len(observed_contexts), 1)
        self.assertIs(observed_contexts[0].source, EventSource.HTTP)
        self.assertIsNone(observed_contexts[0].actor)
        self.assertIsInstance(observed_contexts[0].correlation_id, UUID)
        self.assertIsNone(get_optional_event_context())

    async def test_restore_outer_context_after_downstream_response(self) -> None:
        middleware = RequestLoggingMiddleware(app=self._unused_app)
        outer_context = EventContext(
            correlation_id=UUID("00000000-0000-0000-0000-000000000001"),
            source=EventSource.CLI,
        )
        observed_contexts: list[EventContext] = []

        async def call_next(_request: Request) -> Response:
            observed_contexts.append(get_event_context())
            return Response(status_code=200)

        with bind_event_context(outer_context):
            await middleware.dispatch(self._request(), call_next)
            self.assertIs(get_event_context(), outer_context)

        self.assertIs(observed_contexts[0].source, EventSource.HTTP)
        self.assertIsNot(observed_contexts[0], outer_context)
        self.assertIsNone(get_optional_event_context())

    async def test_restore_context_and_reraise_downstream_failure(self) -> None:
        middleware = RequestLoggingMiddleware(app=self._unused_app)
        observed_contexts: list[EventContext] = []

        async def call_next(_request: Request) -> Response:
            observed_contexts.append(get_event_context())
            raise RuntimeError("downstream failed")

        with self.assertRaisesRegex(RuntimeError, "downstream failed"):
            await middleware.dispatch(self._request(), call_next)

        self.assertEqual(len(observed_contexts), 1)
        self.assertIs(observed_contexts[0].source, EventSource.HTTP)
        self.assertIsNone(get_optional_event_context())

    @staticmethod
    async def _unused_app(_scope: object, _receive: object, _send: object) -> None:
        raise AssertionError("The middleware app should not be called directly in these tests.")

    @staticmethod
    def _request() -> Request:
        return Request({
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/health",
            "raw_path": b"/health",
            "query_string": b"",
            "headers": [],
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
        })


class HttpEventContextIntegrationShould(unittest.TestCase):
    def test_enrich_middleware_context_with_authenticated_actor_for_endpoint(self) -> None:
        app = FastAPI()
        app.add_middleware(RequestLoggingMiddleware)
        observed_contexts: list[EventContext] = []

        def protected(
            _principal: Annotated[AuthenticatedHTTPPrincipal, Depends(get_current_user)],
        ) -> dict[str, str]:
            context = get_event_context()
            observed_contexts.append(context)
            assert context.actor is not None
            return {
                "source": context.source.value,
                "username": context.actor.username,
            }

        app.get("/protected")(protected)

        user_repo = MagicMock()
        app.dependency_overrides[auth_module.get_user_repository] = lambda: user_repo

        with patch.object(auth_module, "principal_from_token", return_value=self._principal()) as from_token:
            response = TestClient(app).get("/protected", headers={"Authorization": "Bearer access-token"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"source": EventSource.HTTP.value, "username": "alice"})
        self.assertEqual(len(observed_contexts), 1)
        self.assertEqual(observed_contexts[0].actor.user_id if observed_contexts[0].actor else None, 1)
        from_token.assert_called_once_with("access-token", user_repo)

    @staticmethod
    def _principal() -> AuthenticatedHTTPPrincipal:
        record = UserRecord(
            user_id=1,
            username="alice",
            role="MANAGER",
            name="Alice",
            email="alice@example.com",
            phone_number="0412345678",
            password="hash",
            token_version=1,
        )
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
            token=TokenPayload(
                sub="1",
                iat=1,
                exp=2,
                jti="token-id",
                type="access",
                username="alice",
                role="MANAGER",
                token_version=1,
            ),
        )
