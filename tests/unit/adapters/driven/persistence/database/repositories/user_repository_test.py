import unittest
from unittest.mock import MagicMock, patch

from src.adapters.driven.persistence.database.queries import QUERIES
from src.adapters.driven.persistence.database.repositories.user_repository import PostgresUserRepository
from src.adapters.driven.security.password_hasher import PasswordHash
from src.application.models.user_record import UserRecord
from src.domain.enums.auth import Role

MODULE = "src.adapters.driven.persistence.database.repositories.user_repository"


class PostgresUserRepository_Should(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = PostgresUserRepository()
        self.password_hash = PasswordHash(
            algo="sha256",
            iterations=200_000,
            salt_b64="salt",
            hash_b64="hash",
        )

    @patch(f"{MODULE}.fetch_one", return_value=None)
    @patch(f"{MODULE}.map_user_record")
    def test_get_returns_none_for_blank_username(
        self,
        map_user_record_mock: MagicMock,
        fetch_one_mock: MagicMock,
    ) -> None:
        user = self.repo.get_by_username("   ")

        self.assertIsNone(user)
        fetch_one_mock.assert_not_called()
        map_user_record_mock.assert_not_called()

    @patch(f"{MODULE}.fetch_one", return_value=None)
    @patch(f"{MODULE}.map_user_record")
    def test_get_returns_none_when_user_is_missing(
        self,
        map_user_record_mock: MagicMock,
        fetch_one_mock: MagicMock,
    ) -> None:
        user = self.repo.get_by_username(" Alice ")

        self.assertIsNone(user)
        fetch_one_mock.assert_called_once_with(QUERIES.users.get_by_username, ("alice",))
        map_user_record_mock.assert_not_called()

    @patch(f"{MODULE}.fetch_one")
    @patch(f"{MODULE}.map_user_record")
    def test_get_maps_existing_user(
        self,
        map_user_record_mock: MagicMock,
        fetch_one_mock: MagicMock,
    ) -> None:
        row = self._user_row()
        expected = self._user_record()
        fetch_one_mock.return_value = row
        map_user_record_mock.return_value = expected

        user = self.repo.get_by_username(" Alice ")

        self.assertIs(user, expected)
        fetch_one_mock.assert_called_once_with(QUERIES.users.get_by_username, ("alice",))
        map_user_record_mock.assert_called_once_with(row)

    @patch(f"{MODULE}.execute_insert", return_value=9)
    @patch(f"{MODULE}.fetch_one", return_value=None)
    def test_create_validates_and_inserts_user(
        self,
        fetch_one_mock: MagicMock,
        execute_insert_mock: MagicMock,
    ) -> None:
        user = self.repo.create(
            username=" Alice ",
            role="manager",
            name=" Alice Admin ",
            email="ALICE@example.com",
            phone_number="0412345678",
            password_hash=self.password_hash,
        )

        fetch_one_mock.assert_called_once_with(QUERIES.users.get_by_username, ("alice",))
        execute_insert_mock.assert_called_once_with(
            QUERIES.users.add,
            (
                "Alice",
                Role.MANAGER.value,
                "Alice Admin",
                "alice@example.com",
                "0412345678",
                self.password_hash.serialize(),
            ),
        )
        self.assertEqual(user.user_id, 9)
        self.assertEqual(user.username, "Alice")
        self.assertEqual(user.role, Role.MANAGER.value)
        self.assertEqual(user.name, "Alice Admin")
        self.assertEqual(user.email, "alice@example.com")
        self.assertEqual(user.phone_number, "0412345678")
        self.assertEqual(user.password, self.password_hash.serialize())
        self.assertEqual(user.token_version, 1)

    @patch(f"{MODULE}.fetch_one", return_value=None)
    def test_create_rejects_blank_username(self, fetch_one_mock: MagicMock) -> None:
        with self.assertRaises(ValueError) as ctx:
            self.repo.create("", "EMPLOYEE", "Alice", "", "", self.password_hash)

        self.assertIn("Username is required.", str(ctx.exception))
        fetch_one_mock.assert_not_called()

    @patch(f"{MODULE}.fetch_one")
    def test_create_rejects_duplicate_username(self, fetch_one_mock: MagicMock) -> None:
        fetch_one_mock.return_value = self._user_row()

        with self.assertRaises(ValueError) as ctx:
            self.repo.create("Alice", "EMPLOYEE", "Alice", "", "", self.password_hash)

        self.assertIn("Username already exists.", str(ctx.exception))

    @patch(f"{MODULE}.fetch_one", return_value=None)
    def test_create_rejects_invalid_role(self, fetch_one_mock: MagicMock) -> None:
        with self.assertRaises(ValueError):
            self.repo.create("Alice", "ADMIN", "Alice", "", "", self.password_hash)

        fetch_one_mock.assert_called_once_with(QUERIES.users.get_by_username, ("alice",))

    @patch(f"{MODULE}.fetch_one", return_value=None)
    def test_create_rejects_invalid_password_hash_type(self, fetch_one_mock: MagicMock) -> None:
        with self.assertRaises(TypeError) as ctx:
            self.repo.create("Alice", "EMPLOYEE", "Alice", "", "", object())  # type: ignore[arg-type]

        self.assertIn("password_hash must be a PasswordHash", str(ctx.exception))
        fetch_one_mock.assert_called_once_with(QUERIES.users.get_by_username, ("alice",))

    @patch(f"{MODULE}.execute_write")
    @patch(f"{MODULE}.fetch_one")
    def test_update_password_writes_serialized_hash_for_existing_user(
        self,
        fetch_one_mock: MagicMock,
        execute_write_mock: MagicMock,
    ) -> None:
        fetch_one_mock.return_value = self._user_row()

        self.repo.update_password(" Alice ", self.password_hash)

        fetch_one_mock.assert_called_once_with(QUERIES.users.get_by_username, ("alice",))
        execute_write_mock.assert_called_once_with(
            QUERIES.users.update_password,
            (self.password_hash.serialize(), "alice"),
        )

    @patch(f"{MODULE}.execute_write")
    @patch(f"{MODULE}.fetch_one", return_value=None)
    def test_update_password_rejects_missing_user(
        self,
        fetch_one_mock: MagicMock,
        execute_write_mock: MagicMock,
    ) -> None:
        with self.assertRaises(ValueError) as ctx:
            self.repo.update_password("Alice", self.password_hash)

        self.assertIn("User with username Alice not found", str(ctx.exception))
        fetch_one_mock.assert_called_once_with(QUERIES.users.get_by_username, ("alice",))
        execute_write_mock.assert_not_called()

    def test_save_is_noop(self) -> None:
        self.assertIsNone(self.repo.save())

    @patch(f"{MODULE}.fetch_all")
    @patch(f"{MODULE}.map_user_record")
    def test_list_users_maps_all_rows(
        self,
        map_user_record_mock: MagicMock,
        fetch_all_mock: MagicMock,
    ) -> None:
        rows = [self._user_row(), {**self._user_row(), "user_id": 2, "username": "Bob"}]
        users = [self._user_record(), self._user_record(user_id=2, username="Bob")]
        fetch_all_mock.return_value = rows
        map_user_record_mock.side_effect = users

        result = self.repo.list_users()

        self.assertEqual(result, users)
        fetch_all_mock.assert_called_once_with(QUERIES.users.list_all)
        self.assertEqual([call.args[0] for call in map_user_record_mock.call_args_list], rows)

    @patch(f"{MODULE}.fetch_one", return_value=None)
    @patch(f"{MODULE}.map_user_record")
    def test_get_by_id_returns_none_when_user_is_missing(
        self,
        map_user_record_mock: MagicMock,
        fetch_one_mock: MagicMock,
    ) -> None:
        user = self.repo.get_by_id(99)

        self.assertIsNone(user)
        fetch_one_mock.assert_called_once_with(QUERIES.users.get_by_id, (99,))
        map_user_record_mock.assert_not_called()

    @patch(f"{MODULE}.fetch_one")
    @patch(f"{MODULE}.map_user_record")
    def test_get_by_id_maps_existing_user(
        self,
        map_user_record_mock: MagicMock,
        fetch_one_mock: MagicMock,
    ) -> None:
        row = self._user_row()
        expected = self._user_record()
        fetch_one_mock.return_value = row
        map_user_record_mock.return_value = expected

        user = self.repo.get_by_id(1)

        self.assertIs(user, expected)
        fetch_one_mock.assert_called_once_with(QUERIES.users.get_by_id, (1,))
        map_user_record_mock.assert_called_once_with(row)

    @patch(f"{MODULE}.execute_returning_one", return_value=None)
    @patch(f"{MODULE}.map_user_record")
    def test_increment_token_version_by_id_returns_none_when_user_is_missing(
        self,
        map_user_record_mock: MagicMock,
        execute_returning_one_mock: MagicMock,
    ) -> None:
        user = self.repo.increment_token_version_by_id(99)

        self.assertIsNone(user)
        execute_returning_one_mock.assert_called_once_with(QUERIES.users.increment_token_version_by_id, (99,))
        map_user_record_mock.assert_not_called()

    @patch(f"{MODULE}.execute_returning_one")
    @patch(f"{MODULE}.map_user_record")
    def test_increment_token_version_by_id_maps_returned_user(
        self,
        map_user_record_mock: MagicMock,
        execute_returning_one_mock: MagicMock,
    ) -> None:
        row = {**self._user_row(), "token_version": 2}
        expected = self._user_record()
        execute_returning_one_mock.return_value = row
        map_user_record_mock.return_value = expected

        user = self.repo.increment_token_version_by_id(1)

        self.assertIs(user, expected)
        execute_returning_one_mock.assert_called_once_with(QUERIES.users.increment_token_version_by_id, (1,))
        map_user_record_mock.assert_called_once_with(row)

    @patch(f"{MODULE}.execute_returning_one", return_value=None)
    @patch(f"{MODULE}.map_user_record")
    def test_increment_token_version_by_username_returns_none_when_user_is_missing(
        self,
        map_user_record_mock: MagicMock,
        execute_returning_one_mock: MagicMock,
    ) -> None:
        user = self.repo.increment_token_version_by_username(" Alice ")

        self.assertIsNone(user)
        execute_returning_one_mock.assert_called_once_with(
            QUERIES.users.increment_token_version_by_username,
            ("alice",),
        )
        map_user_record_mock.assert_not_called()

    @patch(f"{MODULE}.execute_returning_one")
    @patch(f"{MODULE}.map_user_record")
    def test_increment_token_version_by_username_maps_returned_user(
        self,
        map_user_record_mock: MagicMock,
        execute_returning_one_mock: MagicMock,
    ) -> None:
        row = {**self._user_row(), "token_version": 2}
        expected = self._user_record()
        execute_returning_one_mock.return_value = row
        map_user_record_mock.return_value = expected

        user = self.repo.increment_token_version_by_username(" Alice ")

        self.assertIs(user, expected)
        execute_returning_one_mock.assert_called_once_with(
            QUERIES.users.increment_token_version_by_username,
            ("alice",),
        )
        map_user_record_mock.assert_called_once_with(row)

    def _user_row(self) -> dict[str, object]:
        return {
            "user_id": 1,
            "username": "Alice",
            "role": Role.EMPLOYEE.value,
            "name": "Alice",
            "email": "",
            "phone": "",
            "password_hash": self.password_hash.serialize(),
            "token_version": 1,
        }

    def _user_record(self, user_id: int = 1, username: str = "Alice") -> UserRecord:
        return UserRecord(
            user_id=user_id,
            username=username,
            role=Role.EMPLOYEE.value,
            name="Alice",
            email="",
            phone_number="",
            password=self.password_hash.serialize(),
            token_version=1,
        )
