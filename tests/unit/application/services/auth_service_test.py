import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.application.exceptions.application_errors import (
    AuthenticationError,
    NotFoundError,
    ValidationError,
)
from src.application.exceptions.password_errors import LoginInvalidUserRuntimeError
from src.application.models.user_record import UserRecord
from src.application.services.auth_service import AuthService
from src.domain.enums.auth import Role

VALID_PASSWORD_HASH = "pbkdf2_sha256$200000$U0FMVFNBTFRTQUxUU0FMVA==$SEFTSEhBU0hIQVNI"


def _user_record(
    *,
    user_id: int = 1,
    username: str = "u",
    password: str = "OLD",
    role: str = "EMPLOYEE",
    name: str = "User",
    email: str = "",
    phone_number: str = "",
) -> UserRecord:
    return UserRecord(
        user_id=user_id,
        username=username,
        role=role,
        name=name,
        email=email,
        phone_number=phone_number,
        password=password,
    )


class AuthService_Should(unittest.TestCase):
    def make_service(self) -> tuple[AuthService, MagicMock]:
        store = MagicMock()
        store.get_by_username.return_value = None
        svc = AuthService(user_store=store)  # type: ignore[reportArgumentType]
        return svc, store

    @patch("src.application.services.auth_service.hash_password")
    @patch("src.application.services.auth_service.ContactInfo")
    def test_register_user_passes_cleaned_fields_and_hashed_password(
        self, ContactInfo: MagicMock, hash_password: MagicMock
    ) -> None:
        svc, store = self.make_service()

        # Make ContactInfo echo “cleaned” values (simulate normalization)
        ContactInfo.side_effect = lambda name, email, phone_number: SimpleNamespace(  # type: ignore[reportUnknownLambdaType]
            name=name.strip(),  # type: ignore[reportUnknownMemberType]
            email=(email or "").strip().lower(),  # type: ignore[reportUnknownMemberType]
            phone_number=phone_number.strip(),  # type: ignore[reportUnknownMemberType]
        )
        hash_password.return_value = "HASHED!"

        svc.register_user(
            username="  User1  ",
            role=Role.EMPLOYEE,
            name="  Alice  ",
            email="  Alice@EX.com ",
            phone_number=" 0412 345 ",
            password="Secret123!",
        )

        store.create.assert_called_once_with(
            username="user1",
            role="EMPLOYEE",
            name="Alice",
            email="alice@ex.com",
            phone_number="0412 345",
            password_hash="HASHED!",
        )

    def test_register_user_rejects_blank_username(self) -> None:
        svc, store = self.make_service()

        with self.assertRaises(ValidationError) as ctx:
            svc.register_user(
                username="  ",
                role=Role.EMPLOYEE,
                name="Alice",
                email="",
                phone_number="",
                password="Secret123!",
            )

        self.assertIn("Username is required", str(ctx.exception))
        store.create.assert_not_called()

    def test_register_user_enforces_minimum_password_length(self) -> None:
        svc, store = self.make_service()

        with self.assertRaises(ValidationError) as ctx:
            svc.register_user(
                username="alice",
                role=Role.EMPLOYEE,
                name="Alice",
                email="",
                phone_number="",
                password="short7",
            )

        self.assertIn("at least 8", str(ctx.exception))
        store.create.assert_not_called()

    def test_register_user_enforces_password_strength_policy(self) -> None:
        svc, store = self.make_service()

        with self.assertRaises(ValidationError) as ctx:
            svc.register_user(
                username="alice",
                role=Role.EMPLOYEE,
                name="Alice",
                email="",
                phone_number="",
                password="NoSpecial1",
            )

        self.assertIn("at least one special character", str(ctx.exception))
        store.create.assert_not_called()

    @patch("src.application.services.auth_service.verify_password", return_value=True)
    @patch("src.application.services.auth_service.PasswordHash.parse", return_value=object())
    def test_login_success_manager_sets_current_principal(
        self,
        _parse: MagicMock,
        _verify: MagicMock,
    ) -> None:
        svc, store = self.make_service()

        rec = SimpleNamespace(
            user_id=101,
            username="boss",
            password="stored-hash",
            role="MANAGER",
            name="Bea",
            email="bea@ex.com",
            phone_number="0412345678",
        )
        store.get_by_username.return_value = rec

        principal, record = svc.login("boss", "CorrectHorse")

        self.assertIs(record, rec)
        self.assertEqual(principal.user_id, 101)
        self.assertEqual(principal.username, "boss")
        self.assertEqual(principal.name, "Bea")
        self.assertEqual(principal.email, "bea@ex.com")
        self.assertEqual(principal.phone_number, "0412345678")
        self.assertIs(principal.role, Role.MANAGER)
        self.assertEqual(svc.current_user, principal)

    @patch("src.application.services.auth_service.verify_password", return_value=True)
    @patch("src.application.services.auth_service.PasswordHash.parse", return_value=object())
    def test_login_success_employee(self, _parse: MagicMock, _verify: MagicMock) -> None:
        svc, store = self.make_service()
        rec = SimpleNamespace(
            user_id=202,
            username="alice",
            password="stored-hash",
            role="EMPLOYEE",
            name="Alice",
            email="alice@example.com",
            phone_number="0498765432",
        )
        store.get_by_username.return_value = rec

        principal, record = svc.login("alice", "ok")

        self.assertIs(record, rec)
        self.assertEqual(principal.user_id, 202)
        self.assertEqual(principal.username, "alice")
        self.assertEqual(principal.name, "Alice")
        self.assertEqual(principal.email, "alice@example.com")
        self.assertEqual(principal.phone_number, "0498765432")
        self.assertIs(principal.role, Role.EMPLOYEE)

    @patch("src.application.services.auth_service.verify_password", return_value=False)
    @patch("src.application.services.auth_service.PasswordHash.parse", return_value=object())
    def test_login_wrong_password_raises_and_does_not_set_state(
        self, _parse: MagicMock, _verify: MagicMock
    ) -> None:
        svc, store = self.make_service()
        store.get_by_username.return_value = SimpleNamespace(
            user_id=1,
            username="u",
            password="hash",
            role="EMPLOYEE",
            name="N",
            email="",
            phone_number="",
        )
        with self.assertRaises(AuthenticationError) as ctx:
            svc.login("u", "bad")
        self.assertIn("Invalid username or password.", str(ctx.exception))
        self.assertIsNone(svc.current_user)

    def test_login_unknown_user_raises(self) -> None:
        svc, store = self.make_service()
        store.get_by_username.return_value = None
        with self.assertRaises(AuthenticationError) as ctx:
            svc.login("nouser", "pw")
        self.assertIn("Invalid username or password.", str(ctx.exception))
        self.assertIsNone(svc.current_user)

    def test_logout_clears_current_user(self) -> None:
        svc, _store = self.make_service()
        svc._current_user = object()  # type: ignore[reportAttributeAccessIssue]
        svc.logout()
        self.assertIsNone(svc.current_user)

    @patch("src.application.services.auth_service.hash_password")
    @patch("src.application.services.auth_service.verify_password")
    @patch("src.application.services.auth_service.PasswordHash.parse", return_value=object())
    def test_change_password_happy_path(
        self, _parse: MagicMock, verify_password: MagicMock, hash_password: MagicMock
    ) -> None:
        svc, store = self.make_service()
        rec = _user_record(user_id=10, username="alice", password="OLDHASH")
        store.get_by_username.return_value = rec

        # old matches, new does NOT match old
        verify_password.side_effect = [True, False]  # [old_ok, new_same?]
        hashed = SimpleNamespace(serialize=lambda: "NEWHASH")
        hash_password.return_value = hashed

        svc.change_password("alice", "Old123456", "New123456")

        store.update_password.assert_called_once_with("alice", hashed)
        store.increment_token_version_by_id.assert_not_called()
        store.increment_token_version_by_username.assert_not_called()

    @patch("src.application.services.auth_service.verify_password")
    @patch("src.application.services.auth_service.PasswordHash.parse", return_value=object())
    def test_change_password_unknown_user_raises(self, _parse: MagicMock, verify_password: MagicMock) -> None:
        svc, store = self.make_service()
        store.get_by_username.return_value = None
        with self.assertRaises(NotFoundError) as ctx:
            svc.change_password("nope", "x", "y")
        self.assertIn("User not found.", str(ctx.exception))
        verify_password.assert_not_called()

    @patch("src.application.services.auth_service.verify_password")
    @patch("src.application.services.auth_service.PasswordHash.parse", return_value=object())
    def test_change_password_old_incorrect_raises(self, _parse: MagicMock, verify_password: MagicMock) -> None:
        svc, store = self.make_service()
        store.get_by_username.return_value = _user_record(password="HASH")
        verify_password.side_effect = [False]  # old password fails
        with self.assertRaises(AuthenticationError) as ctx:
            svc.change_password("u", "bad", "New123456")
        self.assertIn("Old password incorrect.", str(ctx.exception))

    @patch("src.application.services.auth_service.verify_password")
    @patch("src.application.services.auth_service.PasswordHash.parse", return_value=object())
    def test_change_password_new_same_as_old_raises(
        self, _parse: MagicMock, verify_password: MagicMock
    ) -> None:
        svc, store = self.make_service()
        store.get_by_username.return_value = _user_record(password="HASH")
        # old ok, new matches old
        verify_password.side_effect = [True, True]
        with self.assertRaises(ValidationError) as ctx:
            svc.change_password("u", "Old123456", "Old123456")
        self.assertIn("New password must be different from the old one.", str(ctx.exception))

    @patch("src.application.services.auth_service.hash_password")
    def test_reset_password_enforces_min_length_and_saves(self, hash_password: MagicMock) -> None:
        svc, store = self.make_service()
        rec = _user_record(username="u", password="OLD")
        store.get_by_username.return_value = rec
        hashed = SimpleNamespace(serialize=lambda: "NEWHASH")
        hash_password.return_value = hashed

        # Too short -> error (via _set_password)
        with self.assertRaises(ValidationError) as ctx:
            svc.reset_password("u", "short7")
        self.assertIn("at least 8", str(ctx.exception))
        store.update_password.assert_not_called()

        # Long enough -> ok
        svc.reset_password("u", "LongEnough8!")
        store.update_password.assert_called_once_with("u", hashed)
        store.increment_token_version_by_id.assert_not_called()
        store.increment_token_version_by_username.assert_not_called()

    @patch("src.application.services.auth_service.hash_password")
    def test_reset_password_enforces_password_strength_policy(self, hash_password: MagicMock) -> None:
        svc, store = self.make_service()
        store.get_by_username.return_value = _user_record(username="u", password="OLD")
        hash_password.side_effect = ValueError("at least one special character")

        with self.assertRaises(ValidationError) as ctx:
            svc.reset_password("u", "NoSpecial1")

        self.assertIn("at least one special character", str(ctx.exception))
        store.update_password.assert_not_called()

    @patch("src.application.services.auth_service.hash_password")
    def test_auth_service_works_with_in_memory_repository(self, hash_password: MagicMock) -> None:
        from src.adapters.driven.persistence.memory.user_repository import InMemoryUserRepository

        hash_password.side_effect = [
            SimpleNamespace(serialize=lambda: "HASH1"),
            SimpleNamespace(serialize=lambda: "HASH2"),
            SimpleNamespace(serialize=lambda: "HASH3"),
        ]
        svc = AuthService(user_store=InMemoryUserRepository())

        rec = svc.register_user(
            username="alice",
            role=Role.EMPLOYEE,
            name="Alice",
            email="alice@example.com",
            phone_number="0412345678",
            password="Secret123!",
        )

        self.assertEqual(rec.password, "HASH1")
        self.assertEqual(rec.token_version, 1)

        with (
            patch("src.application.services.auth_service.PasswordHash.parse", return_value=object()),
            patch(
                "src.application.services.auth_service.verify_password", side_effect=[True, True, False, True]
            ),
        ):
            _, user1 = svc.login("ALICE", "Secret123!")
            self.assertEqual(user1.name, "Alice")

            svc.change_password("alice", "Secret123!", "NewSecret123!")
            changed_record = svc._store.get_by_username("alice")  # type: ignore[reportPrivateUsage]
            assert changed_record is not None
            self.assertEqual(changed_record.password, "HASH2")
            self.assertEqual(changed_record.token_version, 2)

            _, user2 = svc.login("alice", "NewSecret123!")
            self.assertEqual(user2.name, "Alice")

        svc.reset_password("alice", "ResetSecret123!")
        reset_record = svc._store.get_by_username("alice")  # type: ignore[reportPrivateUsage]
        assert reset_record is not None
        self.assertEqual(reset_record.password, "HASH3")
        self.assertEqual(reset_record.token_version, 3)

    def test_reset_password_unknown_user_raises(self) -> None:
        svc, store = self.make_service()
        store.get_by_username.return_value = None
        with self.assertRaises(NotFoundError) as ctx:
            svc.reset_password("ghost", "NewPass123")
        self.assertIn("User not found.", str(ctx.exception))

    @patch("src.application.services.auth_service.verify_password", return_value=True)
    def test_login_preserves_user_id_for_manager(self, mock_verify: MagicMock) -> None:
        store = MagicMock()
        auth = AuthService(store)

        store.get_by_username.return_value = UserRecord(
            user_id=42,
            username="alice",
            role="MANAGER",
            name="Alice",
            email="alice@example.com",
            phone_number="0412345678",
            password=VALID_PASSWORD_HASH,
        )

        principal, record = auth.login("alice", "pw")

        self.assertIs(record, store.get_by_username.return_value)
        self.assertEqual(principal.user_id, 42)
        self.assertEqual(principal.username, "alice")
        self.assertEqual(principal.name, "Alice")
        self.assertIs(principal.role, Role.MANAGER)
        self.assertEqual(auth.current_user, principal)
        mock_verify.assert_called_once()

    @patch("src.application.services.auth_service.verify_password", return_value=True)
    def test_login_preserves_user_id_for_employee(self, mock_verify: MagicMock) -> None:
        store = MagicMock()
        auth = AuthService(store)

        store.get_by_username.return_value = UserRecord(
            user_id=17,
            username="bob",
            role="EMPLOYEE",
            name="Bob",
            email="bob@example.com",
            phone_number="0400123456",
            password=VALID_PASSWORD_HASH,
        )

        principal, record = auth.login("bob", "pw")

        self.assertIs(record, store.get_by_username.return_value)
        self.assertEqual(principal.user_id, 17)
        self.assertEqual(principal.username, "bob")
        self.assertEqual(principal.name, "Bob")
        self.assertIs(principal.role, Role.EMPLOYEE)
        self.assertEqual(auth.current_user, principal)
        mock_verify.assert_called_once()

    @patch("src.application.services.auth_service.verify_password", return_value=True)
    def test_login_rejects_unknown_persisted_role(self, mock_verify: MagicMock) -> None:
        store = MagicMock()
        auth = AuthService(store)
        store.get_by_username.return_value = UserRecord(
            user_id=99,
            username="badrole",
            role="OWNER",
            name="Bad Role",
            email="badrole@example.com",
            phone_number="0412345678",
            password=VALID_PASSWORD_HASH,
        )

        with self.assertRaises(LoginInvalidUserRuntimeError) as ctx:
            auth.login("badrole", "pw")

        self.assertIn("Invalid persisted role", str(ctx.exception))
        self.assertEqual(ctx.exception.user_id, 99)
        self.assertEqual(ctx.exception.username, "badrole")
        self.assertIsNone(auth.current_user)
        mock_verify.assert_called_once()
