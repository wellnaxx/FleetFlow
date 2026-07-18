import unittest

from src.application.services.auth_normalization import normalize_role, normalize_username
from src.domain.enums.auth import Role


class AuthNormalization_Should(unittest.TestCase):
    def test_normalizes_optional_username(self) -> None:
        self.assertEqual(normalize_username("  Alice  "), "alice")
        self.assertEqual(normalize_username(None), "")

    def test_normalizes_role_enum_and_string(self) -> None:
        self.assertEqual(normalize_role(Role.MANAGER), Role.MANAGER.value)
        self.assertEqual(normalize_role(" employee "), Role.EMPLOYEE.value)

    def test_rejects_invalid_role_type_and_value(self) -> None:
        with self.assertRaises(TypeError):
            normalize_role(1)

        with self.assertRaises(ValueError):
            normalize_role("owner")
