from dataclasses import dataclass, asdict
from typing import Optional, Dict
import json, os, tempfile
from src.core.crypto import PasswordHash
from src.core.paths import resolve_data_path, ensure_data_dir

@dataclass
class UserRecord:
    """Serializable user record stored on disk."""
    user_id: int
    username: str             
    role: str                 
    name: str                  
    email: str
    phone_number: str
    password: str              

class UserStore:
    """Load/save users to data/users.json (or a custom path) with atomic writes."""
    def __init__(self, path: str = "users.json"):
        """
        Args:
            path: Filename or path to the users file. Bare filenames are placed in data/.
        """
        self.path = resolve_data_path(path)
        self._by_username: Dict[str, UserRecord] = {}
        self._next_id = 1
        self._load()

    def _load(self):
        """Load users from disk into memory. Missing file => no users."""
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            return
        self._next_id = int(data.get("_next_id", 1))
        for obj in data.get("users", []):
            rec = UserRecord(**obj)
            self._by_username[rec.username.lower()] = rec

    def _atomic_write(self, data: dict) -> str:
        """Write JSON atomically to self.path. Returns absolute path."""
        ensure_data_dir()
        directory = os.path.dirname(self.path) or "."
        os.makedirs(directory, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".users.", suffix=".json", dir=directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, self.path)
        finally:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:
                pass
        return self.path

    def save(self) -> str:
        """Persist users to disk. Returns absolute path."""
        data = {
            "_next_id": self._next_id,
            "users": [asdict(rec) for rec in sorted(self._by_username.values(), key=lambda r: r.user_id)],
        }
        return self._atomic_write(data)

    def get(self, username: str) -> Optional[UserRecord]:
        """Fetch a user by username (case-insensitive)."""
        key = (username or "").lower()
        return self._by_username.get(key)

    def create(
        self,
        username: str,
        role: str,
        name: str,
        email: str,
        phone_number: str,
        password_hash: PasswordHash,
    ) -> UserRecord:
        """Create and persist a new user. Raises ValueError if username exists."""
        key = (username or "").strip()
        norm = key.lower()
        if not norm:
            raise ValueError("Username is required.")
        if norm in self._by_username:
            raise ValueError("Username already exists.")

        rec = UserRecord(
            user_id=self._next_id,
            username=key,  
            role=role,
            name=name,
            email=email,
            phone_number=phone_number,
            password=password_hash.serialize(),
        )
        self._by_username[norm] = rec
        self._next_id += 1
        self.save()
        return rec


    def update_password(self, username: str, new_hash: PasswordHash) -> None:
        """Update the password for an existing user."""
        rec = self.get(username)
        if not rec:
            raise ValueError("User not found.")
        rec.password = new_hash.serialize()
        self.save()

    def list_users(self) -> list[UserRecord]:
        """Return all users (unordered)."""
        return list(self._by_username.values())