import unittest

from src.models.contact_info import ContactInfo


class ContactInfo_Should(unittest.TestCase):
    def test_name_is_stripped_and_length_checked(self):
        ci = ContactInfo("  Alice  ")
        self.assertEqual(ci.name, "Alice")

    def test_name_too_short_raises(self):
        with self.assertRaises(ValueError):
            ContactInfo("Al")

    def test_name_too_long_raises(self):
        with self.assertRaises(ValueError):
            ContactInfo("A" * 31)

    def test_name_non_string_raises(self):
        with self.assertRaises(ValueError):
            ContactInfo(123)  # type: ignore[arg-type]

    def test_email_is_lowercased_and_stripped(self):
        ci = ContactInfo("Bob", "  BOB.Example+tag@Ex-Ample.COM  ")
        self.assertEqual(ci.email, "bob.example+tag@ex-ample.com")

    def test_email_empty_or_none_becomes_blank(self):
        self.assertEqual(ContactInfo("Bob", "").email, "")
        self.assertEqual(ContactInfo("Bob", None).email, "")  # type: ignore[arg-type]

    def test_email_invalid_formats_raise(self):
        bad_emails = [
            "no-at-symbol",
            "@domain.com",
            "local@",
            "a..b@c.com",
            "local@domain",           # missing TLD dot
            "local@.domain.com",      # empty label
            "local@domain..com",      # empty label
            "local@do_main.com",      # underscore not allowed in domain labels
            "local@-domain.com",      # label starts with hyphen
            "local@domain-.com",      # label ends with hyphen
            "loca l@domain.com",      # space in local
            "local@domain!.com",      # invalid char
        ]
        for e in bad_emails:
            with self.subTest(e=e):
                with self.assertRaises(ValueError):
                    ContactInfo("Bob", e)

    def test_email_local_charclass_allows_specified_symbols(self):
        # Allowed specials in local part per regex
        ok = "a.!#$%&'*+/=?^_`{|}~-z@ex.com"
        ci = ContactInfo("Bob", ok)
        self.assertEqual(ci.email, ok.lower())

    def test_phone_optional_blank(self):
        self.assertEqual(ContactInfo("Carl", phone_number="").phone_number, "")
        self.assertEqual(ContactInfo("Carl", phone_number=None).phone_number, "")  # type: ignore[arg-type]

    def test_phone_must_be_string_of_digits_exactly_10_and_start_04(self):
        with self.assertRaises(ValueError):
            ContactInfo("Carl", phone_number=412345678)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            ContactInfo("Carl", phone_number="04123O5678")  # letter O
        with self.assertRaises(ValueError):
            ContactInfo("Carl", phone_number="041234567")   # 9 digits
        with self.assertRaises(ValueError):
            ContactInfo("Carl", phone_number="04123456789")   # 11 digits
        with self.assertRaises(ValueError):
            ContactInfo("Carl", phone_number="0012345678")  # wrong prefix

    def test_phone_is_stripped_and_kept_as_digits(self):
        ci = ContactInfo("Dana", phone_number="  0412345678  ")
        self.assertEqual(ci.phone_number, "0412345678")

    def test_display_email_and_phone_fallbacks(self):
        ci = ContactInfo("Eve", email="", phone_number="")
        self.assertEqual(ci.display_email(), "No email provided")
        self.assertEqual(ci.display_phone(), "No phone number provided")

        ci2 = ContactInfo("Eve", email="a@b.com", phone_number="0412345678")
        self.assertEqual(ci2.display_email(), "a@b.com")
        self.assertEqual(ci2.display_phone(), "0412345678")

    def test_normalized_phone_passthrough(self):
        ci = ContactInfo("Frank", phone_number="0412345678")
        self.assertEqual(ci.normalized_phone(), "0412345678")

    def test_setting_attributes_after_init_applies_cleaning(self):
        ci = ContactInfo("Grace", email="x@y.com", phone_number="0412345678")
        ci.name = "  Grace Hopper  "
        ci.email = "  GRACE@EXAMPLE.COM  "
        ci.phone_number = "  0411222333 "
        self.assertEqual(ci.name, "Grace Hopper")
        self.assertEqual(ci.email, "grace@example.com")
        self.assertEqual(ci.phone_number, "0411222333")

        # invalid assignment raises
        with self.assertRaises(ValueError):
            ci.email = "bad@domain"  # missing TLD dot
        with self.assertRaises(ValueError):
            ci.phone_number = "0312345678"  # wrong prefix
        with self.assertRaises(ValueError):
            ci.name = "ab"  # too short

