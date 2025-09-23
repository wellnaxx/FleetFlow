from typing import Optional
from src.core.user_store import UserStore, UserRecord
from src.core.crypto import hash_password, verify_password, PasswordHash
from src.models.users.employee import Employee
from src.models.users.manager import Manager
from src.models.auth import Role
from src.models.contact_info import ContactInfo

class AuthService:
    def __init__(self, user_store: UserStore):
        self._store = user_store
        self._current_user = None  # domain User (Employee/Manager)
        self.last_username = None

    @property
    def current_user(self):
        return self._current_user

    def register_user(self, username: str, role: Role, name: str, email: str, phone_number: str, password: str) -> UserRecord:
        # Only managers should be allowed to call this — enforce via RBAC higher up.
        ph = hash_password(password)
        rec = self._store.create(username=username, role=role.value, name=name, email=email, phone_number=phone_number, password_hash=ph)
        return rec
    
    def _set_password(self, rec, new_password: str):
        if len(new_password) < 8:
            raise ValueError("Password must be at least 8 characters.")
        rec.password = hash_password(new_password).serialize()
        self._store.save()

    def login(self, username: str, password: str):
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

    def logout(self):
        self._current_user = None
        self.last_username = None

    def change_password(self, username, old_password, new_password):
        rec = self._store.get(username)
        if not rec: raise ValueError("User not found.")
        if not verify_password(old_password, PasswordHash.parse(rec.password)):
            raise ValueError("Old password incorrect.")
        if verify_password(new_password, PasswordHash.parse(rec.password)):
            raise ValueError("New password must be different from the old one.")
        self._set_password(rec, new_password)

    def reset_password(self, username, new_password):
        rec = self._store.get(username)
        if not rec: raise ValueError("User not found.")
        self._set_password(rec, new_password)