from decimal import Decimal

from banking.models import Account, Transaction
from banking.tests.base import BankingAPITestCase


class OpenAccountTests(BankingAPITestCase):
    def test_opens_account_with_zero_balance_by_default(self):
        response = self.client.post("/api/accounts/", {}, format="json")

        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body["balance"], 0)
        self.assertIn("id", body)
        self.assertIn("created_at", body)

    def test_account_belongs_to_the_logged_in_customer(self):
        # The client never sends a customer_id — it comes from the token.
        body = self.create_account()

        self.assertEqual(body["customer_id"], self.customer["customer_id"])

    def test_opens_account_with_initial_deposit(self):
        body = self.create_account(initial_deposit="250.50")

        self.assertEqual(body["balance"], 250.50)

    def test_initial_deposit_is_recorded_as_a_transaction(self):
        account = self.create_account(initial_deposit="100.00")

        results = self.client.get(
            f"/api/accounts/{account['id']}/transactions/"
        ).json()["results"]

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["type"], "deposit")
        self.assertEqual(results[0]["balance_after"], 100.00)

    def test_zero_initial_deposit_records_no_transaction(self):
        account = self.create_account(initial_deposit="0")

        results = self.client.get(
            f"/api/accounts/{account['id']}/transactions/"
        ).json()["results"]

        self.assertEqual(results, [])

    def test_negative_initial_deposit_is_rejected(self):
        response = self.client.post(
            "/api/accounts/", {"initial_deposit": "-10.00"}, format="json"
        )

        error = self.assertErrorCode(response, 400, "validation_error")
        self.assertIn("initial_deposit", error["details"])

    def test_initial_deposit_rejects_more_than_two_decimal_places(self):
        response = self.client.post(
            "/api/accounts/", {"initial_deposit": "10.001"}, format="json"
        )

        self.assertErrorCode(response, 400, "validation_error")

    def test_one_customer_can_hold_several_accounts(self):
        first = self.create_account()
        second = self.create_account()

        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(first["customer_id"], second["customer_id"])


class ListAndRetrieveAccountTests(BankingAPITestCase):
    def test_list_is_empty_for_a_new_customer(self):
        response = self.client.get("/api/accounts/")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json(), {"count": 0, "results": []})

    def test_list_returns_only_my_accounts(self):
        mine = self.create_account()
        _, other_token = self.make_other_customer("Jane Doe")

        # Jane opens an account of her own.
        self.authenticate(other_token)
        self.create_account()

        # Back to Nina — she should see exactly one account, hers.
        self.authenticate_as_default()
        body = self.client.get("/api/accounts/").json()

        self.assertEqual(body["count"], 1)
        self.assertEqual(body["results"][0]["id"], mine["id"])

    def test_retrieve_returns_a_single_account(self):
        account = self.create_account(initial_deposit="42.00")

        body = self.get_account(account["id"])

        self.assertEqual(body["id"], account["id"])
        self.assertEqual(body["balance"], 42.00)

    def test_retrieve_unknown_account_returns_404(self):
        response = self.client.get("/api/accounts/9999/")

        self.assertErrorCode(response, 404, "account_not_found")


class AccountOwnershipTests(BankingAPITestCase):
    """Somebody else's account must be indistinguishable from one that
    doesn't exist — otherwise the error code alone leaks which ids are real."""

    def setUp(self):
        super().setUp()
        self.my_account = self.create_account(initial_deposit="100.00")
        _, self.other_token = self.make_other_customer("Bob")
        self.authenticate(self.other_token)  # act as Bob from here on

    def test_cannot_read_another_customers_account(self):
        response = self.client.get(f"/api/accounts/{self.my_account['id']}/")

        self.assertErrorCode(response, 404, "account_not_found")

    def test_cannot_deposit_into_another_customers_account(self):
        response = self.deposit(self.my_account["id"], "50.00")

        self.assertErrorCode(response, 404, "account_not_found")

    def test_cannot_withdraw_from_another_customers_account(self):
        response = self.withdraw(self.my_account["id"], "50.00")

        self.assertErrorCode(response, 404, "account_not_found")

    def test_cannot_read_another_customers_transactions(self):
        response = self.client.get(
            f"/api/accounts/{self.my_account['id']}/transactions/"
        )

        self.assertErrorCode(response, 404, "account_not_found")

    def test_cannot_close_another_customers_account(self):
        response = self.client.delete(f"/api/accounts/{self.my_account['id']}/")

        self.assertErrorCode(response, 404, "account_not_found")

    def test_the_balance_is_untouched_by_a_failed_attempt(self):
        self.withdraw(self.my_account["id"], "100.00")

        self.authenticate_as_default()
        self.assertEqual(self.get_account(self.my_account["id"])["balance"], 100.00)


