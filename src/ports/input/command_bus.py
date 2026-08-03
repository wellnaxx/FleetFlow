"""Input port for dispatching typed application commands."""

from typing import Protocol

from src.application.messaging.command import Command, CommandKey


class CommandBus(Protocol):
    """Dispatch-only application boundary for state-changing requests.

    Driving adapters depend on this narrow protocol and cannot mutate the
    handler registry. Composition configures handlers through the concrete bus
    implementation before exposing it as this input port.
    """

    def dispatch[C: Command, R](self, key: CommandKey[C, R], command: C) -> R:
        """Dispatch a command to the exact handler registered for its key.

        Args:
            key: Typed routing key binding the concrete command to result ``R``.
            command: Concrete command instance accepted by ``key``.

        Returns:
            Value returned by the registered command handler.

        Raises:
            LookupError: If no handler is registered for ``key``.
            TypeError: If the runtime command type does not match the key's
                declared command type.
            Exception: Propagates failures raised by the registered handler.
        """
        ...
