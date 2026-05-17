import unittest
from types import SimpleNamespace

from src.adapters.driven.persistence.memory.user_repository import InMemoryUserRepository
from src.application.models.user_record import UserRecord


def _ph(s: str = "hash") -> SimpleNamespace:
    return SimpleNamespace(serialize=lambda: f"SER({s})")


class InMemoryUserRepository_Should(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = InMemoryUserRepository()

    def test_create_stores_normalized_and_cleaned_fields(self) -> None:
        rec = self.repo.create(
            username=" Alice ",
            role="employee",
            name=" Alice Liddell ",
            email=" ALICE@EXAMPLE.COM ",
            phone_number="0412345678",
            password_hash=_ph("pw1"),  # type: ignore[reportArgumentType]
        )

        self.assertEqual(
            rec,
            UserRecord(
                user_id=1,
                username="Alice",
                role="EMPLOYEE",
                name="Alice Liddell",
                email="alice@example.com",
                phone_number="0412345678",
                password="SER(pw1)",
                token_version=1,
            ),
        )

    def test_duplicate_username_is_rejected_case_insensitively(self) -> None:
        self.repo.create("Alice", "EMPLOYEE", "Alice", "", "", _ph("pw1"))  # type: ignore[reportArgumentType]

        with self.assertRaises(ValueError) as ctx:
            self.repo.create("alice", "EMPLOYEE", "Alice", "", "", _ph("pw2"))  # type: ignore[reportArgumentType]

        self.assertIn("Username already exists.", str(ctx.exception))

    def test_duplicate_username_is_rejected_with_whitespace_and_case_variants(self) -> None:
        self.repo.create("Alice", "EMPLOYEE", "Alice", "", "", _ph("pw1"))  # type: ignore[reportArgumentType]

        with self.assertRaises(ValueError) as ctx:
            self.repo.create("  alice  ", "EMPLOYEE", "Alice 2", "", "", _ph("pw2"))  # type: ignore[reportArgumentType]

        self.assertIn("Username already exists.", str(ctx.exception))

    def test_get_is_whitespace_and_case_insensitive(self) -> None:
        rec = self.repo.create("Alice", "EMPLOYEE", "Alice", "", "", _ph("pw1"))  # type: ignore[reportArgumentType]

        self.assertIs(self.repo.get("alice"), rec)
        self.assertIs(self.repo.get(" ALICE "), rec)
        self.assertIs(self.repo.get("\tAlice\n"), rec)

    def test_update_password_updates_only_target_user(self) -> None:
        self.repo.create("alice", "EMPLOYEE", "Alice", "", "", _ph("old1"))  # type: ignore[reportArgumentType]
        self.repo.create("bob", "MANAGER", "Bob", "", "", _ph("old2"))  # type: ignore[reportArgumentType]

        self.repo.update_password("ALICE", _ph("new1"))  # type: ignore[reportArgumentType]

        self.assertEqual(self.repo.get("alice").password, "SER(new1)")  # type: ignore[reportOptionalMemberAccess]
        self.assertEqual(self.repo.get("bob").password, "SER(old2)")  # type: ignore[reportOptionalMemberAccess]

    def test_update_password_unknown_user_raises(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            self.repo.update_password("ghost", _ph("x"))  # type: ignore[reportArgumentType]

        self.assertIn("User not found.", str(ctx.exception))

    def test_update_password_accepts_whitespace_and_case_insensitive_username(self) -> None:
        self.repo.create("Alice", "EMPLOYEE", "Alice", "", "", _ph("old"))  # type: ignore[reportArgumentType]

        self.repo.update_password("  ALICE  ", _ph("new"))  # type: ignore[reportArgumentType]

        self.assertEqual(self.repo.get("alice").password, "SER(new)")  # type: ignore[reportOptionalMemberAccess]

    def test_list_users_returns_all_records(self) -> None:
        self.repo.create("alice", "EMPLOYEE", "Alice", "", "", _ph("pw1"))  # type: ignore[reportArgumentType]
        self.repo.create("bob", "MANAGER", "Bob", "", "", _ph("pw2"))  # type: ignore[reportArgumentType]

        users = self.repo.list_users()

        self.assertCountEqual([user.username for user in users], ["alice", "bob"])

    def test_save_is_noop(self) -> None:
        self.assertIsNone(self.repo.save())
