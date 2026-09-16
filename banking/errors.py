from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.views import exception_handler as drf_exception_handler


class BankingError(APIException):
    """Base for domain errors"""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "The request could not be processed."
    default_code = "banking_error"

    def __init__(self, detail=None, details=None):
        super().__init__(detail)
        self.details = details or {}



class AccountNotFound(BankingError):
    status_code = status.HTTP_404_NOT_FOUND  # 404 "no such resource"
    default_detail = "No account exists with that id."
    default_code = "account_not_found"

class CustomerNotFound(BankingError):
    status_code = status.HTTP_404_NOT_FOUND  # 404 "no such resource"
    default_detail = "No customer exists with that id."
    default_code = "customer_not_found"

class CustomerHasAccounts(BankingError):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Close the customer's accounts before deleting the customer."
    default_code = "customer_has_accounts"


class InsufficientFunds(BankingError):
    status_code = status.HTTP_409_CONFLICT  # 409 request conflicts with current state
    default_detail = "The account does not hold enough funds for this operation."
    default_code = "insufficient_funds"


class AccountNotEmpty(BankingError):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "An account must have a zero balance before it can be closed."
    default_code = "account_not_empty"


def api_exception_handler(exc, context):
    """For every exception raised it returns {"error": {"code", "message", "details"}}."""

    if isinstance(exc, Http404):
        exc = NotFound()

    response = drf_exception_handler(exc, context)
    if response is None:
        return None # "not a DRF-recognized exception", let it propagate as a 500 error

    if isinstance(exc, ValidationError):
        details = exc.detail
        if not isinstance(details, dict):
            details = {"non_field_errors": details}
        error = {
            "code": "validation_error",
            "message": "The request payload is invalid.",
            "details": details,
        }
    else:
        error = {
            "code": getattr(exc, "default_code", "error"),
            "message": str(exc.detail),
        }
        details = getattr(exc, "details", None)
        if details:
            error["details"] = details

    response.data = {"error": error}
    return response
