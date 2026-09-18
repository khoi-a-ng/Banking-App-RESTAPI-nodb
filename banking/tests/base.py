from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

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
            # Signup hands back two tokens now. The refresh one is kept so
            # tests that exercise logout/refresh have it to hand.
            self.default_token = body["access"]
            self.default_refresh = body["refresh"]
            self.authenticate(body["access"])
        return body["customer"]

    def authenticate(self, token):
        """Send `Authorization: Bearer <jwt>` on every subsequent request.

        The scheme word changed with the swap to JWT: DRF's TokenAuthentication
        looked for `Token`, simplejwt looks for `Bearer`.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

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
        # Minted directly rather than through the login endpoint, same as the
        # old Token.objects.create() did.
        access = RefreshToken.for_user(user).access_token
        return user, str(access)

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
        return body["customer"], body["access"]

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
