import unittest
from unittest.mock import patch, MagicMock, mock_open
from types import SimpleNamespace

from src.core.user_store import UserStore, UserRecord
from json import JSONDecodeError


def _ph(s="hash"):
    # lightweight PasswordHash with stable serialize()
    return SimpleNamespace(serialize=lambda: f"SER({s})")


class UserStore_Load_Save_Should(unittest.TestCase):
    @patch("src.core.user_store.resolve_data_path", return_value="C:/fake/users.json")
    @patch("src.core.user_store.os.path.exists", return_value=True)
    @patch("src.core.user_store.open", new_callable=mock_open)
    @patch("src.core.user_store.json.load")
    def test_init_loads_existing_file(self, jload, mopen, exists, resolve):
        jload.return_value = {
            "_next_id": 5,
            "users": [
                {
                    "user_id": 1,
                    "username": "alice",
                    "role": "EMPLOYEE",
                    "name": "Alice",
                    "email": "a@x",
                    "phone_number": "0412",
                    "password": "SER(h1)",
                },
                {
                    "user_id": 4,
                    "username": "bob",
                    "role": "MANAGER",
                    "name": "Bob",
                    "email": "b@x",
                    "phone_number": "0400",
                    "password": "SER(h2)",
                },
            ],
        }

        store = UserStore()  # triggers _load
        # case-insensitive get
        self.assertIsInstance(store.get("ALICE"), UserRecord)
        self.assertEqual(store.get("bob").user_id, 4)
        # next id was restored
        self.assertEqual(store._next_id, 5)

    @patch("src.core.user_store.resolve_data_path", return_value="C:/fake/users.json")
    @patch("src.core.user_store.os.path.exists", return_value=True)
    @patch("src.core.user_store.open", new_callable=mock_open)
    @patch("src.core.user_store.json.load", side_effect=JSONDecodeError("bad json", "{", 0))  # simulate JSONDecodeError-ish
    def test_init_with_bad_json_fails_open_but_results_in_empty_store(self, jload, mopen, exists, resolve):
        store = UserStore()
        self.assertIsNone(store.get("any"))
        self.assertEqual(store._next_id, 1)

    @patch.object(UserStore, "_atomic_write", return_value="C:/fake/users.json")
    @patch("src.core.user_store.resolve_data_path", return_value="C:/fake/users.json")
    @patch("src.core.user_store.os.path.exists", return_value=False)
    def test_save_writes_sorted_payload(self, exists, resolve, atomic_write):
        store = UserStore()
        # seed users out of order to check sorting by user_id
        u1 = UserRecord(3, "c", "EMPLOYEE", "C", "c@x", "03", "p3")
        u2 = UserRecord(1, "a", "EMPLOYEE", "A", "a@x", "01", "p1")
        u3 = UserRecord(2, "b", "MANAGER",  "B", "b@x", "02", "p2")
        store._by_username = {"a": u2, "b": u3, "c": u1}
        store._next_id = 4

        path = store.save()
        self.assertEqual(path, "C:/fake/users.json")
        # capture payload passed to _atomic_write
        (payload,), _ = atomic_write.call_args
        self.assertEqual(payload["_next_id"], 4)
        ids = [u["user_id"] for u in payload["users"]]
        self.assertEqual(ids, [1, 2, 3])  # sorted


