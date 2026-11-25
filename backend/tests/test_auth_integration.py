"""Real MySQL integration checks. Set MYSQL_TEST_DATABASE to an empty disposable database."""
import os
import unittest
import uuid
from datetime import date
from datetime import timedelta

import mysql.connector
from werkzeug.security import check_password_hash

from finsight import create_app
from finsight.config import Config


class AuthIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database = os.getenv("MYSQL_TEST_DATABASE")
        if not database:
            raise unittest.SkipTest("Set MYSQL_TEST_DATABASE to an empty disposable MySQL database to run persistence tests.")
        config = {
            "DB_HOST": os.getenv("MYSQL_HOST", Config.DB_HOST),
            "DB_PORT": int(os.getenv("MYSQL_PORT", Config.DB_PORT)),
            "DB_NAME": database,
            "DB_USER": os.getenv("MYSQL_USER", Config.DB_USER),
            "DB_PASSWORD": os.getenv("MYSQL_PASSWORD", Config.DB_PASSWORD),
            "SECRET_KEY": "integration-test-only-secret",
            "DEBUG": True,
            "DEMO_RESET_MODE": True,
            "TESTING": False,
            "CORS_ORIGINS": [],
        }
        cls.app = create_app(config)
        cls.client = cls.app.test_client()
        with mysql.connector.connect(host=config["DB_HOST"], port=config["DB_PORT"], database=database, user=config["DB_USER"], password=config["DB_PASSWORD"]) as conn:
            cursor = conn.cursor()
            cursor.execute("""CREATE TABLE IF NOT EXISTS users (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                full_name VARCHAR(100) NOT NULL,
                email VARCHAR(254) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB""")
            cursor.execute("""CREATE TABLE IF NOT EXISTS financial_profiles (
                user_id BIGINT UNSIGNED NOT NULL PRIMARY KEY,
                currency CHAR(3) NOT NULL DEFAULT 'INR',
                monthly_income DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                savings_goal DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                CONSTRAINT fk_financial_profiles_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB""")
            cursor.execute("""CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT UNSIGNED NOT NULL,
                token_hash CHAR(64) NOT NULL UNIQUE,
                expires_at DATETIME NOT NULL,
                used_at DATETIME NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_password_reset_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                INDEX ix_password_reset_user_expiry (user_id, expires_at)
            ) ENGINE=InnoDB""")
            cursor.execute("""CREATE TABLE IF NOT EXISTS transactions (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT UNSIGNED NOT NULL,
                title VARCHAR(120) NOT NULL,
                amount DECIMAL(12,2) NOT NULL,
                category VARCHAR(60) NOT NULL,
                type ENUM('income','expense') NOT NULL,
                payment_method ENUM('cash','debit_card','credit_card','bank_transfer','digital_wallet','other') NOT NULL,
                description VARCHAR(500) NOT NULL DEFAULT '',
                transaction_date DATE NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                CONSTRAINT fk_transactions_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                INDEX ix_transactions_user_date (user_id, transaction_date),
                INDEX ix_transactions_user_type (user_id, type),
                INDEX ix_transactions_user_category (user_id, category)
            ) ENGINE=InnoDB""")
            cursor.execute("""CREATE TABLE IF NOT EXISTS monthly_budgets (
                user_id BIGINT UNSIGNED NOT NULL,
                category VARCHAR(60) NOT NULL,
                month CHAR(7) NOT NULL,
                amount DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, category, month),
                CONSTRAINT fk_monthly_budgets_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB""")
            cursor.close()

    def test_registration_login_duplicate_logout_profile_isolation_and_persistence(self):
        suffix = uuid.uuid4().hex
        email = f"phase2-{suffix}@example.test"
        password = "FinSight-Valid-123"

        unauthenticated = self.client.get("/api/profile/me")
        self.assertEqual(unauthenticated.status_code, 401)

        registered = self.client.post("/api/auth/register", json={"name": "Phase Two", "email": email.upper(), "password": password})
        self.assertEqual(registered.status_code, 201)
        user_id = registered.json["user"]["id"]
        self.assertEqual(self.client.get("/api/auth/me").status_code, 200)
        with mysql.connector.connect(host=os.getenv("MYSQL_HOST", Config.DB_HOST), port=int(os.getenv("MYSQL_PORT", Config.DB_PORT)), database=os.environ["MYSQL_TEST_DATABASE"], user=os.getenv("MYSQL_USER", Config.DB_USER), password=os.getenv("MYSQL_PASSWORD", Config.DB_PASSWORD)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT password_hash FROM users WHERE id = %s", (user_id,))
            password_hash = cursor.fetchone()[0]
            cursor.close()
        self.assertNotEqual(password_hash, password)
        self.assertTrue(check_password_hash(password_hash, password))

        duplicate = self.client.post("/api/auth/register", json={"name": "Again", "email": email, "password": password})
        self.assertEqual(duplicate.status_code, 409)
        invalid_login = self.client.post("/api/auth/login", json={"email": email, "password": "wrong-password"})
        self.assertEqual(invalid_login.status_code, 401)
        logged_out = self.client.post("/api/auth/logout")
        self.assertEqual(logged_out.status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)

        login = self.client.post("/api/auth/login", json={"email": email, "password": password})
        self.assertEqual(login.status_code, 200)
        save = self.client.put("/api/profile/me", json={"currency": "INR", "monthly_income": 81500, "savings_goal": 12000})
        self.assertEqual(save.status_code, 200)
        second_client = self.app.test_client()
        self.assertEqual(second_client.get("/api/profile/me").status_code, 401)

        self.client.post("/api/auth/logout")
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)
        self.client.post("/api/auth/login", json={"email": email, "password": password})
        self.assertEqual(self.client.get("/api/profile/me").json["profile"]["monthly_income"], 81500.0)

    def test_demo_password_reset_is_one_time_and_does_not_expose_hash(self):
        email = f"reset-{uuid.uuid4().hex}@example.test"
        self.client.post("/api/auth/register", json={"name": "Reset User", "email": email, "password": "Old-password-123"})
        response = self.client.post("/api/auth/forgot-password", json={"email": email})
        self.assertEqual(response.status_code, 200)
        token = response.json["demo_reset_token"]
        reset = self.client.post("/api/auth/reset-password", json={"token": token, "password": "New-password-456"})
        self.assertEqual(reset.status_code, 200)
        reused = self.client.post("/api/auth/reset-password", json={"token": token, "password": "Another-password-789"})
        self.assertEqual(reused.status_code, 400)
        self.client.post("/api/auth/logout")
        self.assertEqual(self.client.post("/api/auth/login", json={"email": email, "password": "New-password-456"}).status_code, 200)

    def test_transaction_crud_filters_aggregates_budgets_and_user_isolation(self):
        suffix = uuid.uuid4().hex
        email = f"transactions-{suffix}@example.test"
        password = "FinSight-Transactions-123"
        self.assertEqual(self.client.post("/api/auth/register", json={"name": "Transaction Owner", "email": email, "password": password}).status_code, 201)
        today = date.today().isoformat()
        expense = self.client.post("/api/transactions", json={"title": "Coffee with client", "amount": "48.50", "category": "Dining", "type": "expense", "payment_method": "credit_card", "description": "Morning meeting", "transaction_date": today})
        income = self.client.post("/api/transactions", json={"title": "Consulting payment", "amount": "200.00", "category": "Contract work", "type": "income", "payment_method": "bank_transfer", "description": "", "transaction_date": today})
        self.assertEqual(expense.status_code, 201)
        self.assertEqual(income.status_code, 201)
        expense_id = expense.json["transaction"]["id"]

        invalid = self.client.post("/api/transactions", json={"title": "Bad amount", "amount": "-4", "category": "Dining", "type": "expense", "payment_method": "cash", "transaction_date": today})
        self.assertEqual(invalid.status_code, 400)
        by_category = self.client.get("/api/transactions?type=expense&category=Dining&date_from=" + today + "&date_to=" + today)
        self.assertEqual([row["id"] for row in by_category.json["transactions"]], [expense_id])
        searched = self.client.get("/api/transactions?q=Morning+meeting&sort_by=amount&sort_dir=asc")
        self.assertEqual(len(searched.json["transactions"]), 1)

        updated = self.client.put(f"/api/transactions/{expense_id}", json={"title": "Client lunch", "amount": "65.25", "category": "Dining", "type": "expense", "payment_method": "cash", "description": "Updated note", "transaction_date": today})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json["transaction"]["amount"], 65.25)
        summary = self.client.get("/api/dashboard/summary")
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.json["totals"]["income"], 200.0)
        self.assertEqual(summary.json["totals"]["expenses"], 65.25)
        self.assertEqual(summary.json["monthly"]["savings"], 134.75)

        month = today[:7]
        budget = self.client.put(f"/api/budgets?month={month}", json={"category": "Dining", "limit": 100})
        self.assertEqual(budget.status_code, 201)
        budget_list = self.client.get(f"/api/budgets?month={month}")
        self.assertEqual(budget_list.json["budgets"][0]["spent"], 65.25)

        second_client = self.app.test_client()
        second_email = f"other-{suffix}@example.test"
        self.assertEqual(second_client.post("/api/auth/register", json={"name": "Other User", "email": second_email, "password": password}).status_code, 201)
        self.assertEqual(second_client.get("/api/transactions").json["transactions"], [])
        self.assertEqual(second_client.put(f"/api/transactions/{expense_id}", json={"title": "Change", "amount": 1, "category": "Dining", "type": "expense", "payment_method": "cash", "transaction_date": today}).status_code, 404)
        self.assertEqual(second_client.delete(f"/api/transactions/{expense_id}").status_code, 404)

        removed = self.client.delete(f"/api/transactions/{income.json['transaction']['id']}")
        self.assertEqual(removed.status_code, 200)
        self.assertEqual(self.client.delete(f"/api/budgets?month={month}", json={"category": "Dining"}).status_code, 200)
        self.assertEqual(len(self.client.get("/api/transactions").json["transactions"]), 1)

    def test_budget_alerts_analytics_filters_and_csv_use_real_transactions(self):
        suffix = uuid.uuid4().hex
        email = f"reports-{suffix}@example.test"
        password = "FinSight-Reports-123"
        self.assertEqual(self.client.post("/api/auth/register", json={"name": "Reports User", "email": email, "password": password}).status_code, 201)
        today = date.today()
        today_text = today.isoformat()
        sample_rows = [
            {"title": "Salary sample", "amount": 1000, "category": "Income", "type": "income", "payment_method": "bank_transfer", "transaction_date": today_text},
            {"title": "Dining sample 80", "amount": 80, "category": "Dining", "type": "expense", "payment_method": "debit_card", "transaction_date": today_text},
            {"title": "Dining sample 20", "amount": 20, "category": "Dining", "type": "expense", "payment_method": "cash", "transaction_date": today_text},
            {"title": "Dining overage", "amount": "0.01", "category": "Dining", "type": "expense", "payment_method": "cash", "transaction_date": today_text},
            {"title": "Older sample", "amount": 25, "category": "Groceries", "type": "expense", "payment_method": "cash", "transaction_date": (today - timedelta(days=10)).isoformat()},
        ]
        for row in sample_rows:
            result = self.client.post("/api/transactions", json=row)
            self.assertEqual(result.status_code, 201)

        month = today_text[:7]
        self.assertEqual(self.client.put(f"/api/budgets?month={month}", json={"category": "Dining", "limit": 100}).status_code, 201)
        budget = self.client.get(f"/api/budgets?month={month}").json["budgets"][0]
        self.assertEqual(budget["alert_level"], "exceeded")
        self.assertEqual(budget["remaining"], -0.01)
        # Exercise the 100%, exactly 80%, and over-budget states against persisted MySQL records.
        transactions = self.client.get("/api/transactions?category=Dining").json["transactions"]
        overage = next(item for item in transactions if item["title"] == "Dining overage")
        self.assertEqual(self.client.delete(f"/api/transactions/{overage['id']}").status_code, 200)
        budget = self.client.get(f"/api/budgets?month={month}").json["budgets"][0]
        self.assertEqual(budget["alert_level"], "reached")
        expense20 = next(item for item in transactions if item["title"] == "Dining sample 20")
        update = self.client.put(f"/api/transactions/{expense20['id']}", json={**expense20, "amount": 0})
        self.assertEqual(update.status_code, 400)
        self.assertEqual(self.client.delete(f"/api/transactions/{expense20['id']}").status_code, 200)
        budget = self.client.get(f"/api/budgets?month={month}").json["budgets"][0]
        self.assertEqual(budget["alert_level"], "warning")
        self.assertEqual(budget["usage_percent"], 80.0)
        self.assertEqual(budget["remaining"], 20.0)
        self.assertEqual(self.client.post("/api/transactions", json={"title":"Dining sample 20.01","amount":"20.01","category":"Dining","type":"expense","payment_method":"cash","transaction_date":today_text}).status_code, 201)
        budget = self.client.get(f"/api/budgets?month={month}").json["budgets"][0]
        self.assertEqual(budget["alert_level"], "exceeded")
        self.assertEqual(budget["remaining"], -0.01)

        current = self.client.get("/api/analytics?range=this_month")
        self.assertEqual(current.status_code, 200)
        self.assertEqual(current.json["summary"]["income"], 1000.0)
        older_in_current_month = (today - timedelta(days=10)).month == today.month
        current_expenses = 125.01 if older_in_current_month else 100.01
        self.assertEqual(current.json["summary"]["expenses"], current_expenses)
        self.assertEqual(current.json["summary"]["savings_percentage"], 87.5 if older_in_current_month else 90.0)
        self.assertEqual(current.json["highest_spending_categories"][0]["category"], "Dining")
        self.assertEqual(current.json["monthly_reports"][-1]["income"], 1000.0)
        last_7 = self.client.get("/api/analytics?range=last_7_days")
        self.assertEqual(last_7.json["summary"]["expenses"], 100.01)
        last_30 = self.client.get("/api/analytics?range=last_30_days")
        self.assertEqual(last_30.json["summary"]["expenses"], 125.01)
        custom = self.client.get(f"/api/analytics?range=custom&date_from={today_text}&date_to={today_text}")
        self.assertEqual(custom.json["summary"]["expenses"], 100.01)
        self.assertEqual(self.client.get("/api/analytics?range=last_month").status_code, 200)
        report = self.client.get("/api/analytics/export?range=this_month")
        self.assertEqual(report.status_code, 200)
        self.assertEqual(report.mimetype, "text/csv")
        self.assertIn("Salary sample", report.get_data(as_text=True))
        self.assertIn("Dining sample 80", report.get_data(as_text=True))

    def test_ai_insights_endpoint_uses_authenticated_users_transactions(self):
        suffix = uuid.uuid4().hex
        password = "FinSight-AI-Reports-123"
        first_email = f"ai-owner-{suffix}@example.test"
        self.assertEqual(self.client.post("/api/auth/register", json={"name": "AI Owner", "email": first_email, "password": password}).status_code, 201)
        today = date.today()
        for index, amount in enumerate((100, 200, 300, 400), start=1):
            record_date = date(today.year, index, 10).isoformat()
            result = self.client.post("/api/transactions", json={"title": f"History {index}", "amount": amount, "category": "Food", "type": "expense", "payment_method": "cash", "transaction_date": record_date})
            self.assertEqual(result.status_code, 201)
        response = self.client.get("/api/ai-insights")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["transaction_count"], 4)
        self.assertTrue(response.json["forecast"]["available"])
        self.assertEqual(response.json["forecast"]["estimated_expenses"], 500.0)

        second_client = self.app.test_client()
        second_email = f"ai-other-{suffix}@example.test"
        self.assertEqual(second_client.post("/api/auth/register", json={"name": "Other AI User", "email": second_email, "password": password}).status_code, 201)
        other_response = second_client.get("/api/ai-insights")
        self.assertEqual(other_response.status_code, 200)
        self.assertEqual(other_response.json["transaction_count"], 0)
        self.assertFalse(other_response.json["forecast"]["available"])


if __name__ == "__main__":
    unittest.main()
