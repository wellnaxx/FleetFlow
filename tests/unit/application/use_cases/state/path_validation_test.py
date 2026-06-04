import unittest

from src.application.exceptions.application_errors import ValidationError
from src.application.use_cases.state.path_validation import validate_world_state_path


class ValidateWorldStatePathShould(unittest.TestCase):
    def test_accepts_non_empty_path(self) -> None:
        self.assertEqual(validate_world_state_path("snapshot.json"), "snapshot.json")

    def test_returns_stripped_path(self) -> None:
        self.assertEqual(validate_world_state_path("  snapshot.json  "), "snapshot.json")

    def test_rejects_empty_path(self) -> None:
        with self.assertRaises(ValidationError) as ctx:
            validate_world_state_path("")

        self.assertIn("World state snapshot path is required.", str(ctx.exception))

    def test_rejects_whitespace_only_path(self) -> None:
        with self.assertRaises(ValidationError) as ctx:
            validate_world_state_path("   ")

        self.assertIn("World state snapshot path is required.", str(ctx.exception))
