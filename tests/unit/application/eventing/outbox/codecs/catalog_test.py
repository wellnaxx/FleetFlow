"""Keep current payload codecs complete against the published-event catalog.

Discovery is test-only, not runtime registration. Only classes defined in their
own module and named ``*EventPayloadCodec`` are included, avoiding imported
protocols and re-exports. Historical decoder classes are not current codecs.
"""

import inspect
import unittest
from importlib import import_module
from pkgutil import walk_packages
from typing import cast
from unittest.mock import patch

from src.application.eventing.outbox.codec import EventPayloadCodec
from src.application.eventing.outbox.errors import DuplicateEventCodecError
from src.application.eventing.outbox.registry import EventOutboxCodecRegistry
from src.composition.event_catalog import PUBLISHED_EVENT_TYPES
from src.composition.outbox_codecs import build_event_payload_codec_registry, register_event_payload_codecs
from src.shared.event import Event


def _discover_current_codecs() -> tuple[EventPayloadCodec[Event], ...]:
    """Instantiate current codecs in deterministic module/class order.

    Concrete codecs are stateless and have no constructor dependencies. Import
    and construction failures deliberately fail the test rather than silently
    excluding a broken codec from the completeness check.
    """
    codecs = import_module("src.application.eventing.outbox.codecs")
    discovered: list[EventPayloadCodec[Event]] = []
    modules = sorted(walk_packages(codecs.__path__, prefix=f"{codecs.__name__}."), key=lambda item: item.name)
    for module_info in modules:
        module = import_module(module_info.name)
        for name, candidate in inspect.getmembers(module, inspect.isclass):
            if candidate.__module__ == module.__name__ and name.endswith("EventPayloadCodec"):
                codec_class = cast(type[EventPayloadCodec[Event]], candidate)
                discovered.append(codec_class())
    return tuple(discovered)


class CurrentCodecCatalogShould(unittest.TestCase):
    """Guard catalog coverage and the joint registration contract."""

    def setUp(self) -> None:
        self.codecs = _discover_current_codecs()

    def test_covers_every_published_event_exactly_once_without_extra_codecs(self) -> None:
        self.assertTrue(PUBLISHED_EVENT_TYPES, "The published-event catalog must not be empty.")
        self.assertEqual(
            len(PUBLISHED_EVENT_TYPES),
            len(set(PUBLISHED_EVENT_TYPES)),
            "The published-event catalog contains duplicate classes.",
        )
        self.assertCountEqual(
            [codec.event_class for codec in self.codecs],
            PUBLISHED_EVENT_TYPES,
            "Each published event must have exactly one current payload codec, with no extra codecs.",
        )

    def test_current_versions_are_positive_integers_matching_event_classes(self) -> None:
        for codec in self.codecs:
            with self.subTest(codec=type(codec).__name__):
                self.assertIs(type(codec.event_version), int)
                self.assertGreater(codec.event_version, 0)
                self.assertEqual(codec.event_version, codec.event_class.event_version)

    def test_current_wire_identities_are_unique(self) -> None:
        identities = [(codec.event_type, codec.event_version) for codec in self.codecs]
        self.assertEqual(len(identities), len(set(identities)), f"Duplicate wire identities: {identities}")

    def test_all_current_codecs_register_together_and_resolve_by_identity(self) -> None:
        registry = EventOutboxCodecRegistry()
        with patch.object(registry, "register", wraps=registry.register) as register:
            result = register_event_payload_codecs(registry)

        self.assertIsNone(result)
        self.assertEqual(
            [call.args[0] for call in register.call_args_list],
            list(PUBLISHED_EVENT_TYPES),
        )
        self.assertCountEqual(
            [(call.args[0], type(call.args[1])) for call in register.call_args_list],
            [(codec.event_class, type(codec)) for codec in self.codecs],
        )

        for codec in self.codecs:
            with self.subTest(codec=type(codec).__name__):
                adapter = registry.for_identity(codec.event_type, codec.event_version)
                self.assertIs(adapter.event_class, codec.event_class)
                self.assertEqual(adapter.event_type, codec.event_type)
                self.assertEqual(adapter.event_version, codec.event_version)

    def test_repeated_registration_rejects_duplicates_without_replacing_adapters(self) -> None:
        registry = EventOutboxCodecRegistry()
        register_event_payload_codecs(registry)
        adapters = [registry.for_identity(codec.event_type, codec.event_version) for codec in self.codecs]

        with self.assertRaises(DuplicateEventCodecError):
            register_event_payload_codecs(registry)

        for codec, adapter in zip(self.codecs, adapters, strict=True):
            with self.subTest(codec=type(codec).__name__):
                self.assertIs(registry.for_identity(codec.event_type, codec.event_version), adapter)

    def test_builder_populates_and_returns_the_registry_passed_to_registration(self) -> None:
        with patch(
            "src.composition.outbox_codecs.register_event_payload_codecs",
            wraps=register_event_payload_codecs,
        ) as register:
            registry = build_event_payload_codec_registry()

        register.assert_called_once_with(registry)
        registered_events: list[type[Event]] = []
        for codec in self.codecs:
            with self.subTest(codec=type(codec).__name__):
                adapter = registry.for_identity(codec.event_type, codec.event_version)
                self.assertIs(adapter.event_class, codec.event_class)
                self.assertEqual(adapter.event_type, codec.event_type)
                self.assertEqual(adapter.event_version, codec.event_version)
                registered_events.append(adapter.event_class)
        self.assertCountEqual(registered_events, PUBLISHED_EVENT_TYPES)

    def test_builder_creates_independent_registries_and_adapters_on_every_call(self) -> None:
        first = build_event_payload_codec_registry()
        first_adapters = [first.for_identity(codec.event_type, codec.event_version) for codec in self.codecs]

        second = build_event_payload_codec_registry()

        self.assertIsNot(first, second)
        for codec, original in zip(self.codecs, first_adapters, strict=True):
            with self.subTest(codec=type(codec).__name__):
                self.assertIs(first.for_identity(codec.event_type, codec.event_version), original)
                self.assertIsNot(second.for_identity(codec.event_type, codec.event_version), original)

    def test_builder_propagates_registration_errors_unchanged(self) -> None:
        failure = DuplicateEventCodecError("Conflicting codec identity")
        with (
            patch(
                "src.composition.outbox_codecs.register_event_payload_codecs",
                side_effect=failure,
            ) as register,
            self.assertRaises(DuplicateEventCodecError) as raised,
        ):
            build_event_payload_codec_registry()

        self.assertIs(raised.exception, failure)
        register.assert_called_once()
