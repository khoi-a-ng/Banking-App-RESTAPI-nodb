from decimal import Decimal

from rest_framework import serializers


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
    created_at = serializers.DateTimeField(read_only=True)
    # Who did it. A customer sees their own email on their own transactions;
    # the case that matters is by_staff -- an admin moved this money.
    performed_by = serializers.SerializerMethodField()
    by_staff = serializers.SerializerMethodField()

    def get_performed_by(self, txn):
        return txn.performed_by.email if txn.performed_by_id else None

    def get_by_staff(self, txn):
        return bool(txn.performed_by_id and txn.performed_by.is_staff)


class ActivitySerializer(TransactionSerializer):
    """A transaction plus whose account it touched -- for feeds that span
    many customers, where an account id alone means nothing to the reader."""

    customer_name = serializers.CharField(source="account.customer.name", read_only=True)


class OpenAccountSerializer(serializers.Serializer):
    initial_deposit = money_field(
        required=False, default=Decimal("0.00"), min_value=Decimal("0.00")
    )

class CustomerSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(max_length=100, trim_whitespace=True)
    email = serializers.EmailField(max_length=100, trim_whitespace=True)
    created_at = serializers.DateTimeField(read_only=True)

class SignupSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, trim_whitespace=True)
    email = serializers.EmailField(max_length=100, trim_whitespace=True)
    password = serializers.CharField(min_length=8, write_only=True)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=100, trim_whitespace=True)
    password = serializers.CharField(write_only=True)


class LogoutSerializer(serializers.Serializer):

    refresh = serializers.CharField()


class AmountSerializer(serializers.Serializer):
    amount = money_field(min_value=Decimal("0.01"))
    description = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=200
    )
