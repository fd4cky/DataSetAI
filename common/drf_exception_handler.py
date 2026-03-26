from rest_framework.response import Response
from rest_framework.views import exception_handler

from common.exceptions import ServiceError


def custom_exception_handler(exc, context):
    if isinstance(exc, ServiceError):
        return Response(
            {
                "detail": exc.detail,
                "code": exc.code,
            },
            status=exc.status_code,
        )
    return exception_handler(exc, context)
