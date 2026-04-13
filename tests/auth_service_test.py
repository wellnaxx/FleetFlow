import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.core.auth_service import AuthService


class AuthService_Should(unittest.TestCase):
    def make_service(self) -> tuple[AuthService, MagicMock]:
        store = MagicMock()
        svc = AuthService(user_store=store)  # type: ignore[reportArgumentType]
        return svc, store

    @patch("src.core.auth_service.hash_password")
    @patch("src.core.auth_service.ContactInfo")
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
            username="user1",
            role=SimpleNamespace(value="EMPLOYEE"),  # type: ignore[reportArgumentType]
            name="  Alice  ",
            email="  Alice@EX.com ",
            phone_number=" 0412 345 ",
            password="Secret123",
        )

        store.create.assert_called_once_with(
            username="user1",
            role="EMPLOYEE",
            name="Alice",
            email="alice@ex.com",
            phone_number="0412 345",
            password_hash="HASHED!",
        )

    @patch("src.core.auth_service.Employee")
    @patch("src.core.auth_service.Manager")
    @patch("src.core.auth_service.verify_password", return_value=True)
    @patch("src.core.auth_service.PasswordHash.parse", return_value=object())
    @patch("src.core.auth_service.ContactInfo")
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
        Manager.assert_called_once_with("Bea", "bea@ex.com", "0400")
        self.assertEqual(svc.current_user, Manager.return_value)
        self.assertEqual(user, Manager.return_value)
        self.assertEqual(svc.last_username, "boss")

    @patch("src.core.auth_service.Employee")
    @patch("src.core.auth_service.verify_password", return_value=True)
    @patch("src.core.auth_service.PasswordHash.parse", return_value=object())
    @patch("src.core.auth_service.ContactInfo")
    def test_login_success_employee(
        self, ContactInfo: MagicMock, _parse: MagicMock, _verify: MagicMock, Employee: MagicMock
    ) -> None:
        svc, store = self.make_service()
        rec = SimpleNamespace(
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
        Employee.assert_called_once_with("Alice", "a@x", "0412")
        self.assertEqual(user, Employee.return_value)
        self.assertEqual(svc.last_username, "alice")

    @patch("src.core.auth_service.verify_password", return_value=False)
    @patch("src.core.auth_service.PasswordHash.parse", return_value=object())
    def test_login_wrong_password_raises_and_does_not_set_state(
        self, _parse: MagicMock, _verify: MagicMock
    ) -> None:
        svc, store = self.make_service()
        store.get.return_value = SimpleNamespace(
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

    @patch("src.core.auth_service.hash_password")
    @patch("src.core.auth_service.verify_password")
    @patch("src.core.auth_service.PasswordHash.parse", return_value=object())
    def test_change_password_happy_path(
        self, _parse: MagicMock, verify_password: MagicMock, hash_password: MagicMock
    ) -> None:
        svc, store = self.make_service()
        rec = SimpleNamespace(password="OLDHASH")
        store.get.return_value = rec

        # old matches, new does NOT match old
        verify_password.side_effect = [True, False]  # [old_ok, new_same?]
        hash_password.return_value = SimpleNamespace(serialize=lambda: "NEWHASH")

        svc.change_password("alice", "Old123456", "New123456")

        # rec.password updated and persisted
        self.assertEqual(rec.password, "NEWHASH")
        store.save.assert_called_once()

    @patch("src.core.auth_service.verify_password")
    @patch("src.core.auth_service.PasswordHash.parse", return_value=object())
    def test_change_password_unknown_user_raises(self, _parse: MagicMock, verify_password: MagicMock) -> None:
        svc, store = self.make_service()
        store.get.return_value = None
        with self.assertRaises(ValueError) as ctx:
            svc.change_password("nope", "x", "y")
        self.assertIn("User not found.", str(ctx.exception))
        verify_password.assert_not_called()

    @patch("src.core.auth_service.verify_password")
    @patch("src.core.auth_service.PasswordHash.parse", return_value=object())
    def test_change_password_old_incorrect_raises(self, _parse: MagicMock, verify_password: MagicMock) -> None:
        svc, store = self.make_service()
        store.get.return_value = SimpleNamespace(password="HASH")
        verify_password.side_effect = [False]  # old password fails
        with self.assertRaises(ValueError) as ctx:
            svc.change_password("u", "bad", "New123456")
        self.assertIn("Old password incorrect.", str(ctx.exception))

    @patch("src.core.auth_service.verify_password")
    @patch("src.core.auth_service.PasswordHash.parse", return_value=object())
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

    @patch("src.core.auth_service.hash_password")
    def test_reset_password_enforces_min_length_and_saves(self, hash_password: MagicMock) -> None:
        svc, store = self.make_service()
        rec = SimpleNamespace(password="OLD")
        store.get.return_value = rec
        hash_password.return_value = SimpleNamespace(serialize=lambda: "NEWHASH")

        # Too short -> error (via _set_password)
        with self.assertRaises(ValueError) as ctx:
            svc.reset_password("u", "short7")
        self.assertIn("at least 8", str(ctx.exception))
        store.save.assert_not_called()

        # Long enough -> ok
        svc.reset_password("u", "LongEnough8")
        self.assertEqual(rec.password, "NEWHASH")
        store.save.assert_called_once()

    def test_reset_password_unknown_user_raises(self) -> None:
        svc, store = self.make_service()
        store.get.return_value = None
        with self.assertRaises(ValueError) as ctx:
            svc.reset_password("ghost", "NewPass123")
        self.assertIn("User not found.", str(ctx.exception))
