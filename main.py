import os

from src.adapters.driven.persistence.json.user_store import UserStore
from src.adapters.driving.cli.command_factory import CommandFactory
from src.adapters.driving.cli.engine import Engine
from src.application.config.state_persistence import DEFAULT_WORLD_STATE_PATH
from src.application.services.auth_service import AuthService
from src.composition.container import Container
from src.domain.enums.auth import Role


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

    container = Container(auth)

    try:
        if os.path.exists(DEFAULT_WORLD_STATE_PATH):
            container.load_world_state_use_case.execute(DEFAULT_WORLD_STATE_PATH)
    except Exception:
        pass

    cmd_factory = CommandFactory(auth, container.authz, container)
    Engine(
        cmd_factory,
        auth,
        container.authz,
        container.save_world_state_use_case,
        container.default_world_state_path,
        container.advance_world_state_use_case,
    ).start()


if __name__ == "__main__":
    main()
