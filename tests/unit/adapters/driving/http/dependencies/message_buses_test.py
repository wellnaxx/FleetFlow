"""Tests for authenticated HTTP message-bus dependencies."""

import unittest
from typing import cast
from unittest.mock import MagicMock

from src.adapters.driving.http.dependencies.auth import AuthenticatedHTTPPrincipal
from src.adapters.driving.http.dependencies.message_buses import (
    get_authenticated_command_bus,
    get_authenticated_query_bus,
    get_command_bus,
)
from src.composition.container import Container
from src.ports.input.command_bus import CommandBus
from src.ports.input.query_bus import QueryBus


class MessageBusDependenciesShould(unittest.TestCase):
    """Expose public and authenticated buses from the container."""

    def setUp(self) -> None:
        """Create isolated principal, container, and bus doubles."""
        self.principal = cast(AuthenticatedHTTPPrincipal, MagicMock())
        self.container = cast(Container, MagicMock())
        self.command_bus = MagicMock(spec=CommandBus)
        self.query_bus = MagicMock(spec=QueryBus)
        self.container.command_bus = self.command_bus
        self.container.query_bus = self.query_bus

    def test_returns_container_command_bus(self) -> None:
        """Return the configured bus after authentication."""
        result = get_authenticated_command_bus(self.principal, self.container)

        self.assertIs(result, self.command_bus)

    def test_returns_public_container_command_bus(self) -> None:
        """Return the command bus without requiring a principal."""
        result = get_command_bus(self.container)

        self.assertIs(result, self.command_bus)

    def test_returns_container_query_bus(self) -> None:
        """Return the configured query bus without wrapping it."""
        result = get_authenticated_query_bus(self.principal, self.container)

        self.assertIs(result, self.query_bus)


if __name__ == "__main__":
    unittest.main()
