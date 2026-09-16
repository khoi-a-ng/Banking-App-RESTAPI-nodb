"""In-memory bank.
Stands in database
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from banking.errors import (
    AccountNotEmpty,
    AccountNotFound,
    CustomerHasAccounts,
    CustomerNotFound,
    InsufficientFunds,
    SameAccountTransfer,
)

CENTS = Decimal("0.01")
ZERO = Decimal("0.00")


DEPOSIT = "deposit"
WITHDRAWAL = "withdrawal"
TRANSFER_OUT = "transfer_out"
TRANSFER_IN = "transfer_in"
TRANSACTION_TYPES = (DEPOSIT, WITHDRAWAL, TRANSFER_OUT, TRANSFER_IN)


def money(value) -> Decimal:
    return Decimal(value).quantize(CENTS)


@dataclass
class Account:
    id: int
    customer_id: int  # who owns this account — look up the name via get_customer
    balance: Decimal
    created_at: datetime

@dataclass
class Customer:
    customer_id: int
    name: str
    email: str
    created_at: datetime

@dataclass
class Transaction:
    txn_id: int
    account_id: int
    type: str
    amount: Decimal
    balance_after: Decimal
    created_at: datetime
    description: str = ""
    related_account_id: int | None = None


class InMemoryBank:
    """ a dict of accounts and a list of transactions
    """

    def __init__(self):

        self._lock = threading.RLock() # Thread.Rlock ensures race conditions don't happen
        self.reset()

    # Reset the bank's state when restarts or tests are run
    def reset(self) -> None:
        with self._lock: 
            self._accounts: dict[int, Account] = {} # Auto incrementing account ids, starting at 1
            self._customers: dict[int, Customer] = {} # Auto incrementing customer ids, starting at 1
            self._transactions: list[Transaction] = [] # Append-only transaction log, in chronological order
            self._next_account_id = 1 
            self._next_customer_id = 1 
            self._next_transaction_id = 1

    def get_customer(self, customer_id: int) -> Customer: # Method retrieves customer by id
        with self._lock:
            try:
                return self._customers[int(customer_id)]
            except (KeyError, TypeError, ValueError):
                raise CustomerNotFound()

    def get_account(self, account_id: int) -> Account: # Method retrieves acc by id
        with self._lock: 
            try:
                return self._accounts[int(account_id)]
            except (KeyError, TypeError, ValueError):
                raise AccountNotFound() 

    def list_customers(self) -> list[Customer]:
        with self._lock:
            return [self._customers[key] for key in sorted(self._customers)]

    def list_accounts(self) -> list[Account]: # Method returns all accounts in ascending order by id
        with self._lock:
            return [self._accounts[key] for key in sorted(self._accounts)]

    def create_customer(self, name: str, email: str) -> Customer:
        with self._lock:
            customer = Customer(
                customer_id=self._next_customer_id,
                name=name,
                email=email,
                created_at=datetime.now(timezone.utc),
            )
            self._next_customer_id += 1 # Bc creating a new customer we increment the next customer id
            self._customers[customer.customer_id] = customer
            return customer # return the object so it can be used

    def delete_customer(self, customer_id: int) -> None:
        with self._lock:
            customer = self.get_customer(customer_id)
            # Same idea as "an account must be empty before closing": a
            # customer can't be deleted while accounts still point at them,
            # or those accounts would reference an id that no longer exists.
            if self.list_accounts_for_customer(customer.customer_id):
                raise CustomerHasAccounts()
            del self._customers[customer.customer_id]


    def open_account(self, customer_id: int, initial_deposit: Decimal = ZERO) -> Account: # Method opens a new account
        with self._lock:
            customer = self.get_customer(customer_id) # Validates if customer by using method

            account = Account(
                id=self._next_account_id,
                customer_id=customer.customer_id,
                balance=ZERO,
                created_at=datetime.now(timezone.utc),
            )
            self._next_account_id += 1
            self._accounts[account.id] = account

            if money(initial_deposit) > ZERO: # opening acc and making an initial deposit, if any
                self._apply(account, DEPOSIT, money(initial_deposit), "Initial deposit") 
            return account

    def close_account(self, account_id: int, customer_id: int | None = None) -> None:
        with self._lock:
            account = self.get_account(account_id)
            # Optional ownership check, for a customer-scoped close endpoint.
            # AccountNotFound rather than CustomerNotFound: the customer does
            # exist, they just don't own this account — and answering "not
            # found" avoids telling them which other accounts are real.
            if customer_id is not None:
                customer = self.get_customer(customer_id)
                if account.customer_id != customer.customer_id:
                    raise AccountNotFound()


            if account.balance != ZERO: # Acc needs to be empty b4 closed
                raise AccountNotEmpty(details={"balance": account.balance}) # Throws exception
            del self._accounts[account.id]
            # Remove all transactions for this account from the log. 
            self._transactions = [
                txn for txn in self._transactions if txn.account_id != account.id 
            ]

    def deposit(
        self, account_id: int, amount: Decimal, description: str = ""
    ) -> tuple[Account, Transaction]:
        with self._lock:
            account = self.get_account(account_id) 
            transaction = self._apply(account, DEPOSIT, money(amount), description)
            return account, transaction

    def withdraw(
        self, account_id: int, amount: Decimal, description: str = ""
    ) -> tuple[Account, Transaction]:
        with self._lock:
            account = self.get_account(account_id)
            amount = money(amount)
            self._require_funds(account, amount) 
            transaction = self._apply(account, WITHDRAWAL, -amount, description)
            return account, transaction

    def transfer(
        self,
        from_account_id: int,
        to_account_id: int,
        amount: Decimal,
        description: str = "",
    ) -> tuple[Account, Account, Transaction, Transaction]:
        with self._lock:
            source = self.get_account(from_account_id)
            target = self.get_account(to_account_id)
            if source.id == target.id:
                raise SameAccountTransfer() # cannot transfer to the same account

            amount = money(amount)
            self._require_funds(source, amount)

            outgoing = self._apply(
                source, TRANSFER_OUT, -amount, description, related=target.id
            )
            incoming = self._apply(
                target, TRANSFER_IN, amount, description, related=source.id
            )
            return source, target, outgoing, incoming

    def list_accounts_for_customer(self, customer_id: int) -> list[Account]:
        with self._lock:
            customer = self.get_customer(customer_id)
            # sorted() so this matches list_accounts' ascending-id ordering
            return [
                account
                for account in sorted(self._accounts.values(), key=lambda a: a.id)
                if account.customer_id == customer.customer_id
            ]

    def list_transactions( 
        self, account_id: int | None = None, type: str | None = None
    ) -> list[Transaction]:
        with self._lock:
            transactions = self._transactions
            if account_id is not None: # Filter transactions by account if specified
                account = self.get_account(account_id)
                transactions = [
                    txn for txn in transactions if txn.account_id == account.id
                ]
            if type is not None:
                transactions = [txn for txn in transactions if txn.type == type]
            # Return in reverse chronological order (newest first) 
            return list(reversed(transactions))

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
        related: int | None = None,
    ) -> Transaction:
        """Update the account balance and append a transaction to the log."""
        account.balance = money(account.balance + delta)
        transaction = Transaction(
            txn_id=self._next_transaction_id,
            account_id=account.id,
            type=type,
            amount=abs(delta),
            balance_after=account.balance,
            created_at=datetime.now(timezone.utc),
            description=description,
            related_account_id=related,
        )
        self._next_transaction_id += 1
        self._transactions.append(transaction)
        return transaction


# Where data is usually stored in a database, this API keeps it in memory.
bank = InMemoryBank() # shared instance of the bank, used by views to perform operations


def reset() -> None:
    bank.reset()
