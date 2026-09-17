from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from banking import store
from banking.serializers import (
    AccountSerializer,
    AmountSerializer,
    CustomerSerializer,
    LoginSerializer,
    OpenAccountSerializer,
    SignupSerializer,
    TransactionSerializer,
)

bank = store.bank


def collection(serializer_class, items):
    data = serializer_class(items, many=True).data
    return Response({"count": len(data), "results": data})


def validated(serializer_class, data): # helper, validates and then sends back cleaned vals
    serializer = serializer_class(data=data)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


class SignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        payload = validated(SignupSerializer, request.data)

        if User.objects.filter(username=payload["email"]).exists():
            raise ValidationError({"email": ["An account with that email already exists."]})

        with transaction.atomic():
            user = User.objects.create_user(
                username=payload["email"],
                email=payload["email"],
                password=payload["password"],
            )
            customer = bank.create_customer(
                name=payload["name"], email=payload["email"], user=user
            )
            token = Token.objects.create(user=user)

        return Response(
            {
                "token": token.key,
                "customer": CustomerSerializer(customer).data,
                "is_admin": False, 
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):

    permission_classes = [AllowAny]

    def post(self, request):
        payload = validated(LoginSerializer, request.data)

        existing = User.objects.filter(email__iexact=payload["email"]).first()
        username = existing.username if existing else payload["email"]

        user = authenticate(username=username, password=payload["password"])
        if user is None:
            raise ValidationError({"detail": ["Incorrect email or password."]})

        token, _ = Token.objects.get_or_create(user=user)

        customer = None if user.is_staff else bank.customer_for_user(user)
        return Response(
            {
                "token": token.key,
                "customer": CustomerSerializer(customer).data if customer else None,
                "is_admin": user.is_staff,
            }
        )


class LogoutView(APIView):

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):

    def get(self, request):
        if request.user.is_staff:
            return Response(
                {"customer": None, "accounts": [], "total_balance": 0, "is_admin": True}
            )

        customer = bank.customer_for_user(request.user)
        accounts = bank.list_accounts_for_customer(customer.customer_id)
        total = sum(a.balance for a in accounts)
        return Response(
            {
                "customer": CustomerSerializer(customer).data,
                "accounts": AccountSerializer(accounts, many=True).data,
                "total_balance": total,
                "is_admin": False,
            }
        )


class ApiRootView(APIView):

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                "service": "Banking API",
                "endpoints": {
                    "list_customers": "GET /api/customers/",
                    "create_customer": "POST /api/customers/",
                    "retrieve_customer": "GET /api/customers/{id}/",
                    "delete_customer": "DELETE /api/customers/{id}/",
                    "customer_accounts": "GET /api/customers/{id}/accounts/",
                    "list_accounts": "GET /api/accounts/",
                    "open_account": "POST /api/accounts/",
                    "retrieve_account": "GET /api/accounts/{id}/",
                    "close_account": "DELETE /api/accounts/{id}/",
                    "deposit": "POST /api/accounts/{id}/deposit/",
                    "withdraw": "POST /api/accounts/{id}/withdraw/",
                    "account_transactions": "GET /api/accounts/{id}/transactions/",
                },
            }
        )


class AccountListView(APIView):

    def get(self, request):
        customer = bank.customer_for_user(request.user)
        return collection(
            AccountSerializer, bank.list_accounts_for_customer(customer.customer_id)
        )

    def post(self, request):
        payload = validated(OpenAccountSerializer, request.data)
        customer = bank.customer_for_user(request.user)
        account = bank.open_account(
            customer_id=customer.customer_id,
            initial_deposit=payload["initial_deposit"],
        )

        return Response(
            AccountSerializer(account).data, status=status.HTTP_201_CREATED
        )


class AccountDetailView(APIView):


    def get(self, request, pk):
        customer = bank.customer_for_user(request.user)
        return Response(
            AccountSerializer(bank.get_owned_account(pk, customer.customer_id)).data
        )

    def delete(self, request, pk):
        customer = bank.customer_for_user(request.user)
        bank.close_account(pk, customer_id=customer.customer_id)
        return Response(status=status.HTTP_204_NO_CONTENT) # Delete succeeded


class CustomerListView(APIView):

    permission_classes = [IsAdminUser]

    def get(self, request): # List all customer in sys
        return collection(CustomerSerializer, bank.list_customers())


class CustomerDetailView(APIView):

    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        return Response(CustomerSerializer(bank.get_customer(pk)).data)

    def delete(self, request, pk):
        bank.delete_customer(pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CustomerAccountsView(APIView):

    permission_classes = [IsAdminUser]

    def get(self, request, pk): # Lists all acc belonging to customer
        return collection(AccountSerializer, bank.list_accounts_for_customer(pk))


class DepositView(APIView):

    def post(self, request, pk):

        customer = bank.customer_for_user(request.user)
        bank.get_owned_account(pk, customer.customer_id) # 404 unless it's theirs
        payload = validated(AmountSerializer, request.data) # validates depo
        account, transaction = bank.deposit(
            pk, payload["amount"], payload["description"]
        )
        return Response(
            {
                "account": AccountSerializer(account).data,
                "transaction": TransactionSerializer(transaction).data,
            },
            status=status.HTTP_201_CREATED,
        )


class WithdrawView(APIView):

    def post(self, request, pk):
        customer = bank.customer_for_user(request.user)
        bank.get_owned_account(pk, customer.customer_id)
        payload = validated(AmountSerializer, request.data)
        account, transaction = bank.withdraw( # store.py will raise err if balance lower than withd
            pk, payload["amount"], payload["description"]
        )
        return Response(
            {
                "account": AccountSerializer(account).data,
                "transaction": TransactionSerializer(transaction).data,
            },
            status=status.HTTP_201_CREATED,
        )


class AccountTransactionsView(APIView):

    def get(self, request, pk): # Checks acc hist
        customer = bank.customer_for_user(request.user)
        bank.get_owned_account(pk, customer.customer_id)
        return collection(TransactionSerializer, bank.list_transactions(account_id=pk))
