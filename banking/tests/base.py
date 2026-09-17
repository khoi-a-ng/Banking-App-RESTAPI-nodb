from django.test import TestCase
from rest_framework.test import APIClient


class BankingAPITestCase(TestCase):
    """Base case for the API tests.

    TestCase (rather than SimpleTestCase) because there is a real database
    now: Django builds a throwaway test database, then wraps each test in a
    transaction and rolls it back afterwards. That rollback is what isolates
    one test from the next, so nothing has to be deleted by hand -- and the
    tests never touch the real Supabase data.
    """

    def setUp(self):
        self.client = APIClient()

    def create_customer(self, name="Ada Lovelace", email=None):
        payload = {"name": name, "email": email or f"{name.split()[0].lower()}@example.com"}
        response = self.client.post("/api/customers/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()

    def create_account(self, customer_id=None, initial_deposit=None):
        # Accounts now require an owning customer, so make one on the fly
        # unless the test passed a specific customer_id in.
        if customer_id is None:
            customer_id = self.create_customer()["customer_id"]
        payload = {"customer_id": customer_id}
        if initial_deposit is not None:
            payload["initial_deposit"] = initial_deposit
        response = self.client.post("/api/accounts/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()

    def get_account(self, account_id):
        response = self.client.get(f"/api/accounts/{account_id}/")
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def deposit(self, account_id, amount, **extra):
        return self.client.post(
            f"/api/accounts/{account_id}/deposit/",
            {"amount": amount, **extra},
            format="json",
        )

    def withdraw(self, account_id, amount, **extra):
        return self.client.post(
            f"/api/accounts/{account_id}/withdraw/",
            {"amount": amount, **extra},
            format="json",
        )

    def assertErrorCode(self, response, status_code, code):
        self.assertEqual(response.status_code, status_code, response.content)
        body = response.json()
        self.assertIn("error", body)
        self.assertEqual(body["error"]["code"], code, response.content)
        return body["error"]
