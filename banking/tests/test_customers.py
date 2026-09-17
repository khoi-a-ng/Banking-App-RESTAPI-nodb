from rest_framework.test import APIClient

from banking.tests.base import BankingAPITestCase


class SignupTests(BankingAPITestCase):
    def test_signup_returns_a_token_and_customer(self):
        client = APIClient()

        response = client.post(
            "/api/auth/signup/",
            {"name": "Jane Doe", "email": "jane@example.com", "password": "hunter2pass"},
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertIn("token", body)
        self.assertEqual(body["customer"]["name"], "Jane Doe")
        self.assertEqual(body["customer"]["email"], "jane@example.com")

    def test_signup_never_creates_an_admin(self):
        """The whole point of the admin gate: you cannot self-register as one,
        even by passing the flag explicitly."""
        client = APIClient()

        response = client.post(
            "/api/auth/signup/",
            {
                "name": "Bob",
                "email": "sneaky@example.com",
                "password": "hunter2pass",
                # These are ignored — SignupSerializer has no such fields.
                "is_staff": True,
                "is_superuser": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.content)
        self.assertFalse(response.json()["is_admin"])

        # And the new user really is denied at an admin-only endpoint.
        client.credentials(HTTP_AUTHORIZATION=f"Token {response.json()['token']}")
        self.assertEqual(client.get("/api/customers/").status_code, 403)

    def test_password_is_never_returned(self):
        client = APIClient()

        response = client.post(
            "/api/auth/signup/",
            {"name": "Bob", "email": "bob@example.com", "password": "hunter2pass"},
            format="json",
        )

        self.assertNotIn("password", str(response.content))

    def test_duplicate_email_is_rejected(self):
        client = APIClient()
        payload = {
            "name": "Jane Doe",
            "email": "dupe@example.com",
            "password": "hunter2pass",
        }
        client.post("/api/auth/signup/", payload, format="json")

        response = client.post("/api/auth/signup/", payload, format="json")

        error = self.assertErrorCode(response, 400, "validation_error")
        self.assertIn("email", error["details"])

    def test_short_password_is_rejected(self):
        client = APIClient()

        response = client.post(
            "/api/auth/signup/",
            {"name": "Bob", "email": "short@example.com", "password": "abc"},
            format="json",
        )

        self.assertErrorCode(response, 400, "validation_error")

    def test_malformed_email_is_rejected(self):
        client = APIClient()

        response = client.post(
            "/api/auth/signup/",
            {"name": "Bob", "email": "not-an-email", "password": "hunter2pass"},
            format="json",
        )

        self.assertErrorCode(response, 400, "validation_error")


class LoginTests(BankingAPITestCase):
    def test_login_with_correct_password_returns_a_token(self):
        client = APIClient()
        client.post(
            "/api/auth/signup/",
            {"name": "Jane Doe", "email": "jane2@example.com", "password": "hunter2pass"},
            format="json",
        )

        response = client.post(
            "/api/auth/login/",
            {"email": "jane2@example.com", "password": "hunter2pass"},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn("token", response.json())

    def test_wrong_password_is_rejected(self):
        client = APIClient()
        client.post(
            "/api/auth/signup/",
            {"name": "Bob", "email": "bob2@example.com", "password": "hunter2pass"},
            format="json",
        )

        response = client.post(
            "/api/auth/login/",
            {"email": "bob2@example.com", "password": "wrongpassword"},
            format="json",
        )

        self.assertErrorCode(response, 400, "validation_error")

    def test_unknown_email_gives_the_same_error_as_a_wrong_password(self):
        # Identical responses, so nobody can probe for registered emails.
        client = APIClient()

        response = client.post(
            "/api/auth/login/",
            {"email": "nobody@example.com", "password": "hunter2pass"},
            format="json",
        )

        error = self.assertErrorCode(response, 400, "validation_error")
        self.assertIn("Incorrect email or password", str(error["details"]))


class AuthenticationRequiredTests(BankingAPITestCase):
    def setUp(self):
        super().setUp()
        self.logout()  # drop the Authorization header

    def test_accounts_require_a_token(self):
        self.assertEqual(self.client.get("/api/accounts/").status_code, 401)

    def test_opening_an_account_requires_a_token(self):
        self.assertEqual(
            self.client.post("/api/accounts/", {}, format="json").status_code, 401
        )

    def test_me_requires_a_token(self):
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)

    def test_an_invalid_token_is_rejected(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token not-a-real-token")

        self.assertEqual(self.client.get("/api/accounts/").status_code, 401)


class MeTests(BankingAPITestCase):
    def test_me_returns_the_customer_and_their_totals(self):
        self.create_account(initial_deposit="100.00")
        self.create_account(initial_deposit="50.50")

        body = self.client.get("/api/auth/me/").json()

        self.assertEqual(body["customer"]["customer_id"], self.customer["customer_id"])
        self.assertEqual(len(body["accounts"]), 2)
        self.assertEqual(body["total_balance"], 150.50)
        self.assertFalse(body["is_admin"])


class LogoutTests(BankingAPITestCase):
    def test_logout_invalidates_the_token(self):
        self.assertEqual(self.client.get("/api/accounts/").status_code, 200)

        self.client.post("/api/auth/logout/")

        # The same token no longer works — it was deleted server-side, not
        # just forgotten by the browser.
        self.assertEqual(self.client.get("/api/accounts/").status_code, 401)


class AdminTests(BankingAPITestCase):
    def test_regular_customer_cannot_list_all_customers(self):
        self.assertEqual(self.client.get("/api/customers/").status_code, 403)

    def test_regular_customer_cannot_read_another_customer(self):
        other, _ = self.make_other_customer("Jane Doe")

        response = self.client.get(f"/api/customers/{other['customer_id']}/")

        self.assertEqual(response.status_code, 403)

    def test_regular_customer_cannot_delete_a_customer(self):
        other, _ = self.make_other_customer("Jane Doe")

        response = self.client.delete(f"/api/customers/{other['customer_id']}/")

        self.assertEqual(response.status_code, 403)

    def test_admin_can_list_every_customer(self):
        self.make_other_customer("Jane Doe")
        _, admin_token = self.make_admin()
        self.authenticate(admin_token)

        body = self.client.get("/api/customers/").json()

        names = [c["name"] for c in body["results"]]
        self.assertIn("Nina L", names)
        self.assertIn("Jane Doe", names)

    def test_admin_can_view_any_customers_accounts(self):
        account = self.create_account(initial_deposit="75.00")
        _, admin_token = self.make_admin()
        self.authenticate(admin_token)

        body = self.client.get(
            f"/api/customers/{self.customer['customer_id']}/accounts/"
        ).json()

        self.assertEqual(body["count"], 1)
        self.assertEqual(body["results"][0]["id"], account["id"])

    def test_admin_has_no_customer_record_of_their_own(self):
        _, admin_token = self.make_admin()
        self.authenticate(admin_token)

        body = self.client.get("/api/auth/me/").json()

        self.assertIsNone(body["customer"])
        self.assertTrue(body["is_admin"])

    def test_admin_login_reports_admin_status(self):
        self.make_admin(username="boss", password="adminpass123")
        client = APIClient()

        response = client.post(
            "/api/auth/login/",
            {"email": "boss@example.com", "password": "adminpass123"},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.json()["is_admin"])
        self.assertIsNone(response.json()["customer"])
