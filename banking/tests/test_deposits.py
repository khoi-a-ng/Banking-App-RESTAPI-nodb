from banking.tests.base import BankingAPITestCase


class DepositTests(BankingAPITestCase):
    def setUp(self):
        super().setUp()
        self.account = self.create_account()

    def test_deposit_increases_the_balance(self):
        response = self.deposit(self.account["id"], "100.00")

        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body["account"]["balance"], 100.00)
        self.assertEqual(self.get_account(self.account["id"])["balance"], 100.00)

    def test_deposit_returns_the_created_transaction(self):
        response = self.deposit(self.account["id"], "75.25", description="Paycheck")

        transaction = response.json()["transaction"]
        self.assertEqual(transaction["type"], "deposit")
        self.assertEqual(transaction["amount"], 75.25)
        self.assertEqual(transaction["balance_after"], 75.25)
        self.assertEqual(transaction["account_id"], self.account["id"])
        self.assertEqual(transaction["description"], "Paycheck")
        self.assertIsNone(transaction["related_account_id"])

    def test_deposits_accumulate(self):
        self.deposit(self.account["id"], "10.00")
        self.deposit(self.account["id"], "0.50")
        response = self.deposit(self.account["id"], "1.25")

        self.assertEqual(response.json()["account"]["balance"], 11.75)

    def test_deposit_is_recorded_in_the_transaction_history(self):
        self.deposit(self.account["id"], "10.00")
        self.deposit(self.account["id"], "20.00")

        results = self.client.get(
            f"/api/accounts/{self.account['id']}/transactions/"
        ).json()["results"]

        self.assertEqual(len(results), 2)

    def test_deposit_rejects_zero(self):
        response = self.deposit(self.account["id"], "0")

        self.assertErrorCode(response, 400, "validation_error")
        self.assertEqual(self.get_account(self.account["id"])["balance"], 0)

    def test_deposit_rejects_negative_amounts(self):
        response = self.deposit(self.account["id"], "-5.00")

        self.assertErrorCode(response, 400, "validation_error")

    def test_deposit_requires_an_amount(self):
        response = self.client.post(
            f"/api/accounts/{self.account['id']}/deposit/", {}, format="json"
        )

        error = self.assertErrorCode(response, 400, "validation_error")
        self.assertIn("amount", error["details"])

    def test_deposit_rejects_non_numeric_amounts(self):
        response = self.deposit(self.account["id"], "many dollars")

        self.assertErrorCode(response, 400, "validation_error")

    def test_deposit_rejects_fractions_of_a_cent(self):
        response = self.deposit(self.account["id"], "10.005")

        self.assertErrorCode(response, 400, "validation_error")

    def test_deposit_to_unknown_account_returns_404(self):
        response = self.deposit(9999, "10.00")

        self.assertErrorCode(response, 404, "account_not_found")

    def test_deposit_does_not_affect_other_accounts(self):
        other = self.create_account(initial_deposit="30.00")

        self.deposit(self.account["id"], "10.00")

        self.assertEqual(self.get_account(other["id"])["balance"], 30.00)

    def test_failed_deposit_records_no_transaction(self):
        self.deposit(self.account["id"], "-5.00")

        results = self.client.get(
            f"/api/accounts/{self.account['id']}/transactions/"
        ).json()["results"]

        self.assertEqual(results, [])
