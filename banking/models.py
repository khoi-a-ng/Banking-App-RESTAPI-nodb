from django.contrib.auth.models import User
from django.db import models


class TransactionType(models.TextChoices):

    DEPOSIT = "deposit", "Deposit"
    WITHDRAWAL = "withdrawal", "Withdrawal"


class Customer(models.Model): 

    customer_id = models.BigAutoField(primary_key=True) # bigautofield is just an 64-bit incrementer
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="customer",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["customer_id"]

    def __str__(self):
        return f"{self.name} <{self.email}>"


class Account(models.Model):
    id = models.BigAutoField(primary_key=True)
    customer = models.ForeignKey( # DB enforces referenced customer to exist first
        Customer,
        on_delete=models.PROTECT,
        related_name="accounts",
    )
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"Account {self.id} (customer {self.customer_id})"


class Transaction(models.Model):
    txn_id = models.BigAutoField(primary_key=True)
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE, # CASCADE means DB now del its txn too, replaces manual filter
        related_name="transactions",
    )
    type = models.CharField(max_length=20, choices=TransactionType.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    balance_after = models.DecimalField(max_digits=14, decimal_places=2)
    description = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-txn_id"] # (-) means sort by descending as default is increasing. Newest 1st

    def __str__(self):
        return f"{self.type} {self.amount} on account {self.account_id}"
