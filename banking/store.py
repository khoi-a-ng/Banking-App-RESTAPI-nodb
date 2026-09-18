from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone

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

    # isnull filter out closed accounts and deactivated customers.
    def _open_accounts(self):
        return Account.objects.filter(closed_at__isnull=True)

    def _active_customers(self):
        return Customer.objects.filter(deactivated_at__isnull=True)

    def get_customer(self, customer_id) -> Customer:
        try:
            # .get(pk=...) runs SELECT ... WHERE customer_id = x,
            return self._active_customers().get(pk=int(customer_id))
        except (Customer.DoesNotExist, TypeError, ValueError):
            raise CustomerNotFound()

    def get_account(self, account_id) -> Account:
        try:
            return self._open_accounts().get(pk=int(account_id))
        except (Account.DoesNotExist, TypeError, ValueError):
            raise AccountNotFound()

    def list_customers(self):
        return self._active_customers()

    def list_accounts(self):
        return self._open_accounts()

    def list_accounts_for_customer(self, customer_id):
        customer = self.get_customer(customer_id)
        return customer.accounts.filter(closed_at__isnull=True)

    def list_transactions(self, account_id):
        account = self.get_account(account_id)
        return account.transactions.select_related("performed_by")

    def recent_transactions_for_customer(self, customer_id, limit=5):
        return Transaction.objects.filter(
            account__customer_id=int(customer_id),
            account__closed_at__isnull=True,
        ).select_related("performed_by")[:limit]

    def overview(self, recent=8) -> dict:
        totals = self._open_accounts().aggregate(
            count=Count("id"), balance=Sum("balance") # computed in DB
        )
        return { # These are the pill overview you see on admin dashboard
            "customers": self._active_customers().count(),
            "accounts": totals["count"],
            "total_balance": totals["balance"] or ZERO,
            "recent_transactions": Transaction.objects.select_related(
                "account__customer", "performed_by"
            )[:recent],
        }

    def create_customer(self, name: str, email: str, user=None) -> Customer:
        return Customer.objects.create(name=name, email=email, user=user)

    def customer_for_user(self, user) -> Customer:
        try:
            customer = user.customer
        except (Customer.DoesNotExist, AttributeError):
            raise CustomerNotFound()
        if customer.deactivated_at is not None: 
            raise CustomerNotFound()
        return customer

    def get_owned_account(self, account_id, customer_id) -> Account:
        account = self.get_account(account_id)
        if account.customer_id != int(customer_id):
            raise AccountNotFound()
        return account

    def account_for_user(self, account_id, user) -> Account:

        if user.is_staff:
            return self.get_account(account_id)
        customer = self.customer_for_user(user)
        return self.get_owned_account(account_id, customer.customer_id)

    def delete_customer(self, customer_id) -> None:

        with transaction.atomic():
            customer = self.get_customer(customer_id)
            if customer.accounts.filter(closed_at__isnull=True).exists():
                raise CustomerHasAccounts()
            customer.deactivated_at = timezone.now()
            customer.save(update_fields=["deactivated_at"])
            if customer.user_id:
                customer.user.is_active = False
                customer.user.save(update_fields=["is_active"])

    def open_account(
        self, customer_id, initial_deposit: Decimal = ZERO, performed_by=None
    ) -> Account:
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
                    performed_by=performed_by,
                )
            return account

    def close_account(self, account_id, *, actor=None) -> None:

        with transaction.atomic():
            account = self._locked_account(account_id)

            if account.balance != ZERO:
                if actor is not None and actor.is_staff:
                    self._apply(
                        account,
                        TransactionType.WITHDRAWAL,
                        -account.balance,
                        "Balance disbursed on closure",
                        performed_by=actor,
                    )
                else:
                    raise AccountNotEmpty(details={"balance": account.balance})

            account.closed_at = timezone.now()
            account.save(update_fields=["closed_at"])

    def deposit(self, account_id, amount, description: str = "", performed_by=None):
        with transaction.atomic():
            account = self._locked_account(account_id)
            txn = self._apply(
                account,
                TransactionType.DEPOSIT,
                money(amount),
                description,
                performed_by=performed_by,
            )
            return account, txn

    def withdraw(self, account_id, amount, description: str = "", performed_by=None):
        with transaction.atomic():
            account = self._locked_account(account_id)
            amount = money(amount)
            self._require_funds(account, amount)
            txn = self._apply(
                account,
                TransactionType.WITHDRAWAL,
                -amount,
                description,
                performed_by=performed_by,
            )
            return account, txn

    # Basically locks the acc so txn are one at a time thus not prone to race conditions
    def _locked_account(self, account_id) -> Account:
        try:
            return self._open_accounts().select_for_update().get(pk=int(account_id))
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
        performed_by=None,
    ) -> Transaction:
        account.balance = money(account.balance + delta)
        account.save(update_fields=["balance"])

        return Transaction.objects.create(
            account=account,
            type=type,
            amount=abs(delta),
            balance_after=account.balance,
            description=description,
            performed_by=performed_by,
        )


bank = Bank()
