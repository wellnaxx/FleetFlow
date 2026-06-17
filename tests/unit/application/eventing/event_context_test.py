"""Tests for event envelopes and context-local workflow metadata."""

import asyncio
import unittest
from dataclasses import FrozenInstanceError
from datetime import datetime
from uuid import UUID, uuid4

from src.application.enums.event_sources import EventSource
from src.application.enums.user_login_rejection_reasons import UserLoginRejectionReason
from src.application.eventing.context import EventContext
from src.application.eventing.current_context import (
    bind_event_context,
    envelope_event,
    get_event_context,
    get_optional_event_context,
)
from src.application.eventing.envelope import EventActor, EventEnvelope
from src.application.events.auth_events import UserLoginRejected


def _event(username: str = "alice") -> UserLoginRejected:
    return UserLoginRejected(
        user_id=None,
        username=username,
        reason=UserLoginRejectionReason.USER_NOT_FOUND,
        occurred_at=datetime(2026, 6, 11, 10, 0),
    )


def _context(
    *,
    source: EventSource = EventSource.HTTP,
    actor: EventActor | None = None,
    correlation_id: UUID | None = None,
    causation_id: UUID | None = None,
) -> EventContext:
    return EventContext(
        correlation_id=correlation_id or uuid4(),
        source=source,
        actor=actor,
        causation_id=causation_id,
    )


class EventContextShould(unittest.IsolatedAsyncioTestCase):
    def tearDown(self) -> None:
        self.assertIsNone(get_optional_event_context())

    def test_reject_invalid_actor_user_ids(self) -> None:
        invalid_user_ids: tuple[object, ...] = (0, -1, True, False, None, 1.5, "1")

        for user_id in invalid_user_ids:
            with (
                self.subTest(user_id=user_id),
                self.assertRaisesRegex(
                    ValueError,
                    r"^user_id must be a positive integer\.$",
                ),
            ):
                EventActor(user_id=user_id, username="alice")  # type: ignore[arg-type]

    def test_reject_invalid_actor_usernames(self) -> None:
        invalid_usernames: tuple[object, ...] = ("", " ", "\t", None, 1, True)

        for username in invalid_usernames:
            with (
                self.subTest(username=username),
                self.assertRaisesRegex(
                    (ValueError, TypeError),
                    r"^username must be a non-empty string\.$",
                ),
            ):
                EventActor(user_id=1, username=username)  # type: ignore[arg-type]

    def test_normalize_actor_username(self) -> None:
        actor = EventActor(user_id=7, username="  Fleet.Manager  ")

        self.assertEqual(actor.user_id, 7)
        self.assertEqual(actor.username, "fleet.manager")

    def test_keep_actor_immutable(self) -> None:
        actor = EventActor(user_id=7, username="manager")

        with self.assertRaises(FrozenInstanceError):
            actor.username = "employee"  # type: ignore[reportAttributeAccessIssue]

    def test_generate_unique_envelope_ids(self) -> None:
        context = _context()
        event = _event()

        first = context.wrap(event)
        second = context.wrap(event)

        self.assertNotEqual(first.envelope_id, second.envelope_id)

    def test_accept_explicit_envelope_id(self) -> None:
        envelope_id = uuid4()

        envelope = EventEnvelope(
            event=_event(),
            source=EventSource.SYSTEM,
            correlation_id=uuid4(),
            envelope_id=envelope_id,
        )

        self.assertEqual(envelope.envelope_id, envelope_id)

    def test_wrap_event_with_all_context_metadata(self) -> None:
        actor = EventActor(user_id=7, username="manager")
        correlation_id = uuid4()
        causation_id = uuid4()
        context = _context(
            source=EventSource.CLI,
            actor=actor,
            correlation_id=correlation_id,
            causation_id=causation_id,
        )
        event = _event()

        envelope = context.wrap(event)

        self.assertIs(envelope.event, event)
        self.assertIs(envelope.source, EventSource.CLI)
        self.assertIs(envelope.actor, actor)
        self.assertEqual(envelope.correlation_id, correlation_id)
        self.assertEqual(envelope.causation_id, causation_id)

    def test_wrap_system_event_without_actor(self) -> None:
        envelope = _context(source=EventSource.STARTUP, actor=None).wrap(_event())

        self.assertIsNone(envelope.actor)
        self.assertIs(envelope.source, EventSource.STARTUP)

    def test_raise_when_context_is_unbound(self) -> None:
        self.assertIsNone(get_optional_event_context())

        with self.assertRaisesRegex(RuntimeError, r"^No event context is bound\.$"):
            get_event_context()

    def test_expose_and_clear_bound_context(self) -> None:
        context = _context()

        with bind_event_context(context):
            self.assertIs(get_event_context(), context)
            self.assertIs(get_optional_event_context(), context)

        self.assertIsNone(get_optional_event_context())

    def test_reset_bound_context_after_exception(self) -> None:
        context = _context()

        with self.assertRaisesRegex(ValueError, "failure"), bind_event_context(context):
            raise ValueError("failure")

        self.assertIsNone(get_optional_event_context())

    def test_restore_outer_context_after_nested_binding(self) -> None:
        outer = _context(source=EventSource.CLI)
        inner = _context(source=EventSource.HEARTBEAT)

        with bind_event_context(outer):
            self.assertIs(get_event_context(), outer)
            with bind_event_context(inner):
                self.assertIs(get_event_context(), inner)
            self.assertIs(get_event_context(), outer)

        self.assertIsNone(get_optional_event_context())

    def test_envelope_event_uses_bound_context(self) -> None:
        actor = EventActor(user_id=7, username="manager")
        context = _context(actor=actor)
        event = _event()

        with bind_event_context(context):
            envelope = envelope_event(event)

        self.assertIs(envelope.event, event)
        self.assertIs(envelope.actor, actor)
        self.assertEqual(envelope.correlation_id, context.correlation_id)

    def test_envelope_event_raises_when_context_is_unbound(self) -> None:
        with self.assertRaisesRegex(RuntimeError, r"^No event context is bound\.$"):
            envelope_event(_event())

    async def test_isolate_context_bindings_between_async_tasks(self) -> None:
        first = _context(source=EventSource.HTTP)
        second = _context(source=EventSource.HEARTBEAT)
        first_bound = asyncio.Event()
        second_bound = asyncio.Event()

        async def bind_first() -> EventContext:
            with bind_event_context(first):
                first_bound.set()
                await second_bound.wait()
                return get_event_context()

        async def bind_second() -> EventContext:
            await first_bound.wait()
            with bind_event_context(second):
                second_bound.set()
                await asyncio.sleep(0)
                return get_event_context()

        first_result, second_result = await asyncio.gather(bind_first(), bind_second())

        self.assertIs(first_result.source, EventSource.HTTP)
        self.assertIs(second_result.source, EventSource.HEARTBEAT)
