import getpass
import logging
import os
import sys
from datetime import datetime
from uuid import uuid4

from src.adapters.driven.logging.config import configure_logging
from src.adapters.driving.cli.command_factory import CommandFactory
from src.adapters.driving.cli.engine import Engine
from src.application.commands.state.load_world import LOAD_WORLD, LoadWorldCommand
from src.application.enums.event_sources import EventSource
from src.application.eventing.context import EventContext
from src.application.eventing.current_context import bind_event_context
from src.application.exceptions.world_state_errors import WorldStateCorruptionError, WorldStateFileNotFoundError
from src.application.services.auth_service import AuthService
from src.composition.container import Container
from src.composition.runtime import get_container, get_user_repository
from src.domain.enums.auth import Role
from src.ports.output.user_repository import UserRepositoryPort

logger = logging.getLogger(__name__)


def bootstrap_admin(auth: AuthService, store: UserRepositoryPort) -> None:
    if store.get_by_username("admin"):
        logger.info("Admin user already exists; skipping bootstrap.")
        return

    if not sys.stdin.isatty():
        logger.critical(
            "No admin user exists. Run the application interactively once to create the initial admin password."
        )
        raise RuntimeError(
            "No admin user exists. Run the application interactively once to create the initial admin password."
        )

    logger.warning("No admin user exists; starting interactive admin bootstrap.")
    password = getpass.getpass("Create initial manager password: ")
    confirmation = getpass.getpass("Confirm initial manager password: ")
    if password != confirmation:
        logger.warning("Initial admin bootstrap failed because password confirmation did not match.")
        raise ValueError("Initial manager passwords do not match.")

    auth.register_user(
        username="admin",
        role=Role.MANAGER,
        name="Admin",
        email="",
        phone_number="",
        password=password,
    )
    logger.info("Admin user successfully created.")


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
        logger.debug("Skipping default world-state load because autosave is disabled.")
        return

    default_world_state_path = container.default_world_state_path

    if not os.path.exists(default_world_state_path):
        logger.debug("No default world-state file found at %r.", default_world_state_path)
        return

    try:
        container.command_bus.dispatch(
            key=LOAD_WORLD,
            command=LoadWorldCommand(path=default_world_state_path),
        )
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
            logger.warning("Corrupt world state quarantined at %r.", quarantined_path)
        else:
            print(
                "WARNING: Saved world state could not be loaded.\n"
                "Starting with empty state.\n"
                "The corrupt file could not be moved aside automatically."
            )
            logger.warning("Corrupt world state could not be quarantined.")
    else:
        logger.info("Loaded default world state from %r.", default_world_state_path)


def main() -> None:
    configure_logging()
    logger.info("Starting FleetFlow CLI.")

    with bind_event_context(
        EventContext(
            correlation_id=uuid4(),
            source=EventSource.STARTUP,
        )
    ):
        container = get_container()
        logger.info(
            "FleetFlow CLI configured with autosave=%s, default_world_state_path=%r.",
            container.autosave_enabled,
            container.default_world_state_path,
        )

        auth = container.auth
        store = get_user_repository()
        bootstrap_admin(auth, store)

        _load_default_world_state(container)

    cmd_factory = CommandFactory(container)
    Engine(
        cmd_factory,
        auth,
        container.authz,
        container.state_cases.save,
        container.default_world_state_path,
        container.command_bus,
        container.autosave_enabled,
        container.event_collector,
    ).start()


if __name__ == "__main__":
    main()
