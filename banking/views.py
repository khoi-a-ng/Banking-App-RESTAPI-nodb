from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from banking import store
from banking.serializers import (
    AccountSerializer,
    ActivitySerializer,
    AmountSerializer,
    CustomerSerializer,
    LoginSerializer,
    LogoutSerializer,
    OpenAccountSerializer,
    SignupSerializer,
    TransactionSerializer,
)

bank = store.bank

# issues an access (short) & refresh(long-lived) token. 
# Access token sent on every API req, refresh token only gives new access tokens
def issue_tokens(user):

    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


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

        return Response(
            {
                **issue_tokens(user),
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

        customer = None if user.is_staff else bank.customer_for_user(user)
        return Response(
            {

                **issue_tokens(user),
                "customer": CustomerSerializer(customer).data if customer else None,
                "email": user.email,
                "is_admin": user.is_staff,
            }
        )

# revokes refresh token, access token alive until exp
class LogoutView(APIView):

    def post(self, request):
        payload = validated(LogoutSerializer, request.data)
        try:
            RefreshToken(payload["refresh"]).blacklist()
        except TokenError:
            pass
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):

    def get(self, request):
        if request.user.is_staff:
            return Response(
                {
                    "customer": None,
                    "email": request.user.email,
                    "accounts": [],
                    "total_balance": 0,
                    "is_admin": True,
                }
            )

        customer = bank.customer_for_user(request.user)
        accounts = bank.list_accounts_for_customer(customer.customer_id)
        total = sum(a.balance for a in accounts)
        return Response(
            {
                "customer": CustomerSerializer(customer).data,
                "email": request.user.email,
                "accounts": AccountSerializer(accounts, many=True).data,
                "total_balance": total,
                "recent_transactions": TransactionSerializer(
                    bank.recent_transactions_for_customer(customer.customer_id),
                    many=True,
                ).data,
                "is_admin": False,
            }
        )

# Access tokens 15min exp, refreshview gets new access tokens using a valid refresh token
# Usually when the exp is over page is 401, this refreshes your page and gets a new access token silently.
class RefreshView(TokenRefreshView):

    permission_classes = [AllowAny]


class ApiRootView(APIView):

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                "service": "Banking API",
                "endpoints": {
                    "signup": "POST /api/auth/signup/",
                    "login": "POST /api/auth/login/",
                    "refresh": "POST /api/auth/refresh/",
                    "logout": "POST /api/auth/logout/",
                    "me": "GET /api/auth/me/",
                    # Everything below here is admin-only.
                    "admin_overview": "GET /api/admin/overview/",
                    "list_customers": "GET /api/customers/",
                    "retrieve_customer": "GET /api/customers/{id}/",
                    "delete_customer": "DELETE /api/customers/{id}/",
                    "customer_accounts": "GET /api/customers/{id}/accounts/",
                    "open_account_for_customer": "POST /api/customers/{id}/accounts/",
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
            performed_by=request.user,
        )

        return Response(
            AccountSerializer(account).data, status=status.HTTP_201_CREATED
        )


class AccountDetailView(APIView):


    def get(self, request, pk):
        return Response(AccountSerializer(bank.account_for_user(pk, request.user)).data)

    def delete(self, request, pk):
        bank.account_for_user(pk, request.user)  # 404 unless it's theirs, or they're staff
        bank.close_account(pk, actor=request.user)
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

    def post(self, request, pk): # Admin opens an account on a customer's behalf
        payload = validated(OpenAccountSerializer, request.data)
        account = bank.open_account(
            customer_id=pk,
            initial_deposit=payload["initial_deposit"],
            performed_by=request.user,
        )
        return Response(AccountSerializer(account).data, status=status.HTTP_201_CREATED)


class AdminOverviewView(APIView):

    permission_classes = [IsAdminUser]

    def get(self, request):
        data = bank.overview()
        data["recent_transactions"] = ActivitySerializer(
            data["recent_transactions"], many=True
        ).data
        return Response(data)


class DepositView(APIView):

    def post(self, request, pk):

        bank.account_for_user(pk, request.user) # 404 unless it's theirs, or they're staff
        payload = validated(AmountSerializer, request.data) # validates depo
        account, transaction = bank.deposit(
            pk, payload["amount"], payload["description"], performed_by=request.user
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
        bank.account_for_user(pk, request.user)
        payload = validated(AmountSerializer, request.data)
        account, transaction = bank.withdraw( # store.py will raise err if balance lower than withd
            pk, payload["amount"], payload["description"], performed_by=request.user
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
        bank.account_for_user(pk, request.user)
        return collection(TransactionSerializer, bank.list_transactions(account_id=pk))
