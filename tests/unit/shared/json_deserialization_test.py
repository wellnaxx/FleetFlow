"""Tests for JSON timestamp parsing and contextual enum decoding."""

import unittest
from collections.abc import Callable
from datetime import UTC, datetime
from enum import Enum, StrEnum
from uuid import uuid4

from src.shared.json_deserialization import (
    parse_enum_name,
    parse_enum_value,
    parse_naive_datetime,
    parse_optional_naive_datetime,
)

PARSERS: tuple[Callable[[object, str], datetime | None], ...] = (
    parse_naive_datetime,
    parse_optional_naive_datetime,
)


class JsonDeserializationShould(unittest.TestCase):
    def test_parses_existing_iso_forms_without_changing_precision_or_business_time(self) -> None:
        expected = datetime(2030, 1, 2, 3, 4, 5, 123456)
        cases = (
            ("2030-01-02T03:04:05.123456", expected),
            ("2030-01-02 03:04:05.123456", expected),
            ("2030-01-02T03:04:05,123456", expected),
            ("20300102T030405.123456", expected),
            ("2030-01-02T03:04:05.123456789", expected),
            ("2030-01-02T03:04:05.1", datetime(2030, 1, 2, 3, 4, 5, 100000)),
            ("2030-01-02T03:04:05", datetime(2030, 1, 2, 3, 4, 5)),
            ("2030-01-02T03:04", datetime(2030, 1, 2, 3, 4)),
            ("2030-01-02", datetime(2030, 1, 2)),
            ("2028-02-29T12:00:00", datetime(2028, 2, 29, 12)),
            (datetime.min.isoformat(), datetime.min),
            (datetime.max.isoformat(), datetime.max),
        )
        for parser in PARSERS:
            for text, expected in cases:
                with self.subTest(parser=parser.__name__, text=text):
                    parsed = parser(text, "departure_time")
                    self.assertEqual(parsed, expected)
                    self.assertIsInstance(parsed, datetime)
                    assert parsed is not None
                    self.assertIsNone(parsed.tzinfo)

    def test_optional_parser_accepts_null_but_required_parser_rejects_it(self) -> None:
        self.assertIsNone(parse_optional_naive_datetime(None, "departure_time"))
        with self.assertRaisesRegex(TypeError, "departure_time: expected str, got NoneType"):
            parse_naive_datetime(None, "departure_time")

    def test_rejects_non_string_values_without_coercion(self) -> None:
        values: tuple[object, ...] = (
            True,
            False,
            0,
            20300102,
            1.5,
            b"2030-01-02T03:04:05",
            [],
            {},
            ("2030-01-02T03:04:05",),
            datetime(2030, 1, 2),
            datetime(2030, 1, 2, tzinfo=UTC),
            uuid4(),
        )
        for parser in PARSERS:
            for value in values:
                with (
                    self.subTest(parser=parser.__name__, value=value),
                    self.assertRaisesRegex(TypeError, "expected_arrival: expected str"),
                ):
                    parser(value, "expected_arrival")

    def test_invalid_text_raises_field_specific_error_with_original_parse_cause(self) -> None:
        values = (
            "",
            "   ",
            "null",
            "not-a-datetime",
            "03:04:05",
            "2030-13-02T03:04:05",
            "2030-02-29T03:04:05",
            "2030-01-02T24:00:00",
            "2030-01-02T03:04:60",
            "0000-01-01",
            "10000-01-01",
            "2030-01-02T03:04:05garbage",
            " 2030-01-02T03:04:05",
            "2030-01-02T03:04:05 ",
        )
        for parser in PARSERS:
            for value in values:
                with self.subTest(parser=parser.__name__, value=value):
                    with self.assertRaises(ValueError) as raised:
                        parser(value, "scheduled_delivery_time")
                    self.assertEqual(
                        str(raised.exception), "scheduled_delivery_time: expected ISO-formatted datetime."
                    )
                    self.assertIsInstance(raised.exception.__cause__, ValueError)

    def test_rejects_all_aware_business_timestamps_without_dropping_or_converting_offsets(self) -> None:
        for parser in PARSERS:
            for offset in ("Z", "+00:00", "-00:00", "+10:00", "-04:00", "+05:30"):
                with self.subTest(parser=parser.__name__, offset=offset):
                    with self.assertRaises(ValueError) as raised:
                        parser(f"2030-01-02T03:04:05.123456{offset}", "previous_busy_until")
                    self.assertEqual(str(raised.exception), "previous_busy_until must be timezone-naive.")
                    self.assertIsNone(raised.exception.__cause__)


