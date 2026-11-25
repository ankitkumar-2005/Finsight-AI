import unittest

from finsight.validation import normalize_email, validate_password, validate_registration


class ValidationTests(unittest.TestCase):
    def test_registration_normalizes_email_and_accepts_valid_data(self):
        self.assertEqual(normalize_email("  PERSON@Example.com "), "person@example.com")
        self.assertEqual(validate_registration({"name": "A User", "email": "PERSON@Example.com", "password": "long-pass-123"}), {})

    def test_registration_reports_invalid_fields(self):
        errors = validate_registration({"name": "", "email": "bad", "password": "short"})
        self.assertEqual(set(errors), {"name", "email", "password"})

    def test_password_length_bounds(self):
        self.assertFalse(validate_password("short"))
        self.assertTrue(validate_password("long-pass-123"))
        self.assertFalse(validate_password("x" * 129))


if __name__ == "__main__":
    unittest.main()
