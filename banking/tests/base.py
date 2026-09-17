from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from banking.models import Customer


class BankingAPITestCase(TestCase):
    """Base case for the API tests.

    TestCase (not SimpleTestCase) because a real database exists now: Django
    builds a throwaway test database and wraps each test in a transaction it
    rolls back afterwards, which is what isolates one test from the next.

    Every endpoint except signup/login requires a token, so setUp signs a
    default customer in and attaches their credentials to self.client. Tests
    that need a second person or an admin use the helpers below.
    """

    def setUp(self):
        self.client = APIClient()
        self.customer = self.signup()

    def authenticate_as_default(self):
        """Switch back to the customer created in setUp."""
        self.authenticate(self.default_token)

    # --- Auth helpers --------------------------------------------------

    def signup(self, name="Nina L", email=None, password="hunter2pass", login=True):
        """Create a customer through the real signup endpoint."""
        email = email or f"{name.split()[0].lower()}@example.com"
        response = self.client.post(
            "/api/auth/signup/",
            {"name": name, "email": email, "password": password},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        if login:
            self.default_token = body["token"]
            self.authenticate(body["token"])
        return body["customer"]

    def authenticate(self, token):
        """Send `Authorization: Token <key>` on every subsequent request."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")

    def logout(self):
        self.client.credentials()  # clears the header

    def make_admin(self, username="admin", password="adminpass123"):
        """Create a staff user the way `manage.py createsuperuser` would.

        Deliberately NOT via the signup endpoint — that can never produce an
        admin, which is the property the admin tests check.
        """
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password=password,
            is_staff=True,
        )
        token = Token.objects.create(user=user)
        return user, token.key

    def make_other_customer(self, name="Jane Doe"):
        """A second customer, returned with their token, without disturbing
        the client's current login."""
        client = APIClient()
        response = client.post(
            "/api/auth/signup/",
            {
                "name": name,
                "email": f"{name.split()[0].lower()}@example.com",
                "password": "hunter2pass",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        return body["customer"], body["token"]

    # --- Domain helpers ------------------------------------------------

    def create_account(self, initial_deposit=None):
        # No customer_id: the account is opened for whoever the token says
        # you are.
        payload = {}
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
