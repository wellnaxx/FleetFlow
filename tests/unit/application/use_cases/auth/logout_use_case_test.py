import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.application.enums.token_revocation_reasons import TokenRevocationReason
from src.application.events.auth_events import UserSessionEnded, UserTokensRevoked
from src.application.use_cases.auth.logout import LogoutUseCase


class LogoutUseCase_Should(unittest.TestCase):
    def test_revokes_tokens_logs_out_and_records_events(self) -> None:
        auth = MagicMock()
        user_repo = MagicMock()
        occurred_at = datetime(2025, 1, 1, 12, 0)
        use_case = LogoutUseCase(user_repo, auth, clock=lambda: occurred_at)

        result = use_case.execute(user_id=7, username="alice")

        self.assertIsNone(result)
        user_repo.increment_token_version_by_id.assert_called_once_with(7)
        auth.logout.assert_called_once_with()

        revoked, ended = use_case.pending_events
        self.assertIsInstance(revoked, UserTokensRevoked)
        assert isinstance(revoked, UserTokensRevoked)
        self.assertEqual(revoked.user_id, 7)
        self.assertEqual(revoked.username, "alice")
        self.assertIs(revoked.reason, TokenRevocationReason.USER_LOGOUT)
        self.assertEqual(revoked.occurred_at, occurred_at)

        self.assertIsInstance(ended, UserSessionEnded)
        assert isinstance(ended, UserSessionEnded)
        self.assertEqual(ended.user_id, 7)
        self.assertEqual(ended.username, "alice")
        self.assertEqual(ended.occurred_at, occurred_at)

    def test_does_not_clear_session_or_record_events_when_revocation_fails(self) -> None:
        auth = MagicMock()
        user_repo = MagicMock()
        user_repo.increment_token_version_by_id.side_effect = RuntimeError("db failed")
        use_case = LogoutUseCase(user_repo, auth)

        with self.assertRaises(RuntimeError):
            use_case.execute(user_id=7, username="alice")

        auth.logout.assert_not_called()
        self.assertEqual(use_case.pending_events, ())

    def test_execute_current_session_uses_auth_service_identity(self) -> None:
        auth = MagicMock()
        auth.current_user = SimpleNamespace(user_id=7)
        auth.last_username = "  Alice  "
        user_repo = MagicMock()
        use_case = LogoutUseCase(user_repo, auth)

        use_case.execute_current_session()

        user_repo.increment_token_version_by_id.assert_called_once_with(7)
        auth.logout.assert_called_once_with()
        event = use_case.pending_events[0]
        self.assertIsInstance(event, UserTokensRevoked)
        assert isinstance(event, UserTokensRevoked)
        self.assertEqual(event.username, "alice")

    def test_execute_current_session_requires_authenticated_user(self) -> None:
        auth = MagicMock()
        auth.current_user = None
        user_repo = MagicMock()
        use_case = LogoutUseCase(user_repo, auth)

        with self.assertRaises(PermissionError):
            use_case.execute_current_session()

        user_repo.increment_token_version_by_id.assert_not_called()
        auth.logout.assert_not_called()
