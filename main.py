import getpass
import logging
import os
import sys
from datetime import datetime

from src.adapters.driven.persistence.json.user_store import JSONUserStore
from src.adapters.driving.cli.command_factory import CommandFactory
from src.adapters.driving.cli.engine import Engine
from src.application.exceptions.world_state_errors import WorldStateCorruptionError, WorldStateFileNotFoundError
from src.application.services.auth_service import AuthService
from src.composition.container import Container, build_container
from src.domain.enums.auth import Role
from src.ports.output.user_repository import UserRepositoryPort

logger = logging.getLogger(__name__)

DEFAULT_WORLD_STATE_PATH = "state.json"


def bootstrap_admin(auth: AuthService, store: UserRepositoryPort) -> None:
    if store.get("admin"):
        return

    if not sys.stdin.isatty():
        raise RuntimeError(
            "No admin user exists. Run the application interactively once to create the initial admin password."
        )

    password = getpass.getpass("Create initial manager password: ")
    confirmation = getpass.getpass("Confirm initial manager password: ")
    if password != confirmation:
        raise ValueError("Initial manager passwords do not match.")

    auth.register_user(
        username="admin",
        role=Role.MANAGER,
        name="Admin",
        email="",
        phone_number="",
        password=password,
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
    if not container.autosave_enabled:
        return

    default_world_state_path = container.default_world_state_path

    if not os.path.exists(default_world_state_path):
        return

    try:
        container.load_world_state_use_case.execute(default_world_state_path)
    except WorldStateFileNotFoundError:
        return
    except WorldStateCorruptionError:
        logger.exception(
            "Failed to load default world state from %r.",
            default_world_state_path,
        )

        quarantined_path = _quarantine_corrupt_world_state(default_world_state_path)

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
    store = JSONUserStore("users.json")
    auth = AuthService(store)
    bootstrap_admin(auth, store)

    container = build_container(auth)
    _load_default_world_state(container)

    cmd_factory = CommandFactory(auth, container.authz, container)
    Engine(
        cmd_factory,
        auth,
        container.authz,
        container.save_world_state_use_case,
        container.default_world_state_path,
        container.advance_world_state_use_case,
        container.autosave_enabled,
    ).start()


if __name__ == "__main__":
    main()
