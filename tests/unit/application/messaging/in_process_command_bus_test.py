"""Tests for synchronous command registration and dispatch."""

import unittest
from dataclasses import dataclass
from typing import cast

from src.application.messaging.command import Command, CommandKey
from src.application.messaging.errors import (
    DuplicateMessageHandlerError,
    MessageHandlerNotFoundError,
    MessageTypeMismatchError,
)
from src.application.messaging.in_process_command_bus import InProcessCommandBus


@dataclass(frozen=True, slots=True)
class ExampleCommand(Command):
    """Command used to exercise the test bus."""

    value: int


@dataclass(frozen=True, slots=True)
class DerivedExampleCommand(ExampleCommand):
    """Subclass used to verify exact-type routing."""


@dataclass(frozen=True, slots=True)
class OtherCommand(Command):
    """Distinct command used for mismatch tests."""

    value: str


EXAMPLE: CommandKey[ExampleCommand, object] = CommandKey(
    name="example",
    command_type=ExampleCommand,
)
EXAMPLE_ALIAS: CommandKey[ExampleCommand, object] = CommandKey(
    name="example_alias",
    command_type=ExampleCommand,
)
OTHER_WITH_EXAMPLE_NAME: CommandKey[OtherCommand, object] = CommandKey(
    name="example",
    command_type=OtherCommand,
)


class ReturningHandler:
    """Record one command and return a configured object."""

    def __init__(self, result: object) -> None:
        self.result = result
        self.commands: list[ExampleCommand] = []

    def execute(self, command: ExampleCommand) -> object:
        self.commands.append(command)
        return self.result


class RaisingHandler:
    """Raise a configured exception when invoked."""

    def __init__(self, error: Exception) -> None:
        self.error = error

    def execute(self, command: ExampleCommand) -> object:
        del command
        raise self.error


class InProcessCommandBusShould(unittest.TestCase):
    """Verify command-bus registration and exact routing invariants."""

    def test_dispatch_returns_exact_handler_result(self) -> None:
        bus = InProcessCommandBus()
        expected = object()
        handler = ReturningHandler(expected)
        command = ExampleCommand(value=7)
        bus.register(EXAMPLE, handler)

        result = bus.dispatch(EXAMPLE, command)

        self.assertIs(result, expected)
        self.assertEqual(handler.commands, [command])

    def test_dispatch_propagates_exact_handler_exception(self) -> None:
        bus = InProcessCommandBus()
        expected = RuntimeError("handler failed")
        bus.register(EXAMPLE, RaisingHandler(expected))

        with self.assertRaises(RuntimeError) as raised:
            bus.dispatch(EXAMPLE, ExampleCommand(value=7))

        self.assertIs(raised.exception, expected)

    def test_register_rejects_duplicate_key_name_and_preserves_first_handler(self) -> None:
        bus = InProcessCommandBus()
        first_result = object()
        bus.register(EXAMPLE, ReturningHandler(first_result))

        with self.assertRaises(DuplicateMessageHandlerError):
            bus.register(EXAMPLE, ReturningHandler(object()))

        self.assertIs(bus.dispatch(EXAMPLE, ExampleCommand(value=7)), first_result)

    def test_dispatch_rejects_unregistered_key_name(self) -> None:
        bus = InProcessCommandBus()

        with self.assertRaises(MessageHandlerNotFoundError):
            bus.dispatch(EXAMPLE, ExampleCommand(value=7))

    def test_unregistered_alias_cannot_reuse_handler_for_same_command_type(self) -> None:
        bus = InProcessCommandBus()
        bus.register(EXAMPLE, ReturningHandler(object()))

        with self.assertRaises(MessageHandlerNotFoundError):
            bus.dispatch(EXAMPLE_ALIAS, ExampleCommand(value=7))

    def test_separately_registered_alias_uses_its_own_handler(self) -> None:
        bus = InProcessCommandBus()
        primary_result = object()
        alias_result = object()
        bus.register(EXAMPLE, ReturningHandler(primary_result))
        bus.register(EXAMPLE_ALIAS, ReturningHandler(alias_result))

        self.assertIs(bus.dispatch(EXAMPLE, ExampleCommand(value=7)), primary_result)
        self.assertIs(bus.dispatch(EXAMPLE_ALIAS, ExampleCommand(value=7)), alias_result)

    def test_dispatch_rejects_message_that_does_not_match_key_type(self) -> None:
        bus = InProcessCommandBus()
        bus.register(EXAMPLE, ReturningHandler(object()))
        wrong_command = cast(ExampleCommand, OtherCommand(value="wrong"))

        with self.assertRaises(MessageTypeMismatchError):
            bus.dispatch(EXAMPLE, wrong_command)

    def test_dispatch_rejects_command_subclass(self) -> None:
        bus = InProcessCommandBus()
        bus.register(EXAMPLE, ReturningHandler(object()))
        derived: ExampleCommand = DerivedExampleCommand(value=7)

        with self.assertRaises(MessageTypeMismatchError):
            bus.dispatch(EXAMPLE, derived)

    def test_dispatch_rejects_registered_name_with_different_declared_type(self) -> None:
        bus = InProcessCommandBus()
        bus.register(EXAMPLE, ReturningHandler(object()))

        with self.assertRaises(MessageTypeMismatchError):
            bus.dispatch(OTHER_WITH_EXAMPLE_NAME, OtherCommand(value="wrong"))


if __name__ == "__main__":
    unittest.main()
