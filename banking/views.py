from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from banking import store
from banking.serializers import (
    AccountSerializer,
    AmountSerializer,
    CustomerSerializer,
    OpenAccountSerializer,
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


class ApiRootView(APIView):

    def get(self, request): 
        return Response(
            {
                "service": "Banking API (in-memory, no database)",
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
                    "reset": "POST /api/reset/",
                },
            }
        )


class AccountListView(APIView):


    def get(self, request): # Lists all acc
        return collection(AccountSerializer, bank.list_accounts())

    def post(self, request): # Creates new acc
        payload = validated(OpenAccountSerializer, request.data)
        account = bank.open_account(
            customer_id=payload["customer_id"],
            initial_deposit=payload["initial_deposit"],
        )

        return Response(
            AccountSerializer(account).data, status=status.HTTP_201_CREATED
        )


class AccountDetailView(APIView):


    def get(self, request, pk):
        return Response(AccountSerializer(bank.get_account(pk)).data)

    def delete(self, request, pk):
        bank.close_account(pk)
        return Response(status=status.HTTP_204_NO_CONTENT) # Delete succeeded

class CustomerListView(APIView):


    def get(self, request): # List all customer in sys
        return collection(CustomerSerializer, bank.list_customers())

    def post(self, request):
        payload = validated(CustomerSerializer, request.data)
        customer = bank.create_customer(
            name=payload["name"], email=payload["email"]
        )
        return Response(
            CustomerSerializer(customer).data, status=status.HTTP_201_CREATED
        )

class CustomerDetailView(APIView):

    def get(self, request, pk):
        return Response(CustomerSerializer(bank.get_customer(pk)).data)

    def delete(self, request, pk):
        bank.delete_customer(pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CustomerAccountsView(APIView):

    def get(self, request, pk): # Lists all acc belonging to customer
        return collection(AccountSerializer, bank.list_accounts_for_customer(pk))


class DepositView(APIView):

    def post(self, request, pk): 

        bank.get_account(pk) # Looks up acc
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
        bank.get_account(pk)
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
        bank.get_account(pk)
        return collection(TransactionSerializer, bank.list_transactions(account_id=pk))


class ResetView(APIView):

    def post(self, request): 
        if not settings.DEBUG:
            raise NotFound()
        bank.reset()
        return Response({"detail": "All accounts and transactions were cleared."})
