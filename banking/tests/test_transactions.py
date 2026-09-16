from banking.tests.base import BankingAPITestCase


class AccountTransactionTests(BankingAPITestCase):
    def setUp(self):
        super().setUp()
        self.account = self.create_account()

    def test_history_is_empty_for_a_fresh_account(self):
        response = self.client.get(f"/api/accounts/{self.account['id']}/transactions/")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json(), {"count": 0, "results": []})

    def test_history_is_newest_first(self):
        self.deposit(self.account["id"], "10.00", description="first")
        self.deposit(self.account["id"], "20.00", description="second")
        self.withdraw(self.account["id"], "5.00", description="third")

        results = self.client.get(
            f"/api/accounts/{self.account['id']}/transactions/"
        ).json()["results"]

        self.assertEqual(
            [t["description"] for t in results], ["third", "second", "first"]
        )

    def test_history_tracks_the_running_balance(self):
        self.deposit(self.account["id"], "10.00")
        self.deposit(self.account["id"], "20.00")
        self.withdraw(self.account["id"], "5.00")

        results = self.client.get(
            f"/api/accounts/{self.account['id']}/transactions/"
        ).json()["results"]

        self.assertEqual([t["balance_after"] for t in results], [25.00, 30.00, 10.00])

    def test_history_only_contains_this_account(self):
        other = self.create_account()
        self.deposit(self.account["id"], "10.00")
        self.deposit(other["id"], "99.00")

        results = self.client.get(
            f"/api/accounts/{self.account['id']}/transactions/"
        ).json()["results"]

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["amount"], 10.00)

    def test_history_of_unknown_account_returns_404(self):
        response = self.client.get("/api/accounts/9999/transactions/")

        self.assertErrorCode(response, 404, "account_not_found")


class TransactionLedgerTests(BankingAPITestCase):
    def setUp(self):
        super().setUp()
        self.first = self.create_account(initial_deposit="100.00")
        self.second = self.create_account()
        self.withdraw(self.first["id"], "10.00")
        self.transfer(self.first["id"], self.second["id"], "20.00")

    def test_ledger_lists_every_transaction(self):
        body = self.client.get("/api/transactions/").json()

        self.assertEqual(body["count"], 4)

    def test_ledger_can_be_filtered_by_account(self):
        body = self.client.get(
            "/api/transactions/", {"account_id": self.second["id"]}
        ).json()

        self.assertEqual(body["count"], 1)
        self.assertEqual(body["results"][0]["type"], "transfer_in")

    def test_ledger_can_be_filtered_by_type(self):
        body = self.client.get("/api/transactions/", {"type": "withdrawal"}).json()

        self.assertEqual(body["count"], 1)
        self.assertEqual(body["results"][0]["amount"], 10.00)

    def test_ledger_filters_combine(self):
        body = self.client.get(
            "/api/transactions/",
            {"account_id": self.first["id"], "type": "deposit"},
        ).json()

        self.assertEqual(body["count"], 1)

    def test_ledger_rejects_an_unknown_type_filter(self):
        response = self.client.get("/api/transactions/", {"type": "bribe"})

        self.assertErrorCode(response, 400, "validation_error")

    def test_ledger_rejects_a_non_numeric_account_filter(self):
        response = self.client.get("/api/transactions/", {"account_id": "abc"})

        self.assertErrorCode(response, 400, "validation_error")

    def test_ledger_filter_on_unknown_account_returns_404(self):
        response = self.client.get("/api/transactions/", {"account_id": 9999})

        self.assertErrorCode(response, 404, "account_not_found")


class ServiceEndpointTests(BankingAPITestCase):
    def test_root_lists_the_available_endpoints(self):
        response = self.client.get("/api/")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn("endpoints", response.json())

    def test_reset_clears_accounts_and_transactions(self):
        account = self.create_account(initial_deposit="100.00")

        response = self.client.post("/api/reset/")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.client.get("/api/accounts/").json()["count"], 0)
        self.assertEqual(self.client.get("/api/transactions/").json()["count"], 0)
        self.assertEqual(
            self.client.get(f"/api/accounts/{account['id']}/").status_code, 404
        )

    def test_urls_work_without_a_trailing_slash(self):
        customer = self.create_customer()
        response = self.client.post(
            "/api/accounts", {"customer_id": customer["customer_id"]}, format="json"
        )

        self.assertEqual(response.status_code, 201, response.content)
