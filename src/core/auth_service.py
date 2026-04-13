from src.core.crypto import PasswordHash, hash_password, verify_password
from src.core.user_store import UserRecord, UserStore
from src.models.auth import Role
from src.models.contact_info import ContactInfo
from src.models.users.employee import Employee
from src.models.users.manager import Manager
from src.models.users.user import User


class AuthService:
    def __init__(self, user_store: UserStore) -> None:
        self._store = user_store
        self._current_user: User | None = None
        self.last_username: str | None = None

    @property
    def current_user(self) -> User | None:
        return self._current_user

    def register_user(
        self, username: str, role: Role, name: str, email: str, phone_number: str, password: str
    ) -> UserRecord:
        # Only managers should be allowed to call this — enforce via RBAC higher up.
        ci = ContactInfo(name=name, email=email or "", phone_number=phone_number)
        clean_name = ci.name
        clean_email = ci.email
        clean_phone = ci.phone_number
        ph = hash_password(password)
        role_value: str = role.value
        return self._store.create(
            username=username,
            role=role_value,
            name=clean_name,
            email=clean_email,
            phone_number=clean_phone,
            password_hash=ph,
        )

    def _set_password(self, rec: UserRecord, new_password: str) -> None:
        if len(new_password) < 8:
            raise ValueError("Password must be at least 8 characters.")
        rec.password = hash_password(new_password).serialize()
        self._store.save()

    def login(self, username: str, password: str) -> User:
        rec = self._store.get(username)
        if not rec:
            raise ValueError("Invalid username or password.")
        ok = verify_password(password, PasswordHash.parse(rec.password))
        if not ok:
            raise ValueError("Invalid username or password.")

        contact = ContactInfo(name=rec.name, email=rec.email, phone_number=rec.phone_number)
        if rec.role == Role.MANAGER.value:
            self._current_user = Manager(contact.name, contact.email, contact.phone_number)
        else:
            self._current_user = Employee(contact.name, contact.email, contact.phone_number)
        self.last_username = rec.username
        return self._current_user

    def logout(self) -> None:
        self._current_user = None
        self.last_username = None

    def change_password(self, username: str, old_password: str, new_password: str) -> None:
        rec = self._store.get(username)
        if not rec:
            raise ValueError("User not found.")
        if not verify_password(old_password, PasswordHash.parse(rec.password)):
            raise ValueError("Old password incorrect.")
        if verify_password(new_password, PasswordHash.parse(rec.password)):
            raise ValueError("New password must be different from the old one.")
        self._set_password(rec, new_password)

    def reset_password(self, username: str, new_password: str) -> None:
        rec = self._store.get(username)
        if not rec:
            raise ValueError("User not found.")
        self._set_password(rec, new_password)
