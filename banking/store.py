from decimal import Decimal

from django.db import transaction

from banking.errors import (
    AccountNotEmpty,
    AccountNotFound,
    CustomerHasAccounts,
    CustomerNotFound,
    InsufficientFunds,
)
from banking.models import Account, Customer, Transaction, TransactionType

CENTS = Decimal("0.01")
ZERO = Decimal("0.00")


def money(value) -> Decimal:
    return Decimal(value).quantize(CENTS)


class Bank:

    def get_customer(self, customer_id) -> Customer:
        try:
            # .get(pk=...) runs SELECT ... WHERE customer_id = x,
            return Customer.objects.get(pk=int(customer_id))
        except (Customer.DoesNotExist, TypeError, ValueError):
            raise CustomerNotFound()

    def get_account(self, account_id) -> Account:
        try:
            return Account.objects.get(pk=int(account_id))
        except (Account.DoesNotExist, TypeError, ValueError):
            raise AccountNotFound()

    def list_customers(self):
        return Customer.objects.all()

    def list_accounts(self):
        return Account.objects.all()

    def list_accounts_for_customer(self, customer_id):
        customer = self.get_customer(customer_id)
        return customer.accounts.all()

    def list_transactions(self, account_id):
        account = self.get_account(account_id)
        return account.transactions.all()


    def create_customer(self, name: str, email: str) -> Customer:
        return Customer.objects.create(name=name, email=email)

    def delete_customer(self, customer_id) -> None:
        with transaction.atomic():
            customer = self.get_customer(customer_id)
            if customer.accounts.exists():
                raise CustomerHasAccounts()
            customer.delete()

    def open_account(self, customer_id, initial_deposit: Decimal = ZERO) -> Account:
        # atomic() = "all of this succeeds, or none of it does"
        with transaction.atomic():
            customer = self.get_customer(customer_id)
            account = Account.objects.create(customer=customer, balance=ZERO)

            if money(initial_deposit) > ZERO:
                self._apply(
                    account,
                    TransactionType.DEPOSIT,
                    money(initial_deposit),
                    "Initial deposit",
                )
            return account

    def close_account(self, account_id, customer_id=None) -> None:
        with transaction.atomic():
            account = self._locked_account(account_id)

            if customer_id is not None: # Checks if customer and acc match
                customer = self.get_customer(customer_id)
                if account.customer_id != customer.customer_id:
                    raise AccountNotFound()

            if account.balance != ZERO:
                raise AccountNotEmpty(details={"balance": account.balance})
            
            account.delete()

    def deposit(self, account_id, amount, description: str = ""):
        with transaction.atomic():
            account = self._locked_account(account_id) 
            txn = self._apply(
                account, TransactionType.DEPOSIT, money(amount), description
            )
            return account, txn

    def withdraw(self, account_id, amount, description: str = ""):
        with transaction.atomic():
            account = self._locked_account(account_id)
            amount = money(amount)
            self._require_funds(account, amount)
            txn = self._apply(
                account, TransactionType.WITHDRAWAL, -amount, description
            )
            return account, txn

    def reset(self) -> None:

        Transaction.objects.all().delete()
        Account.objects.all().delete()
        Customer.objects.all().delete()


    # Basically locks the acc so txn are one at a time thus not prone to race conditions
    def _locked_account(self, account_id) -> Account:

        try:
            return Account.objects.select_for_update().get(pk=int(account_id))
        except (Account.DoesNotExist, TypeError, ValueError):
            raise AccountNotFound()

    def _require_funds(self, account: Account, amount: Decimal) -> None:
        if amount > account.balance:
            raise InsufficientFunds(
                details={"balance": account.balance, "requested": amount}
            )

    def _apply(
        self,
        account: Account,
        type: str,
        delta: Decimal,
        description: str = "",
    ) -> Transaction:
        account.balance = money(account.balance + delta)
        account.save(update_fields=["balance"])

        return Transaction.objects.create(
            account=account,
            type=type,
            amount=abs(delta),
            balance_after=account.balance,
            description=description,
        )


bank = Bank()


def reset() -> None:
    bank.reset()
