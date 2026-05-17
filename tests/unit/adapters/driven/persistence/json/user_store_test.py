import unittest
from json import JSONDecodeError
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, mock_open, patch

from src.adapters.driven.persistence.json.user_store import JSONUserStore
from src.adapters.driven.security.password_hasher import PasswordHash
from src.application.models.user_record import UserRecord
from src.domain.enums.auth import Role

PERSISTED_PASSWORD = PasswordHash(
    algo="sha256",
    iterations=200000,
    salt_b64="U0FMVFNBTFRTQUxUU0FMVA==",
    hash_b64="SEFTSEhBU0hIQVNI",
).serialize()


def _ph(s: str = "hash") -> SimpleNamespace:
    # lightweight PasswordHash with stable serialize()
    return SimpleNamespace(serialize=lambda: f"SER({s})")


class JSONUserStore_Load_Save_Should(unittest.TestCase):
    @patch(
        "src.adapters.driven.persistence.json.user_store.resolve_data_path", return_value="C:/fake/users.json"
    )
    @patch("src.adapters.driven.persistence.json.user_store.os.path.exists", return_value=True)
    @patch("src.adapters.driven.persistence.json.user_store.open", new_callable=mock_open)
    @patch("src.adapters.driven.persistence.json.user_store.json.load")
    def test_init_loads_existing_file(
        self, jload: MagicMock, mopen: MagicMock, exists: MagicMock, resolve: MagicMock
    ) -> None:
        jload.return_value = {
            "_next_id": 7,
            "users": [
                {
                    "user_id": 4,
                    "username": "bob",
                    "role": "MANAGER",
                    "name": "Bob",
                    "email": "bob@example.com",
                    "phone_number": "0400123456",
                    "password": PERSISTED_PASSWORD,
                },
                {
                    "user_id": 1,
                    "username": "alice",
                    "role": "EMPLOYEE",
                    "name": "Alice",
                    "email": "alice@example.com",
                    "phone_number": "0412345678",
                    "password": PERSISTED_PASSWORD,
                },
            ],
        }

        store = JSONUserStore()  # triggers _load
        # case-insensitive get
        self.assertIsInstance(store.get("ALICE"), UserRecord)
        self.assertEqual(store.get("bob").user_id, 4)  # type: ignore[reportOptionalMemberAccess]
        self.assertEqual(store.get("bob").token_version, 1)  # type: ignore[reportOptionalMemberAccess]
        # next id was restored
        self.assertEqual(store._next_id, 7)  # type: ignore[reportPrivateUsage]

    @patch(
        "src.adapters.driven.persistence.json.user_store.resolve_data_path", return_value="C:/fake/users.json"
    )
    @patch("src.adapters.driven.persistence.json.user_store.os.path.exists", return_value=True)
    @patch("src.adapters.driven.persistence.json.user_store.open", new_callable=mock_open)
    @patch("src.adapters.driven.persistence.json.user_store.json.load")
    def test_init_loads_persisted_token_version(
        self, jload: MagicMock, mopen: MagicMock, exists: MagicMock, resolve: MagicMock
    ) -> None:
        jload.return_value = {
            "_next_id": 2,
            "users": [
                {
                    "user_id": 1,
                    "username": "alice",
                    "role": "EMPLOYEE",
                    "name": "Alice",
                    "email": "",
                    "phone_number": "",
                    "password": PERSISTED_PASSWORD,
                    "token_version": 4,
                },
            ],
        }

        store = JSONUserStore()

        self.assertEqual(store.get("alice").token_version, 4)  # type: ignore[reportOptionalMemberAccess]

    @patch(
        "src.adapters.driven.persistence.json.user_store.resolve_data_path", return_value="C:/fake/users.json"
    )
    @patch("src.adapters.driven.persistence.json.user_store.os.path.exists", return_value=True)
    @patch("src.adapters.driven.persistence.json.user_store.open", new_callable=mock_open)
    @patch("src.adapters.driven.persistence.json.user_store.json.load")
    def test_init_rejects_invalid_token_version(
        self, jload: MagicMock, mopen: MagicMock, exists: MagicMock, resolve: MagicMock
    ) -> None:
        jload.return_value = {
            "_next_id": 2,
            "users": [
                {
                    "user_id": 1,
                    "username": "alice",
                    "role": "EMPLOYEE",
                    "name": "Alice",
                    "email": "",
                    "phone_number": "",
                    "password": PERSISTED_PASSWORD,
                    "token_version": 0,
                },
            ],
        }

        with self.assertRaises(ValueError) as ctx:
            JSONUserStore()

        self.assertIn("Malformed user store JSON", str(ctx.exception))

    @patch(
        "src.adapters.driven.persistence.json.user_store.resolve_data_path", return_value="C:/fake/users.json"
    )
    @patch("src.adapters.driven.persistence.json.user_store.os.path.exists", return_value=True)
    @patch("src.adapters.driven.persistence.json.user_store.open", new_callable=mock_open)
    @patch(
        "src.adapters.driven.persistence.json.user_store.json.load",
        side_effect=JSONDecodeError("bad json", "{", 0),
    )
    def test_init_with_bad_json_raises_value_error(
        self,
        jload: MagicMock,
        mopen: MagicMock,
        exists: MagicMock,
        resolve: MagicMock,
    ) -> None:
        with self.assertRaises(ValueError) as ctx:
            JSONUserStore()

        self.assertIn("Malformed user store JSON", str(ctx.exception))

    @patch(
        "src.adapters.driven.persistence.json.user_store.resolve_data_path", return_value="C:/fake/users.json"
    )
    @patch("src.adapters.driven.persistence.json.user_store.os.path.exists", return_value=True)
    @patch("src.adapters.driven.persistence.json.user_store.open", new_callable=mock_open)
    @patch("src.adapters.driven.persistence.json.user_store.json.load", return_value=["not", "a", "dict"])
    def test_init_with_malformed_payload_raises_value_error(
        self, jload: MagicMock, mopen: MagicMock, exists: MagicMock, resolve: MagicMock
    ) -> None:
        with self.assertRaises(ValueError) as ctx:
            JSONUserStore()

        self.assertIn("Malformed user store JSON", str(ctx.exception))

    @patch(
        "src.adapters.driven.persistence.json.user_store.resolve_data_path", return_value="C:/fake/users.json"
    )
    @patch("src.adapters.driven.persistence.json.user_store.os.path.exists", return_value=True)
    @patch("src.adapters.driven.persistence.json.user_store.open", new_callable=mock_open)
    @patch("src.adapters.driven.persistence.json.user_store.json.load", return_value={"_next_id": 2})
    def test_init_with_missing_users_key_raises_value_error(
        self, jload: MagicMock, mopen: MagicMock, exists: MagicMock, resolve: MagicMock
    ) -> None:
        with self.assertRaises(ValueError) as ctx:
            JSONUserStore()

        self.assertIn("Malformed user store JSON", str(ctx.exception))

    @patch(
        "src.adapters.driven.persistence.json.user_store.resolve_data_path", return_value="C:/fake/users.json"
    )
    @patch("src.adapters.driven.persistence.json.user_store.os.path.exists", return_value=True)
    @patch("src.adapters.driven.persistence.json.user_store.open", new_callable=mock_open)
    @patch(
        "src.adapters.driven.persistence.json.user_store.json.load",
        return_value={
            "_next_id": True,
            "users": [],
        },
    )
    def test_init_with_bool_next_id_raises_value_error(
        self, jload: MagicMock, mopen: MagicMock, exists: MagicMock, resolve: MagicMock
    ) -> None:
        with self.assertRaises(ValueError) as ctx:
            JSONUserStore()

        self.assertIn("Malformed user store JSON", str(ctx.exception))

    @patch(
        "src.adapters.driven.persistence.json.user_store.resolve_data_path", return_value="C:/fake/users.json"
    )
    @patch("src.adapters.driven.persistence.json.user_store.os.path.exists", return_value=True)
    @patch("src.adapters.driven.persistence.json.user_store.open", new_callable=mock_open)
    @patch(
        "src.adapters.driven.persistence.json.user_store.json.load",
        return_value={
            "_next_id": 3,
            "users": [
                {
                    "user_id": 1,
                    "username": "Alice",
                    "role": "EMPLOYEE",
                    "name": "Alice",
                    "email": "alice@example.com",
                    "phone_number": "0412345678",
                    "password": PERSISTED_PASSWORD,
                },
                {
                    "user_id": 2,
                    "username": "alice",
                    "role": "MANAGER",
                    "name": "Alice 2",
                    "email": "bob@example.com",
                    "phone_number": "0400123456",
                    "password": PERSISTED_PASSWORD,
                },
            ],
        },
    )
    def test_init_with_duplicate_usernames_raises_value_error(
        self, jload: MagicMock, mopen: MagicMock, exists: MagicMock, resolve: MagicMock
    ) -> None:
        with self.assertRaises(ValueError) as ctx:
            JSONUserStore()

        self.assertIn("Malformed user store JSON", str(ctx.exception))

    @patch(
        "src.adapters.driven.persistence.json.user_store.resolve_data_path", return_value="C:/fake/users.json"
    )
    @patch("src.adapters.driven.persistence.json.user_store.os.path.exists", return_value=True)
    @patch("src.adapters.driven.persistence.json.user_store.open", new_callable=mock_open)
    @patch(
        "src.adapters.driven.persistence.json.user_store.json.load",
        return_value={
            "_next_id": 9,
            "users": [
                {
                    "user_id": 1,
                    "username": "alice",
                    "role": "EMPLOYEE",
                    "name": "Alice",
                    "email": "alice@example.com",
                    "phone_number": "0412345678",
                    "password": PERSISTED_PASSWORD,
                },
                {
                    "user_id": 1,
                    "username": "bob",
                    "role": "MANAGER",
                    "name": "Bob",
                    "email": "bob@example.com",
                    "phone_number": "0400123456",
                    "password": PERSISTED_PASSWORD,
                },
            ],
        },
    )
    def test_init_rejects_duplicate_user_ids(
        self, jload: MagicMock, mopen: MagicMock, exists: MagicMock, resolve: MagicMock
    ) -> None:
        with self.assertRaises(ValueError) as ctx:
            JSONUserStore()

        self.assertIn("Malformed user store JSON", str(ctx.exception))

    @patch(
        "src.adapters.driven.persistence.json.user_store.resolve_data_path", return_value="C:/fake/users.json"
    )
    @patch("src.adapters.driven.persistence.json.user_store.os.path.exists", return_value=True)
    @patch("src.adapters.driven.persistence.json.user_store.open", new_callable=mock_open)
    @patch(
        "src.adapters.driven.persistence.json.user_store.json.load",
        return_value={
            "_next_id": 2,
            "users": [
                {
                    "user_id": 1,
                    "username": "alice",
                    "role": "OWNER",
                    "name": "Alice",
                    "email": "alice@example.com",
                    "phone_number": "0412345678",
                    "password": PERSISTED_PASSWORD,
                },
            ],
        },
    )
    def test_init_rejects_invalid_persisted_role(
        self, jload: MagicMock, mopen: MagicMock, exists: MagicMock, resolve: MagicMock
    ) -> None:
        with self.assertRaises(ValueError) as ctx:
            JSONUserStore()

        self.assertIn("Malformed user store JSON", str(ctx.exception))

    @patch(
        "src.adapters.driven.persistence.json.user_store.resolve_data_path", return_value="C:/fake/users.json"
    )
    @patch("src.adapters.driven.persistence.json.user_store.os.path.exists", return_value=True)
    @patch("src.adapters.driven.persistence.json.user_store.open", new_callable=mock_open)
    @patch(
        "src.adapters.driven.persistence.json.user_store.json.load",
        return_value={
            "_next_id": 2,
            "users": [
                {
                    "user_id": 1,
                    "username": "alice",
                    "role": "EMPLOYEE",
                    "name": "Alice",
                    "email": "alice@example.com",
                    "phone_number": "0412345678",
                    "password": "not-a-password-hash",
                },
            ],
        },
    )
    def test_init_rejects_invalid_persisted_password_hash(
        self, jload: MagicMock, mopen: MagicMock, exists: MagicMock, resolve: MagicMock
    ) -> None:
        with self.assertRaises(ValueError) as ctx:
            JSONUserStore()

        self.assertIn("Malformed user store JSON", str(ctx.exception))

    @patch(
        "src.adapters.driven.persistence.json.user_store.resolve_data_path", return_value="C:/fake/users.json"
    )
    @patch("src.adapters.driven.persistence.json.user_store.os.path.exists", return_value=True)
    @patch("src.adapters.driven.persistence.json.user_store.open", new_callable=mock_open)
    @patch(
        "src.adapters.driven.persistence.json.user_store.json.load",
        return_value={
            "_next_id": 2,
            "users": [
                {
                    "user_id": 1,
                    "username": "alice",
                    "role": "EMPLOYEE",
                    "name": "Alice",
                    "email": "not-an-email",
                    "phone_number": "0412345678",
                    "password": PERSISTED_PASSWORD,
                },
            ],
        },
    )
    def test_init_rejects_invalid_persisted_contact_info(
        self, jload: MagicMock, mopen: MagicMock, exists: MagicMock, resolve: MagicMock
    ) -> None:
        with self.assertRaises(ValueError) as ctx:
            JSONUserStore()

        self.assertIn("Malformed user store JSON", str(ctx.exception))

    @patch(
        "src.adapters.driven.persistence.json.user_store.resolve_data_path", return_value="C:/fake/users.json"
    )
    @patch("src.adapters.driven.persistence.json.user_store.os.path.exists", return_value=True)
    @patch("src.adapters.driven.persistence.json.user_store.open", new_callable=mock_open)
    @patch(
        "src.adapters.driven.persistence.json.user_store.json.load",
        return_value={
            "_next_id": 2,
            "users": [
                {
                    "user_id": 1,
                    "username": "alice",
                    "role": "EMPLOYEE",
                    "name": "Alice",
                    "email": "alice@example.com",
                    "phone_number": "0412345678",
                    "password": PERSISTED_PASSWORD,
                },
                {
                    "user_id": 4,
                    "username": "bob",
                    "role": "MANAGER",
                    "name": "Bob",
                    "email": "bob@example.com",
                    "phone_number": "0400123456",
                    "password": PERSISTED_PASSWORD,
                },
            ],
        },
    )
    def test_init_corrects_stale_next_id_to_follow_max_loaded_user_id(
        self, jload: MagicMock, mopen: MagicMock, exists: MagicMock, resolve: MagicMock
    ) -> None:
        store = JSONUserStore()

        self.assertEqual(store._next_id, 5)  # type: ignore[reportPrivateUsage]

    @patch(
        "src.adapters.driven.persistence.json.user_store.resolve_data_path", return_value="C:/fake/users.json"
    )
    @patch("src.adapters.driven.persistence.json.user_store.os.path.exists", return_value=True)
    @patch("src.adapters.driven.persistence.json.user_store.open", new_callable=mock_open)
    @patch(
        "src.adapters.driven.persistence.json.user_store.json.load",
        return_value={
            "_next_id": 3,
            "users": [
                {
                    "user_id": 9,
                    "username": "charlie",
                    "role": "EMPLOYEE",
                    "name": "Charlie",
                    "email": "charlie@example.com",
                    "phone_number": "0499123456",
                    "password": PERSISTED_PASSWORD,
                },
                {
                    "user_id": 2,
                    "username": "alice",
                    "role": "EMPLOYEE",
                    "name": "Alice",
                    "email": "alice@example.com",
                    "phone_number": "0412345678",
                    "password": PERSISTED_PASSWORD,
                },
                {
                    "user_id": 5,
                    "username": "bob",
                    "role": "MANAGER",
                    "name": "Bob",
                    "email": "bob@example.com",
                    "phone_number": "0400123456",
                    "password": PERSISTED_PASSWORD,
                },
            ],
        },
    )
    def test_init_accepts_valid_unordered_users_and_corrects_next_id(
        self, jload: MagicMock, mopen: MagicMock, exists: MagicMock, resolve: MagicMock
    ) -> None:
        store = JSONUserStore()

        self.assertEqual(store._next_id, 10)  # type: ignore[reportPrivateUsage]
        self.assertEqual(store.get("alice").user_id, 2)  # type: ignore[reportOptionalMemberAccess]
        self.assertEqual(store.get("BOB").user_id, 5)  # type: ignore[reportOptionalMemberAccess]
        self.assertEqual(store.get("charlie").user_id, 9)  # type: ignore[reportOptionalMemberAccess]

    @patch.object(JSONUserStore, "_atomic_write", return_value="C:/fake/users.json")
    @patch(
        "src.adapters.driven.persistence.json.user_store.resolve_data_path", return_value="C:/fake/users.json"
    )
    @patch("src.adapters.driven.persistence.json.user_store.os.path.exists", return_value=False)
    def test_save_writes_sorted_payload(
        self, exists: MagicMock, resolve: MagicMock, atomic_write: MagicMock
    ) -> None:
        store = JSONUserStore()
        # seed users out of order to check sorting by user_id
        u1 = UserRecord(3, "c", "EMPLOYEE", "C", "c@x", "03", "p3")
        u2 = UserRecord(1, "a", "EMPLOYEE", "A", "a@x", "01", "p1")
        u3 = UserRecord(2, "b", "MANAGER", "B", "b@x", "02", "p2")
        store._by_username = {"a": u2, "b": u3, "c": u1}  # type: ignore[reportAttributeAccessIssue]
        store._next_id = 4  # type: ignore[reportAttributeAccessIssue]

        path = store.save()
        self.assertEqual(path, "C:/fake/users.json")
        # capture payload passed to _atomic_write
        (payload,), _ = atomic_write.call_args  # type: ignore[reportOptionalIterable]
        self.assertEqual(payload["_next_id"], 4)
        ids = [u["user_id"] for u in payload["users"]]
        self.assertEqual(ids, [1, 2, 3])  # sorted


