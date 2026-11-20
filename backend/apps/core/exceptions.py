import logging

from django.db.models import ProtectedError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


def exception_handler(exc, context):
    if isinstance(exc, ProtectedError):
        return Response(
            {"detail": "Bu yozuv boshqa ma'lumotlarda ishlatilgan, uni o'chirib bo'lmaydi. "
                       "O'rniga uni nofaol qiling."},
            status=status.HTTP_409_CONFLICT,
        )
    response = drf_exception_handler(exc, context)
    if response is None:
        logger.exception("Unhandled API error", exc_info=exc)
    return response
