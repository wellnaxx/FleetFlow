import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.application.models.user_record import UserRecord
from src.application.services.auth_service import AuthService
from src.domain.entities.users.employee import Employee
from src.domain.entities.users.manager import Manager

VALID_PASSWORD_HASH = "pbkdf2_sha256$200000$U0FMVFNBTFRTQUxUU0FMVA==$SEFTSEhBU0hIQVNI"


class AuthService_Should(unittest.TestCase):
    def make_service(self) -> tuple[AuthService, MagicMock]:
        store = MagicMock()
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
            role=SimpleNamespace(value="EMPLOYEE"),  # type: ignore[reportArgumentType]
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

        with self.assertRaises(ValueError) as ctx:
            svc.register_user(
                username="  ",
                role=SimpleNamespace(value="EMPLOYEE"),  # type: ignore[reportArgumentType]
                name="Alice",
                email="",
                phone_number="",
                password="Secret123!",
            )

        self.assertIn("Username is required", str(ctx.exception))
        store.create.assert_not_called()

    def test_register_user_enforces_minimum_password_length(self) -> None:
        svc, store = self.make_service()

        with self.assertRaises(ValueError) as ctx:
            svc.register_user(
                username="alice",
                role=SimpleNamespace(value="EMPLOYEE"),  # type: ignore[reportArgumentType]
                name="Alice",
                email="",
                phone_number="",
                password="short7",
            )

        self.assertIn("at least 8", str(ctx.exception))
        store.create.assert_not_called()

    def test_register_user_enforces_password_strength_policy(self) -> None:
        svc, store = self.make_service()

        with self.assertRaises(ValueError) as ctx:
            svc.register_user(
                username="alice",
                role=SimpleNamespace(value="EMPLOYEE"),  # type: ignore[reportArgumentType]
                name="Alice",
                email="",
                phone_number="",
                password="NoSpecial1",
            )

        self.assertIn("at least one special character", str(ctx.exception))
        store.create.assert_not_called()

    @patch("src.application.services.auth_service.Employee")
    @patch("src.application.services.auth_service.Manager")
    @patch("src.application.services.auth_service.verify_password", return_value=True)
    @patch("src.application.services.auth_service.PasswordHash.parse", return_value=object())
    @patch("src.application.services.auth_service.ContactInfo")
    def test_login_success_manager_and_sets_last_username(
        self,
        ContactInfo: MagicMock,
        _parse: MagicMock,
        _verify: MagicMock,
        Manager: MagicMock,
        Employee: MagicMock,
    ) -> None:
        svc, store = self.make_service()

        # Return a record for a manager
        rec = SimpleNamespace(
            user_id=101,
            username="boss",
            password="stored-hash",
            role="MANAGER",
            name="Bea",
            email="bea@ex.com",
            phone_number="0400",
        )
        store.get.return_value = rec

        # ContactInfo returns the same values for simplicity
        ContactInfo.side_effect = lambda name, email, phone_number: SimpleNamespace(  # type: ignore[reportUnknownLambdaType]
            name=name, email=email, phone_number=phone_number
        )

        user = svc.login("boss", "CorrectHorse")
        # Constructed as Manager
        Manager.assert_called_once_with(101, "Bea", "bea@ex.com", "0400")
        self.assertEqual(svc.current_user, Manager.return_value)
        self.assertEqual(user, Manager.return_value)
        self.assertEqual(svc.last_username, "boss")

    @patch("src.application.services.auth_service.Employee")
    @patch("src.application.services.auth_service.verify_password", return_value=True)
    @patch("src.application.services.auth_service.PasswordHash.parse", return_value=object())
    @patch("src.application.services.auth_service.ContactInfo")
    def test_login_success_employee(
        self, ContactInfo: MagicMock, _parse: MagicMock, _verify: MagicMock, Employee: MagicMock
    ) -> None:
        svc, store = self.make_service()
        rec = SimpleNamespace(
            user_id=202,
            username="alice",
            password="stored-hash",
            role="EMPLOYEE",  # anything not equal to Role.MANAGER.value becomes Employee
            name="Alice",
            email="a@x",
            phone_number="0412",
        )
        store.get.return_value = rec
        ContactInfo.side_effect = lambda name, email, phone_number: SimpleNamespace(  # type: ignore[reportUnknownLambdaType]
            name=name, email=email, phone_number=phone_number
        )

        user = svc.login("alice", "ok")
        Employee.assert_called_once_with(202, "Alice", "a@x", "0412")
        self.assertEqual(user, Employee.return_value)
        self.assertEqual(svc.last_username, "alice")

    @patch("src.application.services.auth_service.verify_password", return_value=False)
    @patch("src.application.services.auth_service.PasswordHash.parse", return_value=object())
    def test_login_wrong_password_raises_and_does_not_set_state(
        self, _parse: MagicMock, _verify: MagicMock
    ) -> None:
        svc, store = self.make_service()
        store.get.return_value = SimpleNamespace(
            user_id=1,
            username="u",
            password="hash",
            role="EMPLOYEE",
            name="N",
            email="",
            phone_number="",
        )
        with self.assertRaises(ValueError) as ctx:
            svc.login("u", "bad")
        self.assertIn("Invalid username or password.", str(ctx.exception))
        self.assertIsNone(svc.current_user)
        self.assertIsNone(svc.last_username)

    def test_login_unknown_user_raises(self) -> None:
        svc, store = self.make_service()
        store.get.return_value = None
        with self.assertRaises(ValueError) as ctx:
            svc.login("nouser", "pw")
        self.assertIn("Invalid username or password.", str(ctx.exception))
        self.assertIsNone(svc.current_user)
        self.assertIsNone(svc.last_username)

    def test_logout_clears_current_user_and_last_username(self) -> None:
        svc, _store = self.make_service()
        svc._current_user = object()  # type: ignore[reportAttributeAccessIssue]
        svc.last_username = "someone"
        svc.logout()
        self.assertIsNone(svc.current_user)
        self.assertIsNone(svc.last_username)

    @patch("src.application.services.auth_service.hash_password")
    @patch("src.application.services.auth_service.verify_password")
    @patch("src.application.services.auth_service.PasswordHash.parse", return_value=object())
    def test_change_password_happy_path(
        self, _parse: MagicMock, verify_password: MagicMock, hash_password: MagicMock
    ) -> None:
        svc, store = self.make_service()
        rec = SimpleNamespace(username="alice", password="OLDHASH")
        store.get.return_value = rec

        # old matches, new does NOT match old
        verify_password.side_effect = [True, False]  # [old_ok, new_same?]
        hashed = SimpleNamespace(serialize=lambda: "NEWHASH")
        hash_password.return_value = hashed

        svc.change_password("alice", "Old123456", "New123456")

        store.update_password.assert_called_once_with("alice", hashed)

    @patch("src.application.services.auth_service.verify_password")
    @patch("src.application.services.auth_service.PasswordHash.parse", return_value=object())
    def test_change_password_unknown_user_raises(self, _parse: MagicMock, verify_password: MagicMock) -> None:
        svc, store = self.make_service()
        store.get.return_value = None
        with self.assertRaises(ValueError) as ctx:
            svc.change_password("nope", "x", "y")
        self.assertIn("User not found.", str(ctx.exception))
        verify_password.assert_not_called()

    @patch("src.application.services.auth_service.verify_password")
    @patch("src.application.services.auth_service.PasswordHash.parse", return_value=object())
    def test_change_password_old_incorrect_raises(self, _parse: MagicMock, verify_password: MagicMock) -> None:
        svc, store = self.make_service()
        store.get.return_value = SimpleNamespace(password="HASH")
        verify_password.side_effect = [False]  # old password fails
        with self.assertRaises(ValueError) as ctx:
            svc.change_password("u", "bad", "New123456")
        self.assertIn("Old password incorrect.", str(ctx.exception))

    @patch("src.application.services.auth_service.verify_password")
    @patch("src.application.services.auth_service.PasswordHash.parse", return_value=object())
    def test_change_password_new_same_as_old_raises(
        self, _parse: MagicMock, verify_password: MagicMock
    ) -> None:
        svc, store = self.make_service()
        store.get.return_value = SimpleNamespace(password="HASH")
        # old ok, new matches old
        verify_password.side_effect = [True, True]
        with self.assertRaises(ValueError) as ctx:
            svc.change_password("u", "Old123456", "Old123456")
        self.assertIn("New password must be different from the old one.", str(ctx.exception))

    @patch("src.application.services.auth_service.hash_password")
    def test_reset_password_enforces_min_length_and_saves(self, hash_password: MagicMock) -> None:
        svc, store = self.make_service()
        rec = SimpleNamespace(username="u", password="OLD")
        store.get.return_value = rec
        hashed = SimpleNamespace(serialize=lambda: "NEWHASH")
        hash_password.return_value = hashed

        # Too short -> error (via _set_password)
        with self.assertRaises(ValueError) as ctx:
            svc.reset_password("u", "short7")
        self.assertIn("at least 8", str(ctx.exception))
        store.update_password.assert_not_called()

        # Long enough -> ok
        svc.reset_password("u", "LongEnough8!")
        store.update_password.assert_called_once_with("u", hashed)

    def test_reset_password_enforces_password_strength_policy(self) -> None:
        svc, store = self.make_service()
        store.get.return_value = SimpleNamespace(username="u", password="OLD")

        with self.assertRaises(ValueError) as ctx:
            svc.reset_password("u", "NoSpecial1")

        self.assertIn("at least one special character", str(ctx.exception))
        store.update_password.assert_not_called()

    @patch("src.application.services.auth_service.hash_password")
    def test_auth_service_works_with_in_memory_repository(self, hash_password: MagicMock) -> None:
        from src.adapters.driven.persistence.memory.user_repository import InMemoryUserRepository
        from src.domain.enums.auth import Role

        hash_password.side_effect = [
            SimpleNamespace(serialize=lambda: "HASH1"),
            SimpleNamespace(serialize=lambda: "HASH2"),
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

        with (
            patch("src.application.services.auth_service.PasswordHash.parse", return_value=object()),
            patch(
                "src.application.services.auth_service.verify_password", side_effect=[True, True, False, True]
            ),
        ):
            user1 = svc.login("ALICE", "Secret123!")
            self.assertEqual(user1.name, "Alice")

            svc.change_password("alice", "Secret123!", "NewSecret123!")

            user2 = svc.login("alice", "NewSecret123!")
            self.assertEqual(user2.name, "Alice")

    def test_reset_password_unknown_user_raises(self) -> None:
        svc, store = self.make_service()
        store.get.return_value = None
        with self.assertRaises(ValueError) as ctx:
            svc.reset_password("ghost", "NewPass123")
        self.assertIn("User not found.", str(ctx.exception))

    @patch("src.application.services.auth_service.verify_password", return_value=True)
    def test_login_preserves_user_id_for_manager(self, mock_verify: MagicMock) -> None:
        store = MagicMock()
        auth = AuthService(store)

        store.get.return_value = UserRecord(
            user_id=42,
            username="alice",
            role="MANAGER",
            name="Alice",
            email="alice@example.com",
            phone_number="0412345678",
            password=VALID_PASSWORD_HASH,
        )

        user = auth.login("alice", "pw")

        self.assertIsInstance(user, Manager)
        self.assertEqual(user.user_id, 42)
        self.assertEqual(user.name, "Alice")
        self.assertEqual(auth.current_user, user)
        mock_verify.assert_called_once()

    @patch("src.application.services.auth_service.verify_password", return_value=True)
    def test_login_preserves_user_id_for_employee(self, mock_verify: MagicMock) -> None:
        store = MagicMock()
        auth = AuthService(store)

        store.get.return_value = UserRecord(
            user_id=17,
            username="bob",
            role="EMPLOYEE",
            name="Bob",
            email="bob@example.com",
            phone_number="0400123456",
            password=VALID_PASSWORD_HASH,
        )

        user = auth.login("bob", "pw")

        self.assertIsInstance(user, Employee)
        self.assertEqual(user.user_id, 17)
        self.assertEqual(user.name, "Bob")
        self.assertEqual(auth.current_user, user)
        mock_verify.assert_called_once()

    @patch("src.application.services.auth_service.verify_password", return_value=True)
    def test_login_rejects_unknown_persisted_role(self, mock_verify: MagicMock) -> None:
        store = MagicMock()
        auth = AuthService(store)
        store.get.return_value = UserRecord(
            user_id=99,
            username="badrole",
            role="OWNER",
            name="Bad Role",
            email="badrole@example.com",
            phone_number="0412345678",
            password=VALID_PASSWORD_HASH,
        )

        with self.assertRaises(ValueError) as ctx:
            auth.login("badrole", "pw")

        self.assertIn("Invalid persisted role", str(ctx.exception))
        self.assertIsNone(auth.current_user)
        mock_verify.assert_called_once()
