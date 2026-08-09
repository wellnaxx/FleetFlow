"""Synchronous in-process command registration and dispatch."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from src.application.messaging.command import Command, CommandKey
from src.application.messaging.errors import (
    DuplicateMessageHandlerError,
    MessageHandlerNotFoundError,
    MessageTypeMismatchError,
)
from src.application.messaging.handlers import CommandHandler


@dataclass(frozen=True, slots=True)
class _CommandRegistration:
    """Runtime-erased command registration stored by routing-key name.

    Attributes:
        command_type: Exact command class accepted by the registration.
        invoke: Type-erased adapter that validates and invokes the concrete
            command handler.
    """

    command_type: type[Command]
    invoke: Callable[[Command], object]


class InProcessCommandBus:
    """Register and synchronously dispatch typed commands in one process.

    Registration is mutable so composition can build the routing table during
    startup. Driving adapters should receive only the dispatch-only
    :class:`~src.ports.input.command_bus.CommandBus` protocol.

    Routing names are the runtime identity of command keys. Each registration
    also retains its exact command type so a newly constructed key cannot
    reuse an occupied name with a different command contract.
    """

    def __init__(self) -> None:
        """Initialize an empty command-handler registry."""
        self._handlers: dict[str, _CommandRegistration] = {}

    def register[C: Command, R](self, key: CommandKey[C, R], handler: CommandHandler[C, R]) -> None:
        """Register one handler under a typed command key.

        Args:
            key: Stable routing name and exact command type to register.
            handler: Concrete handler accepting the key's command type and
                producing its statically associated result.

        Raises:
            DuplicateMessageHandlerError: If ``key.name`` is already
                registered. Existing registrations are never replaced.

        Note:
            The generic signature enforces key/handler compatibility during
            static analysis. Python does not expose those generic parameters
            reliably at runtime, so registration does not inspect handler
            annotations.
        """
        if key.name in self._handlers:
            raise DuplicateMessageHandlerError(f"Handler already registered for {key.name!r}.")

        def invoke(command: Command) -> object:
            if type(command) is not key.command_type:
                raise MessageTypeMismatchError(
                    f"Registration {key.name!r} expects {key.command_type.__name__}, "
                    f"got {type(command).__name__}."
                )
            return handler.handle(cast(C, command))

        self._handlers[key.name] = _CommandRegistration(
            command_type=key.command_type,
            invoke=invoke,
        )

    def dispatch[C: Command, R](self, key: CommandKey[C, R], command: C) -> R:
        """Synchronously dispatch a command through its registered key.

        Args:
            key: Typed routing key selecting the handler and result type.
            command: Exact command instance declared by ``key``.

        Returns:
            Result returned by the registered command handler.

        Raises:
            MessageTypeMismatchError: If the command's exact runtime type does
                not match ``key.command_type``, or if the registered key name
                belongs to a different command type.
            MessageHandlerNotFoundError: If no handler is registered under
                ``key.name``.
            Exception: Propagates any failure raised by the handler unchanged.
        """
        if type(command) is not key.command_type:
            raise MessageTypeMismatchError(
                f"Command key {key.name!r} expects {key.command_type.__name__}, got {type(command).__name__}."
            )

        try:
            registration = self._handlers[key.name]
        except KeyError as exc:
            raise MessageHandlerNotFoundError(f"No handler registered for {key.name!r}.") from exc

        if registration.command_type is not key.command_type:
            raise MessageTypeMismatchError(
                f"Command key {key.name!r} declares {key.command_type.__name__}, but the registration "
                f"expects {registration.command_type.__name__}."
            )

        return cast(R, registration.invoke(command))
