"""
Consistent error response format for the whole API.

Every error response looks like:

{
    "error": {
        "code": "validation_error",
        "message": "A short human-readable summary.",
        "details": { ... }   # optional, field-level errors etc.
    }
}
"""

from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework import status
from rest_framework.response import Response


def _code_for_status(status_code):
    return {
        status.HTTP_400_BAD_REQUEST: "validation_error",
        status.HTTP_401_UNAUTHORIZED: "authentication_error",
        status.HTTP_403_FORBIDDEN: "permission_denied",
        status.HTTP_404_NOT_FOUND: "not_found",
        status.HTTP_405_METHOD_NOT_ALLOWED: "method_not_allowed",
        status.HTTP_429_TOO_MANY_REQUESTS: "throttled",
        status.HTTP_500_INTERNAL_SERVER_ERROR: "server_error",
    }.get(status_code, "error")


def custom_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)

    if response is None:
        # Unhandled exception -> don't leak internals, return a generic 500.
        return Response(
            {"error": {"code": "server_error", "message": "An unexpected error occurred."}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    data = response.data
    message = "Request failed."
    details = None

    if isinstance(data, dict):
        # e.g. {"detail": "..."} from most DRF exceptions
        if "detail" in data and len(data) == 1:
            message = str(data["detail"])
        else:
            details = data
            message = "One or more fields failed validation."
    elif isinstance(data, list):
        details = {"non_field_errors": data}
        message = str(data[0]) if data else message

    response.data = {
        "error": {
            "code": _code_for_status(response.status_code),
            "message": message,
            **({"details": details} if details else {}),
        }
    }
    return response
