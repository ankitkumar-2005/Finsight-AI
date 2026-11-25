import unittest

from finsight.transactions import _valid_data
from finsight.calculations import budget_progress, savings_percentage
from finsight.reports import report_period
from datetime import date, timedelta


class TransactionValidationTests(unittest.TestCase):
    def setUp(self):
        self.valid = {
            "title": "Salary",
            "amount": "1250.50",
            "category": "Income",
            "type": "income",
            "payment_method": "bank_transfer",
            "description": "Monthly pay",
            "transaction_date": "2026-10-31",
        }

    def test_valid_transaction_is_normalized(self):
        errors, values = _valid_data(self.valid)
        self.assertEqual(errors, {})
        self.assertEqual(str(values["amount"]), "1250.50")
        self.assertEqual(values["title"], "Salary")

    def test_invalid_amount_type_payment_date_and_description_are_reported(self):
        invalid = {**self.valid, "amount": "NaN", "type": "transfer", "payment_method": "bank", "transaction_date": "2026-02-31", "description": "x" * 501}
        errors, _ = _valid_data(invalid)
        self.assertEqual(set(errors), {"amount", "type", "payment_method", "transaction_date", "description"})

    def test_unexpected_json_types_are_validation_errors_not_server_errors(self):
        invalid = {**self.valid, "type": ["income"], "payment_method": {"name": "cash"}}
        errors, _ = _valid_data(invalid)
        self.assertEqual(set(errors), {"type", "payment_method"})

    def test_budget_thresholds_and_remaining_amount(self):
        self.assertEqual(budget_progress("100", "79.99")["alert_level"], "on_track")
        warning = budget_progress("100", "80")
        self.assertEqual(warning["alert_level"], "warning")
        self.assertEqual(warning["remaining"], 20.0)
        self.assertEqual(budget_progress("100", "100")["alert_level"], "reached")
        exceeded = budget_progress("100", "100.01")
        self.assertEqual(exceeded["alert_level"], "exceeded")
        self.assertEqual(exceeded["remaining"], -0.01)

    def test_savings_percentage_uses_net_amount(self):
        self.assertEqual(savings_percentage("1000", "100.01"), 90.0)
        self.assertEqual(savings_percentage("0", "20"), 0.0)

    def test_report_ranges_validate_custom_dates(self):
        today = date.today()
        start, end, error = report_period({"range": "last_7_days"})
        self.assertIsNone(error)
        self.assertEqual((today - start).days, 6)
        start, end, error = report_period({"range": "custom", "date_from": today.isoformat(), "date_to": today.isoformat()})
        self.assertIsNone(error)
        self.assertEqual(start, end)
        self.assertIsNotNone(report_period({"range": "custom", "date_from": today.isoformat(), "date_to": (today - timedelta(days=1)).isoformat()})[2])
        self.assertIsNotNone(report_period({"range": "not-a-range"})[2])


if __name__ == "__main__":
    unittest.main()
