"""Tests for synchronous query registration and dispatch."""

import unittest
from dataclasses import dataclass
from typing import cast

from src.application.messaging.errors import (
    DuplicateMessageHandlerError,
    MessageHandlerNotFoundError,
    MessageTypeMismatchError,
)
from src.application.messaging.in_process_query_bus import InProcessQueryBus
from src.application.messaging.query import Query, QueryKey


@dataclass(frozen=True, slots=True)
class ExampleQuery(Query):
    """Query used to exercise the test bus."""

    value: int


@dataclass(frozen=True, slots=True)
class DerivedExampleQuery(ExampleQuery):
    """Subclass used to verify exact-type routing."""


@dataclass(frozen=True, slots=True)
class OtherQuery(Query):
    """Distinct query used for mismatch tests."""

    value: str


EXAMPLE: QueryKey[ExampleQuery, object] = QueryKey(
    name="example",
    query_type=ExampleQuery,
)
EXAMPLE_ALIAS: QueryKey[ExampleQuery, object] = QueryKey(
    name="example_alias",
    query_type=ExampleQuery,
)
OTHER_WITH_EXAMPLE_NAME: QueryKey[OtherQuery, object] = QueryKey(
    name="example",
    query_type=OtherQuery,
)


class ReturningHandler:
    """Record one query and return a configured object."""

    def __init__(self, result: object) -> None:
        self.result = result
        self.queries: list[ExampleQuery] = []

    def execute(self, query: ExampleQuery) -> object:
        self.queries.append(query)
        return self.result


class RaisingHandler:
    """Raise a configured exception when invoked."""

    def __init__(self, error: Exception) -> None:
        self.error = error

    def execute(self, query: ExampleQuery) -> object:
        del query
        raise self.error


class InProcessQueryBusShould(unittest.TestCase):
    """Verify query-bus registration and exact routing invariants."""

    def test_dispatch_returns_exact_handler_result(self) -> None:
        bus = InProcessQueryBus()
        expected = object()
        handler = ReturningHandler(expected)
        query = ExampleQuery(value=7)
        bus.register(EXAMPLE, handler)

        result = bus.dispatch(EXAMPLE, query)

        self.assertIs(result, expected)
        self.assertEqual(handler.queries, [query])

    def test_dispatch_propagates_exact_handler_exception(self) -> None:
        bus = InProcessQueryBus()
        expected = RuntimeError("handler failed")
        bus.register(EXAMPLE, RaisingHandler(expected))

        with self.assertRaises(RuntimeError) as raised:
            bus.dispatch(EXAMPLE, ExampleQuery(value=7))

        self.assertIs(raised.exception, expected)

    def test_register_rejects_duplicate_key_name_and_preserves_first_handler(self) -> None:
        bus = InProcessQueryBus()
        first_result = object()
        bus.register(EXAMPLE, ReturningHandler(first_result))

        with self.assertRaises(DuplicateMessageHandlerError):
            bus.register(EXAMPLE, ReturningHandler(object()))

        self.assertIs(bus.dispatch(EXAMPLE, ExampleQuery(value=7)), first_result)

    def test_dispatch_rejects_unregistered_key_name(self) -> None:
        bus = InProcessQueryBus()

        with self.assertRaises(MessageHandlerNotFoundError):
            bus.dispatch(EXAMPLE, ExampleQuery(value=7))

    def test_unregistered_alias_cannot_reuse_handler_for_same_query_type(self) -> None:
        bus = InProcessQueryBus()
        bus.register(EXAMPLE, ReturningHandler(object()))

        with self.assertRaises(MessageHandlerNotFoundError):
            bus.dispatch(EXAMPLE_ALIAS, ExampleQuery(value=7))

    def test_separately_registered_alias_uses_its_own_handler(self) -> None:
        bus = InProcessQueryBus()
        primary_result = object()
        alias_result = object()
        bus.register(EXAMPLE, ReturningHandler(primary_result))
        bus.register(EXAMPLE_ALIAS, ReturningHandler(alias_result))

        self.assertIs(bus.dispatch(EXAMPLE, ExampleQuery(value=7)), primary_result)
        self.assertIs(bus.dispatch(EXAMPLE_ALIAS, ExampleQuery(value=7)), alias_result)

    def test_dispatch_rejects_message_that_does_not_match_key_type(self) -> None:
        bus = InProcessQueryBus()
        bus.register(EXAMPLE, ReturningHandler(object()))
        wrong_query = cast(ExampleQuery, OtherQuery(value="wrong"))

        with self.assertRaises(MessageTypeMismatchError):
            bus.dispatch(EXAMPLE, wrong_query)

    def test_dispatch_rejects_query_subclass(self) -> None:
        bus = InProcessQueryBus()
        bus.register(EXAMPLE, ReturningHandler(object()))
        derived: ExampleQuery = DerivedExampleQuery(value=7)

        with self.assertRaises(MessageTypeMismatchError):
            bus.dispatch(EXAMPLE, derived)

    def test_dispatch_rejects_registered_name_with_different_declared_type(self) -> None:
        bus = InProcessQueryBus()
        bus.register(EXAMPLE, ReturningHandler(object()))

        with self.assertRaises(MessageTypeMismatchError):
            bus.dispatch(OTHER_WITH_EXAMPLE_NAME, OtherQuery(value="wrong"))


if __name__ == "__main__":
    unittest.main()
