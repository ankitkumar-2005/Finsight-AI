import unittest
from datetime import date

from finsight_ai import analyze_transactions


def transaction(day, amount, category="Food", kind="expense", title="Expense", identifier=1):
    return {"id": identifier, "title": title, "amount": amount, "category": category, "type": kind, "transaction_date": day}


class AIAnalysisTests(unittest.TestCase):
    def test_insufficient_monthly_history_does_not_invent_forecast(self):
        result = analyze_transactions([transaction("2026-11-02", 100)], today=date(2026, 11, 25))
        self.assertFalse(result["forecast"]["available"])
        self.assertIn("four distinct months", result["forecast"]["reason"])

    def test_forecast_is_trained_from_monthly_records_and_identifies_limitations(self):
        records = [transaction(f"2026-{month:02}-10", 100 * month) for month in range(1, 5)]
        result = analyze_transactions(records, today=date(2026, 4, 20))
        forecast = result["forecast"]
        self.assertTrue(forecast["available"])
        self.assertEqual(forecast["history_months"], 4)
        self.assertAlmostEqual(forecast["estimated_expenses"], 500.0)
        self.assertEqual(forecast["month"], "2026-05")
        self.assertIn("not guaranteed", forecast["limitation"])

    def test_category_comparison_and_savings_advice_use_actual_period_values(self):
        records = [transaction("2026-10-12", 100, "Shopping"), transaction("2026-11-12", 120, "Shopping"), transaction("2026-11-12", 1000, "Salary", "income")]
        result = analyze_transactions(records, today=date(2026, 11, 25))
        shopping = next(row for row in result["monthly_spending"] if row["category"] == "Shopping")
        self.assertEqual(shopping["change_percent"], 20.0)
        self.assertEqual(result["recommendations"][0]["change_percent"], 20.0)
        self.assertEqual(result["comparison"]["savings_rate_percent"], 88.0)

    def test_unusual_spend_is_explained_and_not_called_fraud(self):
        records = [transaction(f"2026-11-{day:02}", 10, "Travel", identifier=day) for day in range(1, 6)]
        records.append(transaction("2026-11-10", 100, "Travel", title="Large trip", identifier=10))
        result = analyze_transactions(records, today=date(2026, 11, 25))
        self.assertEqual(len(result["unusual_transactions"]), 1)
        self.assertIn("threshold", result["unusual_transactions"][0]["reason"])
        self.assertIn("does not mean fraud", result["unusual_transactions"][0]["notice"])

    def test_invalid_transactions_are_safely_ignored(self):
        result = analyze_transactions([transaction("invalid", "NaN"), transaction("2026-11-03", -50)])
        self.assertEqual(result["transaction_count"], 0)
        self.assertFalse(result["forecast"]["available"])


if __name__ == "__main__":
    unittest.main()
