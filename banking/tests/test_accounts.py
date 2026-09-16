from banking.tests.base import BankingAPITestCase


class CreateAccountTests(BankingAPITestCase):
    def test_creates_account_with_zero_balance_by_default(self):
        customer = self.create_customer("Ada Lovelace")

        response = self.client.post(
            "/api/accounts/", {"customer_id": customer["customer_id"]}, format="json"
        )

        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body["customer_id"], customer["customer_id"])
        self.assertEqual(body["balance"], 0)
        self.assertIn("id", body)
        self.assertIn("created_at", body)

    def test_account_does_not_carry_an_owner_name(self):
        # The holder's name lives on the Customer record only, so it is not
        # duplicated onto the account.
        body = self.create_account()

        self.assertNotIn("owner", body)

    def test_creates_account_with_initial_deposit(self):
        body = self.create_account(initial_deposit="250.50")

        self.assertEqual(body["balance"], 250.50)

    def test_initial_deposit_is_recorded_as_a_transaction(self):
        account = self.create_account(initial_deposit="100.00")

        response = self.client.get(f"/api/accounts/{account['id']}/transactions/")

        self.assertEqual(response.status_code, 200, response.content)
        results = response.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["type"], "deposit")
        self.assertEqual(results[0]["amount"], 100.00)
        self.assertEqual(results[0]["balance_after"], 100.00)

    def test_zero_initial_deposit_records_no_transaction(self):
        account = self.create_account(initial_deposit="0")

        response = self.client.get(f"/api/accounts/{account['id']}/transactions/")

        self.assertEqual(response.json()["results"], [])

    def test_customer_id_is_required(self):
        response = self.client.post("/api/accounts/", {}, format="json")

        error = self.assertErrorCode(response, 400, "validation_error")
        self.assertIn("customer_id", error["details"])

    def test_unknown_customer_is_rejected(self):
        response = self.client.post(
            "/api/accounts/", {"customer_id": 9999}, format="json"
        )

        self.assertErrorCode(response, 404, "customer_not_found")

    def test_non_numeric_customer_id_is_rejected(self):
        response = self.client.post(
            "/api/accounts/", {"customer_id": "abc"}, format="json"
        )

        self.assertErrorCode(response, 400, "validation_error")

    def test_negative_initial_deposit_is_rejected(self):
        customer = self.create_customer()

        response = self.client.post(
            "/api/accounts/",
            {"customer_id": customer["customer_id"], "initial_deposit": "-10.00"},
            format="json",
        )

        error = self.assertErrorCode(response, 400, "validation_error")
        self.assertIn("initial_deposit", error["details"])

    def test_initial_deposit_rejects_more_than_two_decimal_places(self):
        customer = self.create_customer()

        response = self.client.post(
            "/api/accounts/",
            {"customer_id": customer["customer_id"], "initial_deposit": "10.001"},
            format="json",
        )

        self.assertErrorCode(response, 400, "validation_error")

    def test_account_ids_are_unique(self):
        first = self.create_account()
        second = self.create_account()

        self.assertNotEqual(first["id"], second["id"])

    def test_one_customer_can_hold_several_accounts(self):
        customer = self.create_customer()

        first = self.create_account(customer_id=customer["customer_id"])
        second = self.create_account(customer_id=customer["customer_id"])

        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(first["customer_id"], second["customer_id"])

    def test_creating_an_account_does_not_touch_other_accounts(self):
        first = self.create_account(initial_deposit="100.00")
        self.create_account(initial_deposit="5.00")

        self.assertEqual(self.get_account(first["id"])["balance"], 100.00)


class ListAndRetrieveAccountTests(BankingAPITestCase):
    def test_list_is_empty_initially(self):
        response = self.client.get("/api/accounts/")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json(), {"count": 0, "results": []})

    def test_list_returns_created_accounts(self):
        first = self.create_account()
        second = self.create_account()

        body = self.client.get("/api/accounts/").json()

        self.assertEqual(body["count"], 2)
        self.assertEqual(
            [account["id"] for account in body["results"]],
            [first["id"], second["id"]],
        )

    def test_retrieve_returns_a_single_account(self):
        customer = self.create_customer()
        account = self.create_account(
            customer_id=customer["customer_id"], initial_deposit="42.00"
        )

        body = self.get_account(account["id"])

        self.assertEqual(body["id"], account["id"])
        self.assertEqual(body["customer_id"], customer["customer_id"])
        self.assertEqual(body["balance"], 42.00)

    def test_retrieve_unknown_account_returns_404(self):
        response = self.client.get("/api/accounts/9999/")

        self.assertErrorCode(response, 404, "account_not_found")


class CloseAccountTests(BankingAPITestCase):
    def test_empty_account_can_be_closed(self):
        account = self.create_account()

        response = self.client.delete(f"/api/accounts/{account['id']}/")

        self.assertEqual(response.status_code, 204, response.content)

    def test_closed_account_disappears_from_the_list(self):
        account = self.create_account()
        self.client.delete(f"/api/accounts/{account['id']}/")

        body = self.client.get("/api/accounts/").json()

        self.assertEqual(body["count"], 0)

    def test_closed_account_can_no_longer_be_retrieved(self):
        account = self.create_account()
        self.client.delete(f"/api/accounts/{account['id']}/")

        response = self.client.get(f"/api/accounts/{account['id']}/")

        self.assertErrorCode(response, 404, "account_not_found")

    def test_account_holding_money_cannot_be_closed(self):
        account = self.create_account(initial_deposit="10.00")

        response = self.client.delete(f"/api/accounts/{account['id']}/")

        self.assertErrorCode(response, 409, "account_not_empty")
        self.assertEqual(self.get_account(account["id"])["balance"], 10.00)

    def test_closing_unknown_account_returns_404(self):
        response = self.client.delete("/api/accounts/9999/")

        self.assertErrorCode(response, 404, "account_not_found")
