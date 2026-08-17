"""Collect pending events from recorders and publish them as envelopes."""

from collections.abc import Iterable
from typing import NamedTuple, Protocol

from src.application.eventing.current_context import envelope_event
from src.ports.output.event_publisher import EventPublisherPort
from src.shared.event import Event


class EventRecorder(Protocol):
    """Structural contract for an object buffering unpublished events.

    Application execution scopes and domain entities satisfy this protocol
    without sharing an inheritance hierarchy. Collectors only need immutable
    access to pending events and a way to clear them after the complete
    publication batch succeeds.
    """

    @property
    def pending_events(self) -> tuple[Event, ...]:
        """Return pending events in their original recording order."""
        ...

    def clear_events(self) -> None:
        """Remove every pending event after successful publication."""
        ...


class _RecorderSnapshot(NamedTuple):
    """Pending events captured from one live recorder.

    The ``events`` tuple is an immutable copy of the recorder's pending events
    at capture time. The ``recorder`` reference itself remains live and mutable;
    this collector is intended for synchronous, single-workflow draining where
    handlers do not mutate the same recorders while publication is in progress.
    """

    recorder: EventRecorder
    events: tuple[Event, ...]


class EventCollector:
    """Envelope, publish, and clear pending events from event recorders.

    Events are published in recorder order, preserving the recording order
    within each recorder. Pending events are cleared only after the publisher
    accepts the complete batch. If publication fails, recorders keep their
    events so the caller can retry or inspect the failure.
    """

    def __init__(self, publisher: EventPublisherPort) -> None:
        """Initialize the collector with its event publisher.

        Args:
            publisher: Output port used to publish enriched event envelopes.
        """
        self._publisher = publisher

    def drain(self, recorders: Iterable[EventRecorder]) -> None:
        """Publish all pending events from recorders and clear them on success.

        Args:
            recorders: Execution scopes or domain entities that may hold
                pending events.

        Raises:
            ValueError: If the same recorder object is supplied more than once.
            RuntimeError: If no event context is currently bound.
            Exception: Propagates publisher failures. In that case, no recorder
                events are cleared.
        """
        materialized_recorders = tuple(recorders)
        snapshots = self._capture_snapshots(materialized_recorders)
        events = [event for snapshot in snapshots for event in snapshot.events]
        if not events:
            return

        envelopes = tuple(envelope_event(event) for event in events)
        self._publisher.publish_all(envelopes)

        for snapshot in snapshots:
            snapshot.recorder.clear_events()

    @staticmethod
    def _capture_snapshots(recorders: Iterable[EventRecorder]) -> tuple[_RecorderSnapshot, ...]:
        """Capture pending events from each unique recorder.

        Args:
            recorders: Event recorders to inspect.

        Returns:
            Snapshots for recorders that currently have pending events.

        Raises:
            ValueError: If one recorder object is supplied more than once.
        """
        snapshots: list[_RecorderSnapshot] = []
        seen_ids: set[int] = set()

        for recorder in recorders:
            recorder_id = id(recorder)
            if recorder_id in seen_ids:
                raise ValueError("The same event recorder was supplied more than once.")

            seen_ids.add(recorder_id)

            events = recorder.pending_events
            if events:
                snapshots.append(_RecorderSnapshot(recorder=recorder, events=events))

        return tuple(snapshots)
