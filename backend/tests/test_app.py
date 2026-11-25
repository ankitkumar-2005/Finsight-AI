import unittest

from finsight import create_app


class AppTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app({"TESTING": True, "SECRET_KEY": "unit-test-secret"}).test_client()

    def test_health_route(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["status"], "ok")

    def test_api_not_found_returns_json(self):
        response = self.client.get("/api/no-such-route")
        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.json)

    def test_private_finance_routes_require_a_session(self):
        for route in ("/api/transactions", "/api/dashboard/summary", "/api/budgets", "/api/analytics", "/api/analytics/export", "/api/ai-insights"):
            with self.subTest(route=route):
                self.assertEqual(self.client.get(route).status_code, 401)


if __name__ == "__main__":
    unittest.main()
