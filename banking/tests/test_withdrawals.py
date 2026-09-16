from banking.tests.base import BankingAPITestCase


class WithdrawalTests(BankingAPITestCase):
    def setUp(self):
        super().setUp()
        self.account = self.create_account(initial_deposit="100.00")

    def test_withdrawal_decreases_the_balance(self):
        response = self.withdraw(self.account["id"], "30.00")

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["account"]["balance"], 70.00)
        self.assertEqual(self.get_account(self.account["id"])["balance"], 70.00)

    def test_withdrawal_returns_the_created_transaction(self):
        response = self.withdraw(self.account["id"], "25.50", description="Rent")

        transaction = response.json()["transaction"]
        self.assertEqual(transaction["type"], "withdrawal")
        self.assertEqual(transaction["amount"], 25.50)
        self.assertEqual(transaction["balance_after"], 74.50)
        self.assertEqual(transaction["description"], "Rent")

    def test_the_whole_balance_can_be_withdrawn(self):
        response = self.withdraw(self.account["id"], "100.00")

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["account"]["balance"], 0)

    def test_overdrawing_is_rejected(self):
        response = self.withdraw(self.account["id"], "100.01")

        error = self.assertErrorCode(response, 409, "insufficient_funds")
        self.assertIn("balance", error["details"])
        self.assertEqual(error["details"]["balance"], 100.00)
        self.assertEqual(error["details"]["requested"], 100.01)

    def test_overdrawing_leaves_the_balance_untouched(self):
        self.withdraw(self.account["id"], "500.00")

        self.assertEqual(self.get_account(self.account["id"])["balance"], 100.00)

    def test_overdrawing_records_no_transaction(self):
        self.withdraw(self.account["id"], "500.00")

        results = self.client.get(
            f"/api/accounts/{self.account['id']}/transactions/"
        ).json()["results"]

        self.assertEqual([t["type"] for t in results], ["deposit"])

    def test_withdrawal_rejects_zero(self):
        response = self.withdraw(self.account["id"], "0")

        self.assertErrorCode(response, 400, "validation_error")

    def test_withdrawal_rejects_negative_amounts(self):
        response = self.withdraw(self.account["id"], "-5.00")

        self.assertErrorCode(response, 400, "validation_error")
        self.assertEqual(self.get_account(self.account["id"])["balance"], 100.00)

    def test_withdrawal_requires_an_amount(self):
        response = self.client.post(
            f"/api/accounts/{self.account['id']}/withdraw/", {}, format="json"
        )

        error = self.assertErrorCode(response, 400, "validation_error")
        self.assertIn("amount", error["details"])

    def test_withdrawal_from_unknown_account_returns_404(self):
        response = self.withdraw(9999, "10.00")

        self.assertErrorCode(response, 404, "account_not_found")

    def test_withdrawal_does_not_affect_other_accounts(self):
        other = self.create_account(initial_deposit="30.00")

        self.withdraw(self.account["id"], "10.00")

        self.assertEqual(self.get_account(other["id"])["balance"], 30.00)
