from decimal import Decimal

from rest_framework import serializers

from banking.store import TRANSACTION_TYPES


MAX_DIGITS = 14
DECIMAL_PLACES = 2


def money_field(**kwargs): 
    return serializers.DecimalField(
        max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES, **kwargs
    )

# Serializers act as a translator between raw req/resp & python objs so they can be interactable

class AccountSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    customer_id = serializers.IntegerField(read_only=True)
    balance = money_field(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class TransactionSerializer(serializers.Serializer):
    txn_id = serializers.IntegerField(read_only=True)
    account_id = serializers.IntegerField(read_only=True)
    type = serializers.CharField(read_only=True)
    amount = money_field(read_only=True)
    balance_after = money_field(read_only=True)
    description = serializers.CharField(read_only=True)
    related_account_id = serializers.IntegerField(read_only=True, allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)


class OpenAccountSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    initial_deposit = money_field(
        required=False, default=Decimal("0.00"), min_value=Decimal("0.00")
    )

class CustomerSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(max_length=100, trim_whitespace=True)
    email = serializers.EmailField(max_length=100, trim_whitespace=True)
    created_at = serializers.DateTimeField(read_only=True)

class AmountSerializer(serializers.Serializer):
    amount = money_field(min_value=Decimal("0.01"))
    description = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=200
    )


class TransferSerializer(serializers.Serializer):
    from_account = serializers.IntegerField()
    to_account = serializers.IntegerField()
    amount = money_field(min_value=Decimal("0.01"))
    description = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=200
    )


class TransactionFilterSerializer(serializers.Serializer):
    account_id = serializers.IntegerField(required=False)
    type = serializers.ChoiceField(choices=TRANSACTION_TYPES, required=False)