class JSONUserStore_Create_Get_Update_Should(unittest.TestCase):
    @patch(
        "src.adapters.driven.persistence.json.user_store.resolve_data_path", return_value="C:/fake/users.json"
    )
    @patch("src.adapters.driven.persistence.json.user_store.os.path.exists", return_value=False)
    def test_create_normalizes_and_persists_and_get_is_case_insensitive(
        self, exists: MagicMock, resolve: MagicMock
    ) -> None:
        # Patch ContactInfo so we control cleaning behavior
        with (
            patch("src.adapters.driven.persistence.json.user_store.ContactInfo") as CI,
            patch.object(JSONUserStore, "_atomic_write", return_value="C:/fake/users.json") as aw,
        ):
            CI.side_effect = lambda name, email, phone_number: SimpleNamespace(  # type: ignore[reportUnknownLambdaType]
                name=name.strip(),  # type: ignore[reportUnknownMemberType]
                email=(email or "").strip().lower(),  # type: ignore[reportUnknownMemberType]
                phone_number=(phone_number or "").strip(),  # type: ignore[reportUnknownMemberType]
            )

            store = JSONUserStore()

            rec = store.create(
                username="  Alice  ",
                role="employee",  # string role should become upper
                name="  Alice Liddell ",
                email="  ALICE@EX.COM ",
                phone_number=" 0412 345 ",
                password_hash=_ph("pw1"),  # type: ignore[reportArgumentType]
            )

            self.assertEqual(rec.user_id, 1)
            self.assertEqual(rec.username, "Alice")  # stored as given key (stripped)
            self.assertEqual(rec.role, "EMPLOYEE")  # normalized role
            self.assertEqual(rec.name, "Alice Liddell")
            self.assertEqual(rec.email, "alice@ex.com")
            self.assertEqual(rec.phone_number, "0412 345")
            self.assertEqual(rec.password, "SER(pw1)")
            self.assertEqual(rec.token_version, 1)

            # case-insensitive get
            self.assertIs(store.get("alice"), rec)
            self.assertIs(store.get("ALICE"), rec)

            # ensure it persisted (save called internally via create)
            aw.assert_called()

    @patch(
        "src.adapters.driven.persistence.json.user_store.resolve_data_path", return_value="C:/fake/users.json"
    )
    @patch("src.adapters.driven.persistence.json.user_store.os.path.exists", return_value=False)
    def test_create_accepts_role_enum(self, exists: MagicMock, resolve: MagicMock) -> None:
        with (
            patch("src.adapters.driven.persistence.json.user_store.ContactInfo") as CI,
            patch.object(JSONUserStore, "_atomic_write", return_value="C:/fake/users.json"),
        ):
            CI.side_effect = lambda name, email, phone_number: SimpleNamespace(  # type: ignore[reportUnknownLambdaType]
                name=name, email=email, phone_number=phone_number
            )
            store = JSONUserStore()
            rec = store.create("bob", Role.MANAGER, "Bob", "", "", _ph("pw2"))  # type: ignore[reportArgumentType]
            self.assertEqual(rec.role, "MANAGER")

    @patch(
        "src.adapters.driven.persistence.json.user_store.resolve_data_path", return_value="C:/fake/users.json"
    )
    @patch("src.adapters.driven.persistence.json.user_store.os.path.exists", return_value=False)
    def test_create_validations_and_password_type(self, exists: MagicMock, resolve: MagicMock) -> None:
        with patch.object(JSONUserStore, "_atomic_write", return_value="C:/fake/users.json"):
            store = JSONUserStore()
            with self.assertRaises(ValueError):
                store.create("", "EMPLOYEE", "N", "", "", _ph("pw"))  # type: ignore[reportArgumentType]
            store.create("user", "EMPLOYEE", "Name", "", "", _ph("pw"))  # type: ignore[reportArgumentType]
            with self.assertRaises(ValueError):
                store.create("user", "EMPLOYEE", "Name", "", "", _ph("pw"))  # type: ignore[reportArgumentType]  # duplicate username
            with self.assertRaises(ValueError):
                store.create("badrole", "garbage", "Name", "", "", _ph("pw"))  # type: ignore[reportArgumentType]
            with self.assertRaises(TypeError):
                store.create("v", "EMPLOYEE", "Name", "", "", object())  # type: ignore[reportArgumentType]  # password_hash wrong type

    @patch(
        "src.adapters.driven.persistence.json.user_store.resolve_data_path", return_value="C:/fake/users.json"
    )
    @patch("src.adapters.driven.persistence.json.user_store.os.path.exists", return_value=False)
    def test_update_password_happy_and_missing(self, exists: MagicMock, resolve: MagicMock) -> None:
        with patch.object(JSONUserStore, "_atomic_write", return_value="C:/fake/users.json"):
            store = JSONUserStore()
            store.create("anna", "EMPLOYEE", "Anna", "", "", _ph("old"))  # type: ignore[reportArgumentType]
            rec = store.get("Anna")
            self.assertEqual(rec.password, "SER(old)")  # type: ignore[reportOptionalMemberAccess]

            store.update_password("anna", _ph("new"))  # type: ignore[reportArgumentType]
            self.assertEqual(store.get("ANNA").password, "SER(new)")  # type: ignore[reportOptionalMemberAccess]

            with self.assertRaises(ValueError):
                store.update_password("ghost", _ph("x"))  # type: ignore[reportArgumentType]

    @patch(
        "src.adapters.driven.persistence.json.user_store.resolve_data_path", return_value="C:/fake/users.json"
    )
    @patch("src.adapters.driven.persistence.json.user_store.os.path.exists", return_value=False)
    def test_list_users_returns_all(self, exists: MagicMock, resolve: MagicMock) -> None:
        store = JSONUserStore()
        store._by_username = {  # type: ignore[reportAttributeAccessIssue]
            "a": UserRecord(1, "a", "E", "A", "", "", "p"),
            "b": UserRecord(2, "b", "E", "B", "", "", "p"),
        }
        users = store.list_users()
        self.assertCountEqual([u.username for u in users], ["a", "b"])

    @patch(
        "src.adapters.driven.persistence.json.user_store.resolve_data_path", return_value="C:/fake/users.json"
    )
    @patch("src.adapters.driven.persistence.json.user_store.os.path.exists", return_value=False)
    def test_get_is_whitespace_and_case_insensitive(self, exists: MagicMock, resolve: MagicMock) -> None:
        with patch.object(JSONUserStore, "_atomic_write", return_value="C:/fake/users.json"):
            store = JSONUserStore()
            rec = store.create("Alice", "EMPLOYEE", "Alice", "", "", _ph("pw1"))  # type: ignore[reportArgumentType]

            self.assertIs(store.get("alice"), rec)
            self.assertIs(store.get(" ALICE "), rec)
            self.assertIs(store.get("\tAlice\n"), rec)

    @patch(
        "src.adapters.driven.persistence.json.user_store.resolve_data_path", return_value="C:/fake/users.json"
    )
    @patch("src.adapters.driven.persistence.json.user_store.os.path.exists", return_value=False)
    def test_create_rejects_duplicate_username_with_whitespace_and_case_variants(
        self, exists: MagicMock, resolve: MagicMock
    ) -> None:
        with patch.object(JSONUserStore, "_atomic_write", return_value="C:/fake/users.json"):
            store = JSONUserStore()
            store.create("Alice", "EMPLOYEE", "Alice", "", "", _ph("pw1"))  # type: ignore[reportArgumentType]

            with self.assertRaises(ValueError) as ctx:
                store.create("  alice  ", "EMPLOYEE", "Alice 2", "", "", _ph("pw2"))  # type: ignore[reportArgumentType]

            self.assertIn("Username already exists.", str(ctx.exception))

    @patch(
        "src.adapters.driven.persistence.json.user_store.resolve_data_path", return_value="C:/fake/users.json"
    )
    @patch("src.adapters.driven.persistence.json.user_store.os.path.exists", return_value=False)
    def test_update_password_accepts_whitespace_and_case_insensitive_username(
        self, exists: MagicMock, resolve: MagicMock
    ) -> None:
        with patch.object(JSONUserStore, "_atomic_write", return_value="C:/fake/users.json"):
            store = JSONUserStore()
            store.create("Alice", "EMPLOYEE", "Alice", "", "", _ph("old"))  # type: ignore[reportArgumentType]

            store.update_password("  ALICE  ", _ph("new"))  # type: ignore[reportArgumentType]

            self.assertEqual(store.get("alice").password, "SER(new)")  # type: ignore[reportOptionalMemberAccess]


