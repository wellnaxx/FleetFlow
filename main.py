from src.core.user_store import UserStore
from src.core.auth_service import AuthService
from src.core.application_data import ApplicationData
from src.core.command_factory import CommandFactory
from src.models.auth import Role
from src.core.engine import Engine

def bootstrap_admin(auth: AuthService, store: UserStore):
    if not store.get("admin"):
        auth.register_user(username="admin", role=Role.MANAGER, name="Admin", email="", phone_number="", password="ChangeMe123!")

def main():
    store = UserStore("users.json")
    auth = AuthService(store)
    bootstrap_admin(auth, store)

    app_data = ApplicationData(current_user=None)
    try:
        import os, json
        if os.path.exists(app_data.AUTOSAVE_PATH):
            with open(app_data.AUTOSAVE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            app_data._apply_state(data)
            print(f"(Loaded persisted state from {app_data.AUTOSAVE_PATH})")
    except Exception as e:
        print(f"(Warning: failed to auto-load state: {e})")
    cmd_factory = CommandFactory(app_data, auth)
    Engine(cmd_factory, app_data, auth).start()

if __name__ == "__main__":
    main()
