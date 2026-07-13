"""Exact-type registry used to translate events into audit descriptors."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from types import MappingProxyType
from typing import cast

from src.application.models.audit_descriptor import AuditDescriptor
from src.shared.event import Event

type AuditDescriptorFactory = Callable[[Event], AuditDescriptor]


@dataclass(frozen=True, slots=True)
class AuditDescriptorMapping:
    """One exact event type and its audit descriptor factory."""

    event_type: type[Event]
    factory: AuditDescriptorFactory


def audit_mapping[E: Event](
    event_type: type[E],
    factory: Callable[[E], AuditDescriptor],
) -> AuditDescriptorMapping:
    """Create a registry entry while containing callable variance casting.

    Args:
        event_type: Concrete event class accepted by ``factory``.
        factory: Typed function that maps that event into an audit descriptor.

    Returns:
        Non-generic registry entry suitable for heterogeneous collections.
    """
    return AuditDescriptorMapping(
        event_type=event_type,
        factory=cast(AuditDescriptorFactory, factory),
    )


class AuditDescriptorMapper:
    """Map registered concrete event types through immutable lookup state."""

    def __init__(self, mappings: Iterable[AuditDescriptorMapping]) -> None:
        """Build an exact-type mapper and reject duplicate registrations.

        Args:
            mappings: Event mapping entries to register.

        Raises:
            ValueError: If an event type is registered more than once.
        """
        registry: dict[type[Event], AuditDescriptorFactory] = {}
        for entry in mappings:
            if entry.event_type in registry:
                raise ValueError(f"Duplicate audit mapping: {entry.event_type.__name__}")
            registry[entry.event_type] = entry.factory

        self._registry = MappingProxyType(registry)

    @property
    def event_types(self) -> tuple[type[Event], ...]:
        """Return registered event types in deterministic insertion order."""
        return tuple(self._registry)

    def map(self, event: Event) -> AuditDescriptor:
        """Map an event using its exact concrete type.

        Args:
            event: Domain or application event to map.

        Returns:
            Normalized audit descriptor for the event.

        Raises:
            ValueError: If no mapping exists for the concrete event type.
        """
        factory = self._registry.get(type(event))
        if factory is None:
            raise ValueError(f"Unsupported event type: {type(event).__name__}")
        return factory(event)
