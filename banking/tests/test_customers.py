from banking.tests.base import BankingAPITestCase


class CreateCustomerTests(BankingAPITestCase):
    def test_creates_a_customer(self):
        response = self.client.post(
            "/api/customers/",
            {"name": "Ada Lovelace", "email": "ada@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body["name"], "Ada Lovelace")
        self.assertEqual(body["email"], "ada@example.com")
        self.assertIn("customer_id", body)
        self.assertIn("created_at", body)

    def test_name_and_email_are_required(self):
        response = self.client.post("/api/customers/", {}, format="json")

        error = self.assertErrorCode(response, 400, "validation_error")
        self.assertIn("name", error["details"])
        self.assertIn("email", error["details"])

    def test_malformed_email_is_rejected(self):
        response = self.client.post(
            "/api/customers/",
            {"name": "Ada Lovelace", "email": "not-an-email"},
            format="json",
        )

        error = self.assertErrorCode(response, 400, "validation_error")
        self.assertIn("email", error["details"])

    def test_blank_name_is_rejected(self):
        response = self.client.post(
            "/api/customers/",
            {"name": "   ", "email": "ada@example.com"},
            format="json",
        )

        self.assertErrorCode(response, 400, "validation_error")

    def test_customer_ids_are_unique(self):
        first = self.create_customer("Ada Lovelace")
        second = self.create_customer("Grace Hopper")

        self.assertNotEqual(first["customer_id"], second["customer_id"])


class ListAndRetrieveCustomerTests(BankingAPITestCase):
    def test_list_is_empty_initially(self):
        response = self.client.get("/api/customers/")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json(), {"count": 0, "results": []})

    def test_list_returns_created_customers(self):
        self.create_customer("Ada Lovelace")
        self.create_customer("Grace Hopper")

        body = self.client.get("/api/customers/").json()

        self.assertEqual(body["count"], 2)
        self.assertEqual(
            [customer["name"] for customer in body["results"]],
            ["Ada Lovelace", "Grace Hopper"],
        )

    def test_retrieve_returns_a_single_customer(self):
        customer = self.create_customer("Ada Lovelace")

        response = self.client.get(f"/api/customers/{customer['customer_id']}/")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["name"], "Ada Lovelace")

    def test_retrieve_unknown_customer_returns_404(self):
        response = self.client.get("/api/customers/9999/")

        self.assertErrorCode(response, 404, "customer_not_found")


class CustomerAccountsTests(BankingAPITestCase):
    def test_new_customer_has_no_accounts(self):
        customer = self.create_customer()

        response = self.client.get(
            f"/api/customers/{customer['customer_id']}/accounts/"
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json(), {"count": 0, "results": []})

    def test_lists_only_that_customers_accounts(self):
        ada = self.create_customer("Ada Lovelace")
        grace = self.create_customer("Grace Hopper")
        first = self.create_account(customer_id=ada["customer_id"])
        second = self.create_account(customer_id=ada["customer_id"])
        self.create_account(customer_id=grace["customer_id"])

        body = self.client.get(
            f"/api/customers/{ada['customer_id']}/accounts/"
        ).json()

        self.assertEqual(body["count"], 2)
        self.assertEqual(
            [account["id"] for account in body["results"]],
            [first["id"], second["id"]],
        )

    def test_accounts_of_unknown_customer_returns_404(self):
        response = self.client.get("/api/customers/9999/accounts/")

        self.assertErrorCode(response, 404, "customer_not_found")

    def test_closed_account_leaves_the_customers_list(self):
        customer = self.create_customer()
        account = self.create_account(customer_id=customer["customer_id"])

        self.client.delete(f"/api/accounts/{account['id']}/")

        body = self.client.get(
            f"/api/customers/{customer['customer_id']}/accounts/"
        ).json()
        self.assertEqual(body["count"], 0)


class DeleteCustomerTests(BankingAPITestCase):
    def test_customer_without_accounts_can_be_deleted(self):
        customer = self.create_customer()

        response = self.client.delete(f"/api/customers/{customer['customer_id']}/")

        self.assertEqual(response.status_code, 204, response.content)
        self.assertEqual(self.client.get("/api/customers/").json()["count"], 0)

    def test_customer_holding_accounts_cannot_be_deleted(self):
        customer = self.create_customer()
        self.create_account(customer_id=customer["customer_id"])

        response = self.client.delete(f"/api/customers/{customer['customer_id']}/")

        self.assertErrorCode(response, 409, "customer_has_accounts")

    def test_customer_can_be_deleted_once_their_accounts_are_closed(self):
        customer = self.create_customer()
        account = self.create_account(customer_id=customer["customer_id"])
        self.client.delete(f"/api/accounts/{account['id']}/")

        response = self.client.delete(f"/api/customers/{customer['customer_id']}/")

        self.assertEqual(response.status_code, 204, response.content)

    def test_deleting_unknown_customer_returns_404(self):
        response = self.client.delete("/api/customers/9999/")

        self.assertErrorCode(response, 404, "customer_not_found")