class UserStore_Create_Get_Update_Should(unittest.TestCase):
    @patch("src.core.user_store.resolve_data_path", return_value="C:/fake/users.json")
    @patch("src.core.user_store.os.path.exists", return_value=False)
    def test_create_normalizes_and_persists_and_get_is_case_insensitive(self, exists, resolve):
        # Patch ContactInfo so we control cleaning behavior
        with patch("src.core.user_store.ContactInfo") as CI, \
             patch.object(UserStore, "_atomic_write", return_value="C:/fake/users.json") as aw:
            CI.side_effect = lambda name, email, phone_number: SimpleNamespace(
                name=name.strip(),
                email=(email or "").strip().lower(),
                phone_number=(phone_number or "").strip(),
            )

            store = UserStore()

            rec = store.create(
                username="  Alice  ",
                role="employee",           # string role should become upper
                name="  Alice Liddell ",
                email="  ALICE@EX.COM ",
                phone_number=" 0412 345 ",
                password_hash=_ph("pw1"),
            )

            self.assertEqual(rec.user_id, 1)
            self.assertEqual(rec.username, "Alice")   # stored as given key (stripped)
            self.assertEqual(rec.role, "EMPLOYEE")    # normalized role
            self.assertEqual(rec.name, "Alice Liddell")
            self.assertEqual(rec.email, "alice@ex.com")
            self.assertEqual(rec.phone_number, "0412 345")
            self.assertEqual(rec.password, "SER(pw1)")

            # case-insensitive get
            self.assertIs(store.get("alice"), rec)
            self.assertIs(store.get("ALICE"), rec)

            # ensure it persisted (save called internally via create)
            aw.assert_called()

    @patch("src.core.user_store.resolve_data_path", return_value="C:/fake/users.json")
    @patch("src.core.user_store.os.path.exists", return_value=False)
    def test_create_accepts_role_enums_with_value_attr(self, exists, resolve):
        with patch("src.core.user_store.ContactInfo") as CI, \
             patch.object(UserStore, "_atomic_write", return_value="C:/fake/users.json"):
            CI.side_effect = lambda name, email, phone_number: SimpleNamespace(
                name=name, email=email, phone_number=phone_number
            )
            store = UserStore()
            role_enum_like = SimpleNamespace(value="MANAGER")
            rec = store.create("bob", role_enum_like, "Bob", "", "", _ph("pw2"))
            self.assertEqual(rec.role, "MANAGER")

    @patch("src.core.user_store.resolve_data_path", return_value="C:/fake/users.json")
    @patch("src.core.user_store.os.path.exists", return_value=False)
    def test_create_validations_and_password_type(self, exists, resolve):
        store = UserStore()
        with self.assertRaises(ValueError):
            store.create("", "EMPLOYEE", "N", "", "", _ph("pw"))
        store.create("user", "EMPLOYEE", "Name", "", "", _ph("pw"))
        with self.assertRaises(ValueError):
            store.create("user", "EMPLOYEE", "Name", "", "", _ph("pw"))  # duplicate username
        with self.assertRaises(TypeError):
            store.create("v", "EMPLOYEE", "Name", "", "", object())   # password_hash wrong type

    @patch("src.core.user_store.resolve_data_path", return_value="C:/fake/users.json")
    @patch("src.core.user_store.os.path.exists", return_value=False)
    def test_update_password_happy_and_missing(self, exists, resolve):
        with patch.object(UserStore, "_atomic_write", return_value="C:/fake/users.json"):
            store = UserStore()
            store.create("anna", "EMPLOYEE", "Anna", "", "", _ph("old"))
            rec = store.get("Anna")
            self.assertEqual(rec.password, "SER(old)")

            store.update_password("anna", _ph("new"))
            self.assertEqual(store.get("ANNA").password, "SER(new)")

            with self.assertRaises(ValueError):
                store.update_password("ghost", _ph("x"))

    @patch("src.core.user_store.resolve_data_path", return_value="C:/fake/users.json")
    @patch("src.core.user_store.os.path.exists", return_value=False)
    def test_list_users_returns_all(self, exists, resolve):
        store = UserStore()
        store._by_username = {"a": UserRecord(1, "a", "E", "A", "", "", "p"),
                              "b": UserRecord(2, "b", "E", "B", "", "", "p")}
        users = store.list_users()
        self.assertCountEqual([u.username for u in users], ["a", "b"])


class UserStore_AtomicWrite_Should(unittest.TestCase):
    @patch("src.core.user_store.ensure_data_dir")
    @patch("src.core.user_store.resolve_data_path", return_value="C:/fake/users.json")
    @patch("src.core.user_store.os.path.dirname", return_value="C:/fake")
    @patch("src.core.user_store.os.makedirs")
    @patch("src.core.user_store.tempfile.mkstemp", return_value=(123, "C:/fake/.users.tmp.json"))
    @patch("src.core.user_store.os.fdopen")
    @patch("src.core.user_store.os.replace")
    @patch("src.core.user_store.os.path.exists", side_effect=[False, False])  # 1) _load -> False, 2) cleanup tmp -> False
    def test_atomic_write_writes_and_replaces(self, exists, replace, fdopen, mkstemp, makedirs, dirname, resolve, ensure):
        store = UserStore()  # _load is skipped because exists() -> False
        payload = {"_next_id": 1, "users": []}

        cm = MagicMock()
        fdopen.return_value.__enter__.return_value = cm

        out_path = store._atomic_write(payload)
        self.assertEqual(out_path, "C:/fake/users.json")
        makedirs.assert_called()  # directory ensured
        replace.assert_called_once_with("C:/fake/.users.tmp.json", "C:/fake/users.json")
        cm.write.assert_called()  # JSON was written

