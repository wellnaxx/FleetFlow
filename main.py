from src.core.application_data import ApplicationData
from application.services.auth_service import AuthService
from adapters.driving.cli.command_factory import CommandFactory
from adapters.driving.cli.engine import Engine
from adapters.driven.persistence.json.user_store import UserStore
from domain.enums.auth import Role


def bootstrap_admin(auth: AuthService, store: UserStore) -> None:
    if not store.get("admin"):
        auth.register_user(
            username="admin",
            role=Role.MANAGER,
            name="Admin",
            email="",
            phone_number="",
            password="ChangeMe123!",
        )


def main() -> None:
    store = UserStore("users.json")
    auth = AuthService(store)
    bootstrap_admin(auth, store)

    app_data: ApplicationData = ApplicationData(current_user=None)
    try:
        import json
        import os

        if os.path.exists(app_data.AUTOSAVE_PATH):
            with open(app_data.AUTOSAVE_PATH, encoding="utf-8") as f:
                data = json.load(f)
            app_data._apply_state(data) # pyright: ignore[reportPrivateUsage]
    except Exception:
        pass
    cmd_factory = CommandFactory(app_data, auth)
    Engine(cmd_factory, app_data, auth).start()


if __name__ == "__main__":
    main()