class CloseAccountTests(BankingAPITestCase):
    def test_empty_account_can_be_closed(self):
        account = self.create_account()

        response = self.client.delete(f"/api/accounts/{account['id']}/")

        self.assertEqual(response.status_code, 204, response.content)

    def test_closed_account_disappears_from_the_list(self):
        account = self.create_account()
        self.client.delete(f"/api/accounts/{account['id']}/")

        self.assertEqual(self.client.get("/api/accounts/").json()["count"], 0)

    def test_account_holding_money_cannot_be_closed(self):
        account = self.create_account(initial_deposit="10.00")

        response = self.client.delete(f"/api/accounts/{account['id']}/")

        self.assertErrorCode(response, 409, "account_not_empty")
        self.assertEqual(self.get_account(account["id"])["balance"], 10.00)

    def test_closing_unknown_account_returns_404(self):
        response = self.client.delete("/api/accounts/9999/")

        self.assertErrorCode(response, 404, "account_not_found")

    def test_closed_account_keeps_its_history(self):
        """Closing must not erase the record of what happened in the account.
        It disappears from the API, but the rows stay."""
        account = self.create_account(initial_deposit="5.00")
        self.withdraw(account["id"], "5.00")

        self.client.delete(f"/api/accounts/{account['id']}/")

        self.assertEqual(
            Transaction.objects.filter(account_id=account["id"]).count(), 2
        )
        self.assertIsNotNone(Account.objects.get(pk=account["id"]).closed_at)


class AdminAccountAccessTests(BankingAPITestCase):
    """Staff can act on any account. Ownership checks are for customers."""

    def setUp(self):
        super().setUp()
        self.account = self.create_account(initial_deposit="100.00")  # Nina's
        self.admin, token = self.make_admin()
        self.authenticate(token)

    def test_admin_can_read_any_account(self):
        self.assertEqual(self.get_account(self.account["id"])["balance"], 100.00)

    def test_admin_can_read_any_accounts_transactions(self):
        response = self.client.get(f"/api/accounts/{self.account['id']}/transactions/")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["count"], 1)

    def test_admin_can_deposit_into_any_account(self):
        response = self.deposit(self.account["id"], "25.00", description="Correction")

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["account"]["balance"], 125.00)

    def test_admin_can_withdraw_from_any_account(self):
        response = self.withdraw(self.account["id"], "40.00")

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["account"]["balance"], 60.00)

    def test_admin_can_open_an_account_for_a_customer(self):
        response = self.client.post(
            f"/api/customers/{self.customer['customer_id']}/accounts/",
            {"initial_deposit": "10.00"},
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["customer_id"], self.customer["customer_id"])
        self.assertEqual(response.json()["balance"], 10.00)

    def test_admin_closing_an_account_with_money_disburses_it_first(self):
        """A customer can't close an account holding money. Staff can -- but
        the balance has to leave through a recorded withdrawal, never just
        vanish."""
        response = self.client.delete(f"/api/accounts/{self.account['id']}/")
        self.assertEqual(response.status_code, 204, response.content)

        # Gone from the API...
        self.assertEqual(
            self.client.get(f"/api/accounts/{self.account['id']}/").status_code, 404
        )

        # ...but the row survives, emptied by a withdrawal the admin is named on.
        account = Account.objects.get(pk=self.account["id"])
        self.assertIsNotNone(account.closed_at)
        self.assertEqual(account.balance, Decimal("0.00"))
        disbursement = account.transactions.first()  # newest first
        self.assertEqual(disbursement.type, "withdrawal")
        self.assertEqual(disbursement.amount, Decimal("100.00"))
        self.assertEqual(disbursement.performed_by, self.admin)
