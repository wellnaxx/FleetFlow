"""Tests for exact-type audit descriptor registry behavior."""

import unittest
from dataclasses import dataclass
from datetime import datetime

from src.application.enums.audit_actions import AuditAction
from src.application.enums.audit_resource_types import AuditResourceType
from src.application.models.audit_descriptor import AuditDescriptor
from src.application.services.audit_mapping.mapper import AuditDescriptorMapper, audit_mapping
from src.application.services.audit_mapping.registry import AUDIT_MAPPINGS, build_audit_descriptor_mapper
from src.shared.event import Event

NOW = datetime(2025, 1, 1, 12, 0)


@dataclass(frozen=True, slots=True, kw_only=True)
class _RegisteredEvent(Event):
    resource_id: int


@dataclass(frozen=True, slots=True, kw_only=True)
class _DerivedEvent(_RegisteredEvent):
    pass


def _map_registered_event(event: _RegisteredEvent) -> AuditDescriptor:
    return AuditDescriptor(
        resource_type=AuditResourceType.PACKAGE,
        resource_id=str(event.resource_id),
        action=AuditAction.CREATED,
        payload_json={"resource_id": event.resource_id},
    )


class AuditDescriptorRegistryTests(unittest.TestCase):
    """Validate explicit registration and exact concrete-type dispatch."""

    def test_maps_registered_exact_event_type(self) -> None:
        mapper = AuditDescriptorMapper((audit_mapping(_RegisteredEvent, _map_registered_event),))

        descriptor = mapper.map(_RegisteredEvent(resource_id=7, occurred_at=NOW))

        self.assertEqual(descriptor.resource_id, "7")

    def test_does_not_implicitly_apply_base_event_mapping_to_subclass(self) -> None:
        mapper = AuditDescriptorMapper((audit_mapping(_RegisteredEvent, _map_registered_event),))

        with self.assertRaisesRegex(ValueError, "Unsupported event type: _DerivedEvent"):
            mapper.map(_DerivedEvent(resource_id=7, occurred_at=NOW))

    def test_rejects_duplicate_event_registration(self) -> None:
        entry = audit_mapping(_RegisteredEvent, _map_registered_event)

        with self.assertRaisesRegex(ValueError, "Duplicate audit mapping: _RegisteredEvent"):
            AuditDescriptorMapper((entry, entry))

    def test_default_mapper_exposes_every_registered_type_once(self) -> None:
        mapper = build_audit_descriptor_mapper()

        self.assertEqual(mapper.event_types, tuple(entry.event_type for entry in AUDIT_MAPPINGS))
        self.assertEqual(len(mapper.event_types), len(set(mapper.event_types)))