class JSONUserStore_AtomicWrite_Should(unittest.TestCase):
    @patch("src.adapters.driven.persistence.json.user_store.ensure_data_dir")
    @patch(
        "src.adapters.driven.persistence.json.user_store.resolve_data_path", return_value="C:/fake/users.json"
    )
    @patch("src.adapters.driven.persistence.json.user_store.os.path.dirname", return_value="C:/fake")
    @patch("src.adapters.driven.persistence.json.user_store.os.makedirs")
    @patch(
        "src.adapters.driven.persistence.json.user_store.tempfile.mkstemp",
        return_value=(123, "C:/fake/.users.tmp.json"),
    )
    @patch("src.adapters.driven.persistence.json.user_store.os.fdopen")
    @patch("src.adapters.driven.persistence.json.user_store.os.replace")
    @patch(
        "src.adapters.driven.persistence.json.user_store.os.path.exists",
        side_effect=[False, False],
    )  # 1) _load -> False, 2) cleanup tmp -> False
    def test_atomic_write_writes_and_replaces(
        self,
        exists: MagicMock,
        replace: MagicMock,
        fdopen: MagicMock,
        mkstemp: MagicMock,
        makedirs: MagicMock,
        dirname: MagicMock,
        resolve: MagicMock,
        ensure: MagicMock,
    ) -> None:
        store = JSONUserStore()  # _load is skipped because exists() -> False
        payload: dict[str, Any] = {"_next_id": 1, "users": []}

        cm = MagicMock()
        fdopen.return_value.__enter__.return_value = cm

        out_path = store._atomic_write(payload)  # type: ignore[reportPrivateUsage]
        self.assertEqual(out_path, "C:/fake/users.json")
        makedirs.assert_called()  # directory ensured
        replace.assert_called_once_with("C:/fake/.users.tmp.json", "C:/fake/users.json")
        cm.write.assert_called()  # JSON was written

    @patch("src.adapters.driven.persistence.json.user_store.logger")
    @patch("src.adapters.driven.persistence.json.user_store.ensure_data_dir")
    @patch(
        "src.adapters.driven.persistence.json.user_store.resolve_data_path", return_value="C:/fake/users.json"
    )
    @patch("src.adapters.driven.persistence.json.user_store.os.path.dirname", return_value="C:/fake")
    @patch("src.adapters.driven.persistence.json.user_store.os.makedirs")
    @patch(
        "src.adapters.driven.persistence.json.user_store.tempfile.mkstemp",
        return_value=(123, "C:/fake/.users.tmp.json"),
    )
    @patch("src.adapters.driven.persistence.json.user_store.os.fdopen")
    @patch("src.adapters.driven.persistence.json.user_store.os.replace")
    @patch(
        "src.adapters.driven.persistence.json.user_store.os.remove",
        side_effect=OSError("locked"),
    )
    @patch(
        "src.adapters.driven.persistence.json.user_store.os.path.exists",
        side_effect=[False, True],
    )  # 1) _load -> False, 2) cleanup tmp -> True
    def test_atomic_write_logs_cleanup_failure(
        self,
        exists: MagicMock,
        remove: MagicMock,
        replace: MagicMock,
        fdopen: MagicMock,
        mkstemp: MagicMock,
        makedirs: MagicMock,
        dirname: MagicMock,
        resolve: MagicMock,
        ensure: MagicMock,
        logger: MagicMock,
    ) -> None:
        store = JSONUserStore()
        payload: dict[str, Any] = {"_next_id": 1, "users": []}

        cm = MagicMock()
        fdopen.return_value.__enter__.return_value = cm

        out_path = store._atomic_write(payload)  # type: ignore[reportPrivateUsage]

        self.assertEqual(out_path, "C:/fake/users.json")
        replace.assert_called_once_with("C:/fake/.users.tmp.json", "C:/fake/users.json")
        remove.assert_called_once_with("C:/fake/.users.tmp.json")
        logger.warning.assert_called_once_with(
            "Failed to remove temporary user store file %r: %s",
            "C:/fake/.users.tmp.json",
            remove.side_effect,
        )
