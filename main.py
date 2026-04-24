import logging
import os
from datetime import datetime

from src.adapters.driven.persistence.json.user_store import UserStore
from src.adapters.driving.cli.command_factory import CommandFactory
from src.adapters.driving.cli.engine import Engine
from src.application.config.state_persistence import DEFAULT_WORLD_STATE_PATH
from src.application.exceptions.world_state_errors import WorldStateCorruptionError, WorldStateFileNotFoundError
from src.application.services.auth_service import AuthService
from src.composition.container import Container
from src.domain.enums.auth import Role

logger = logging.getLogger(__name__)


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


def _quarantine_corrupt_world_state(path: str) -> str | None:
    """Move a corrupt world-state file aside so startup can continue cleanly."""
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    quarantined_path = f"{path}.corrupt.{timestamp}"

    try:
        os.replace(path, quarantined_path)

    except OSError:
        logger.exception("Failed to quarantine corrupt world state file %r.", path)
        return None
    else:
        return quarantined_path


def _load_default_world_state(container: Container) -> None:
    """Best-effort startup restore for the default world-state file.

    Missing file -> ignore.
    Corrupt file -> warn, quarantine, continue with empty world state.
    """
    if not os.path.exists(DEFAULT_WORLD_STATE_PATH):
        return

    try:
        container.load_world_state_use_case.execute(DEFAULT_WORLD_STATE_PATH)
    except WorldStateFileNotFoundError:
        return
    except WorldStateCorruptionError:
        logger.exception(
            "Failed to load default world state from %r.",
            DEFAULT_WORLD_STATE_PATH,
        )

        quarantined_path = _quarantine_corrupt_world_state(DEFAULT_WORLD_STATE_PATH)

        if quarantined_path is not None:
            print(
                "WARNING: Saved world state could not be loaded and was moved aside.\n"
                f"Starting with empty state.\n"
                f"Quarantined file: {quarantined_path}"
            )
        else:
            print(
                "WARNING: Saved world state could not be loaded.\n"
                "Starting with empty state.\n"
                "The corrupt file could not be moved aside automatically."
            )


def main() -> None:
    store = UserStore("users.json")
    auth = AuthService(store)
    bootstrap_admin(auth, store)

    container = Container(auth)
    _load_default_world_state(container)

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
