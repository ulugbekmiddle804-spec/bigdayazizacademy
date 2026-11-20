from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.cache import public_catalog
from apps.core.net import client_ip
from apps.core.throttles import AttemptStartThrottle, AttemptTokenThrottle, PublicMetaThrottle

from . import services
from .serializers import AnswersSerializer, FinishSerializer, StartAttemptSerializer


class PublicView(APIView):
    """Participant endpoints: no session/cookies, so no CSRF surface.
    Each attempt is authorised by its secret token (X-Attempt-Token header)."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def handle_exception(self, exc):
        if isinstance(exc, services.ExamError):
            return Response({"detail": exc.message, "code": exc.code}, status=exc.status)
        return super().handle_exception(exc)

    @staticmethod
    def token(request):
        return request.headers.get("X-Attempt-Token", "")


class MetaView(PublicView):
    throttle_classes = [PublicMetaThrottle]

    def get(self, request):
        return Response(public_catalog())


class StartAttemptView(PublicView):
    throttle_classes = [AttemptStartThrottle]

    def post(self, request):
        serializer = StartAttemptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = services.start_attempt(
            **serializer.validated_data,
            ip=client_ip(request),
            user_agent=request.headers.get("User-Agent", ""),
        )
        return Response(
            {"token": result.token, "state": services.serialize_state(result.attempt)},
            status=status.HTTP_201_CREATED,
        )


class AttemptStateView(PublicView):
    throttle_classes = [AttemptTokenThrottle]

    def get(self, request, attempt_id):
        attempt = services.load_state(attempt_id, self.token(request))
        return Response(services.serialize_state(attempt))


class SaveAnswersView(PublicView):
    throttle_classes = [AttemptTokenThrottle]

    def put(self, request, attempt_id):
        serializer = AnswersSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        services.save_answers(attempt_id, self.token(request), data["stage"], data["answers"])
        return Response({"saved": len(data["answers"]), "server_time": timezone.now().isoformat()})


class FinishStageView(PublicView):
    throttle_classes = [AttemptTokenThrottle]

    def post(self, request, attempt_id, stage):
        serializer = FinishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attempt = services.finish_stage(attempt_id, self.token(request), stage, serializer.validated_data["answers"])
        return Response(services.serialize_state(attempt))


class StartStageView(PublicView):
    throttle_classes = [AttemptTokenThrottle]

    def post(self, request, attempt_id, stage):
        attempt = services.start_stage(attempt_id, self.token(request), stage)
        return Response(services.serialize_state(attempt))
