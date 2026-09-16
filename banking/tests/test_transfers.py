from banking.tests.base import BankingAPITestCase


class TransferTests(BankingAPITestCase):
    def setUp(self):
        super().setUp()
        self.sender = self.create_account(initial_deposit="100.00")
        self.recipient = self.create_account(initial_deposit="20.00")

    def test_transfer_moves_money_between_accounts(self):
        response = self.transfer(self.sender["id"], self.recipient["id"], "30.00")

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(self.get_account(self.sender["id"])["balance"], 70.00)
        self.assertEqual(self.get_account(self.recipient["id"])["balance"], 50.00)

    def test_transfer_returns_both_accounts(self):
        response = self.transfer(self.sender["id"], self.recipient["id"], "30.00")

        body = response.json()
        self.assertEqual(body["from_account"]["balance"], 70.00)
        self.assertEqual(body["to_account"]["balance"], 50.00)

    def test_transfer_records_a_transaction_on_each_side(self):
        response = self.transfer(
            self.sender["id"], self.recipient["id"], "30.00", description="Rent split"
        )

        outgoing, incoming = response.json()["transactions"]
        self.assertEqual(outgoing["type"], "transfer_out")
        self.assertEqual(outgoing["account_id"], self.sender["id"])
        self.assertEqual(outgoing["related_account_id"], self.recipient["id"])
        self.assertEqual(outgoing["balance_after"], 70.00)
        self.assertEqual(outgoing["description"], "Rent split")

        self.assertEqual(incoming["type"], "transfer_in")
        self.assertEqual(incoming["account_id"], self.recipient["id"])
        self.assertEqual(incoming["related_account_id"], self.sender["id"])
        self.assertEqual(incoming["balance_after"], 50.00)

    def test_transfer_shows_up_in_both_histories(self):
        self.transfer(self.sender["id"], self.recipient["id"], "30.00")

        sender_types = [
            t["type"]
            for t in self.client.get(
                f"/api/accounts/{self.sender['id']}/transactions/"
            ).json()["results"]
        ]
        recipient_types = [
            t["type"]
            for t in self.client.get(
                f"/api/accounts/{self.recipient['id']}/transactions/"
            ).json()["results"]
        ]

        self.assertIn("transfer_out", sender_types)
        self.assertIn("transfer_in", recipient_types)

    def test_transfer_larger_than_the_balance_is_rejected(self):
        response = self.transfer(self.sender["id"], self.recipient["id"], "100.01")

        self.assertErrorCode(response, 409, "insufficient_funds")

    def test_rejected_transfer_leaves_both_balances_untouched(self):
        self.transfer(self.sender["id"], self.recipient["id"], "500.00")

        self.assertEqual(self.get_account(self.sender["id"])["balance"], 100.00)
        self.assertEqual(self.get_account(self.recipient["id"])["balance"], 20.00)

    def test_rejected_transfer_records_no_transactions(self):
        self.transfer(self.sender["id"], self.recipient["id"], "500.00")

        body = self.client.get("/api/transactions/").json()

        self.assertEqual([t["type"] for t in body["results"]], ["deposit", "deposit"])

    def test_transfer_to_the_same_account_is_rejected(self):
        response = self.transfer(self.sender["id"], self.sender["id"], "10.00")

        self.assertErrorCode(response, 409, "same_account_transfer")
        self.assertEqual(self.get_account(self.sender["id"])["balance"], 100.00)

    def test_transfer_from_unknown_account_returns_404(self):
        response = self.transfer(9999, self.recipient["id"], "10.00")

        self.assertErrorCode(response, 404, "account_not_found")

    def test_transfer_to_unknown_account_returns_404(self):
        response = self.transfer(self.sender["id"], 9999, "10.00")

        self.assertErrorCode(response, 404, "account_not_found")

    def test_transfer_to_unknown_account_does_not_debit_the_sender(self):
        self.transfer(self.sender["id"], 9999, "10.00")

        self.assertEqual(self.get_account(self.sender["id"])["balance"], 100.00)

    def test_transfer_requires_both_accounts_and_an_amount(self):
        response = self.client.post("/api/transfers/", {}, format="json")

        error = self.assertErrorCode(response, 400, "validation_error")
        self.assertIn("from_account", error["details"])
        self.assertIn("to_account", error["details"])
        self.assertIn("amount", error["details"])

    def test_transfer_rejects_non_positive_amounts(self):
        response = self.transfer(self.sender["id"], self.recipient["id"], "0")

        self.assertErrorCode(response, 400, "validation_error")