class _State(Enum):
    READY = "ready"
    COMPLETE = "complete"
    FINISHED = COMPLETE


class _TextState(StrEnum):
    READY = "ready"
    COMPLETE = "complete"


class _Permission(Enum):
    READ = 1
    VIEW = READ
    WRITE = 2


class JsonEnumDeserializationShould(unittest.TestCase):
    def test_values_preserve_member_identity_for_enum_and_strenum(self) -> None:
        for member in _State:
            with self.subTest(member=member):
                parsed: _State = parse_enum_value(member.value, "status", _State)
                self.assertIs(parsed, member)
        for member in _TextState:
            with self.subTest(member=member):
                parsed_text: _TextState = parse_enum_value(member.value, "status", _TextState)
                self.assertIs(parsed_text, member)

    def test_names_preserve_member_identity_including_aliases_and_integer_valued_members(self) -> None:
        for name, member in _State.__members__.items():
            with self.subTest(name=name):
                self.assertIs(parse_enum_name(name, "status", _State), member)
        for name, member in _Permission.__members__.items():
            with self.subTest(name=name):
                parsed: _Permission = parse_enum_name(name, "required_permissions[0]", _Permission)
                self.assertIs(parsed, member)
        self.assertIs(parse_enum_value("complete", "status", _State), _State.FINISHED)

    def test_unknown_values_include_field_enum_and_text_and_preserve_value_error_cause(self) -> None:
        for value in ("", "unknown", "READY", "Ready", " ready", "ready ", "FINISHED"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError) as raised:
                    parse_enum_value(value, "previous_status", _State)
                self.assertEqual(str(raised.exception), f"previous_status: unknown _State value {value!r}.")
                self.assertIsInstance(raised.exception.__cause__, ValueError)

    def test_unknown_names_include_index_enum_and_text_and_preserve_key_error_cause(self) -> None:
        for name in ("", "UNKNOWN", "read", "Read", " READ", "READ ", "1"):
            with self.subTest(name=name):
                with self.assertRaises(ValueError) as raised:
                    parse_enum_name(name, "required_permissions[2]", _Permission)
                self.assertEqual(
                    str(raised.exception), f"required_permissions[2]: unknown _Permission name {name!r}."
                )
                self.assertIsInstance(raised.exception.__cause__, KeyError)
                cause = raised.exception.__cause__
                assert isinstance(cause, KeyError)
                self.assertEqual(cause.args, (name,))

    def test_names_do_not_fall_back_to_string_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "status: unknown _State name 'ready'"):
            parse_enum_name("ready", "status", _State)

    def test_values_do_not_coerce_numeric_strings_to_integer_enum_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "permission: unknown _Permission value '1'"):
            parse_enum_value("1", "permission", _Permission)

    def test_both_parsers_reject_non_strings_with_field_context_before_enum_lookup(self) -> None:
        values: tuple[object, ...] = (
            None, True, False, 1, 1.0, [], {}, ("READY",), b"READY", _State.READY,
        )
        for parser in (parse_enum_value, parse_enum_name):
            for value in values:
                with self.subTest(parser=parser.__name__, value=value):
                    with self.assertRaises(TypeError) as raised:
                        parser(value, "reasons[1]", _State)
                    self.assertEqual(
                        str(raised.exception), f"reasons[1]: expected str, got {type(value).__name__}"
                    )
                    self.assertIsNone(raised.exception.__cause__)


if __name__ == "__main__":
    unittest.main()
