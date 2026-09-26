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

from src.application.eventing.outbox.codec import EventPayloadCodec
from src.application.eventing.outbox.registry import EventOutboxCodecRegistry
from src.composition.event_catalog import PUBLISHED_EVENT_TYPES
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
        for codec in self.codecs:
            registry.register(codec.event_class, codec)

        for codec in self.codecs:
            with self.subTest(codec=type(codec).__name__):
                adapter = registry.for_identity(codec.event_type, codec.event_version)
                self.assertIs(adapter.event_class, codec.event_class)
                self.assertEqual(adapter.event_type, codec.event_type)
                self.assertEqual(adapter.event_version, codec.event_version)
