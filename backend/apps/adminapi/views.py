import uuid
from datetime import datetime, time, timedelta

from django.contrib.auth import authenticate, login, logout
from django.db.models import Avg, Count, Max, Q
from django.http import HttpResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Branch, Question, StageConfig, Subject
from apps.core.models import SiteSettings
from apps.core.throttles import AdminLoginThrottle, AdminThrottle
from apps.exams.models import Attempt

from . import excel, word
from .serializers import (
    AttemptDetailSerializer,
    AttemptListSerializer,
    BranchSerializer,
    QuestionSerializer,
    SiteSettingsSerializer,
    SubjectSerializer,
)

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def xlsx_response(content: bytes, filename: str) -> HttpResponse:
    response = HttpResponse(content, content_type=XLSX)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["Cache-Control"] = "no-store"
    return response


def _bool_param(value):
    if value in (None, ""):
        return None
    return value.lower() in ("1", "true", "yes", "ha")


# ----------------------------------------------------------------------------- auth
@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"ok": True})


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AdminLoginThrottle]

    def post(self, request):
        username = str(request.data.get("username", ""))[:150]
        password = str(request.data.get("password", ""))[:256]
        user = authenticate(request, username=username, password=password)
        if user is None or not user.is_active or not user.is_staff:
            return Response({"detail": "Login yoki parol noto'g'ri."}, status=status.HTTP_400_BAD_REQUEST)
        login(request, user)  # rotates the session key
        return Response({"username": user.get_username(), "is_superuser": user.is_superuser})


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        logout(request)
        return Response({"ok": True})


class MeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        user = request.user
        if not user.is_authenticated or not user.is_staff:
            return Response({"detail": "Avtorizatsiya talab qilinadi."}, status=status.HTTP_401_UNAUTHORIZED)
        return Response({"username": user.get_username(), "is_superuser": user.is_superuser})


class AdminMixin:
    permission_classes = [IsAdminUser]
    throttle_classes = [AdminThrottle]


# ----------------------------------------------------------------------------- dashboard
class DashboardView(AdminMixin, APIView):
    def get(self, request):
        now = timezone.now()
        today = timezone.localtime(now).replace(hour=0, minute=0, second=0, microsecond=0)
        base = Attempt.objects.exclude(status=Attempt.Status.ANNULLED)
        completed = base.filter(status=Attempt.Status.COMPLETED)
        totals = completed.aggregate(avg_score=Avg("total_score"), avg_max=Avg("max_score"),
                                     avg_duration=Avg("duration_seconds"), best=Max("total_score"))
        avg_percent = None
        if totals["avg_max"]:
            avg_percent = round((totals["avg_score"] or 0) * 100 / totals["avg_max"], 1)

        by_subject = list(
            completed.values("subject__id", "subject__name", "subject__parent__name")
            .annotate(count=Count("id"), avg=Avg("total_score"), avg_max=Avg("max_score")).order_by("-count")
        )
        by_branch = list(
            completed.values("branch__id", "branch__name").annotate(count=Count("id"), avg=Avg("total_score"))
            .order_by("-count")
        )
        days = []
        for i in range(13, -1, -1):
            start = today - timedelta(days=i)
            days.append({"date": start.date().isoformat(),
                         "count": completed.filter(finished_at__gte=start, finished_at__lt=start + timedelta(days=1))
                         .count()})

        # Question bank health: subjects whose bank is smaller than the stage size.
        counts = {
            (r["subject_id"], r["stage"]): r["n"]
            for r in Question.objects.filter(is_active=True).values("subject_id", "stage").annotate(n=Count("id"))
        }
        academic = Subject.objects.filter(is_academic=True, is_active=True).first()
        academic_total = sum(n for (sid, _st), n in counts.items() if academic and sid == academic.id)
        warnings = []
        subjects = Subject.objects.filter(is_active=True, is_academic=False, children__isnull=True)
        for subj in subjects.prefetch_related("stages"):
            for st in subj.stages.all():
                if not st.is_enabled:
                    continue
                if st.source == StageConfig.Source.ACADEMIC:
                    available = academic_total
                else:
                    available = counts.get((subj.id, st.number), 0)
                if available < st.question_count:
                    warnings.append({"subject": subj.full_name, "stage": st.number, "available": available,
                                     "required": st.question_count})

        recent = base.select_related("branch", "subject", "subject__parent").order_by("-started_at")[:8]
        return Response({
            "attempts_total": base.count(),
            "completed_total": completed.count(),
            "active_now": base.filter(status=Attempt.Status.ACTIVE).count(),
            "today": completed.filter(finished_at__gte=today).count(),
            "avg_percent": avg_percent,
            "avg_duration": int(totals["avg_duration"] or 0),
            "best_score": totals["best"],
            "questions_total": Question.objects.filter(is_active=True).count(),
            "branches_total": Branch.objects.filter(is_active=True).count(),
            "by_subject": [
                {"subject": (f"{r['subject__parent__name']} — {r['subject__name']}" if r["subject__parent__name"]
                             else r["subject__name"]),
                 "count": r["count"],
                 "avg_percent": round((r["avg"] or 0) * 100 / r["avg_max"], 1) if r["avg_max"] else 0}
                for r in by_subject
            ],
            "by_branch": [{"branch": r["branch__name"], "count": r["count"], "avg": round(r["avg"] or 0, 1)}
                          for r in by_branch],
            "daily": days,
            "warnings": warnings,
            "recent": AttemptListSerializer(recent, many=True).data,
        })


# ----------------------------------------------------------------------------- attempts
class AttemptViewSet(AdminMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin,
                     viewsets.GenericViewSet):
    ordering_fields = {
        "total_score": "total_score", "started_at": "started_at", "finished_at": "finished_at",
        "duration": "duration_seconds", "last_name": "last_name", "first_name": "first_name",
        "stage1_score": "stage1_score", "stage2_score": "stage2_score",
    }

    def get_serializer_class(self):
        return AttemptDetailSerializer if self.action == "retrieve" else AttemptListSerializer

    def get_queryset(self):
        qs = Attempt.objects.select_related("branch", "subject", "subject__parent").prefetch_related("stages")
        if self.action == "retrieve":
            return qs.prefetch_related("answers")
        p = self.request.query_params
        if p.get("first_name"):
            qs = qs.filter(first_name__icontains=p["first_name"].strip())
        if p.get("last_name"):
            qs = qs.filter(last_name__icontains=p["last_name"].strip())
        if p.get("search"):
            for word in p["search"].split()[:4]:
                qs = qs.filter(Q(first_name__icontains=word) | Q(last_name__icontains=word))
        if p.get("branch"):
            qs = qs.filter(branch_id=p["branch"]) if p["branch"].isdigit() else qs.none()
        if p.get("subject"):
            if p["subject"].isdigit():
                qs = qs.filter(Q(subject_id=p["subject"]) | Q(subject__parent_id=p["subject"]))
            else:
                qs = qs.none()
        if p.get("status") in Attempt.Status.values:
            qs = qs.filter(status=p["status"])
        for param, lookup, bound in (("date_from", "started_at__gte", time.min), ("date_to", "started_at__lte",
                                                                                     time.max)):
            if p.get(param):
                try:
                    day = datetime.strptime(p[param], "%Y-%m-%d").date()
                    qs = qs.filter(**{lookup: timezone.make_aware(datetime.combine(day, bound))})
                except ValueError:
                    pass
        ordering = p.get("ordering", "-started_at")
        field = self.ordering_fields.get(ordering.lstrip("-"))
        if field:
            qs = qs.order_by(("-" if ordering.startswith("-") else "") + field, "-started_at")
        return qs

    @action(detail=False, methods=["get"])
    def export(self, request):
        qs = self.get_queryset()[:20000]
        detailed = _bool_param(request.query_params.get("answers")) or False
        stamp = timezone.localtime().strftime("%Y%m%d_%H%M")
        return xlsx_response(excel.export_attempts(qs, include_answers=detailed), f"natijalar_{stamp}.xlsx")

    @action(detail=False, methods=["post"], url_path="bulk-delete")
    def bulk_delete(self, request):
        """Delete selected results ({"ids": [...]}) or every result that matches the current filters
        ({"all": true, "confirm": "DELETE"}; filters come from the query string, as in the list)."""
        if request.data.get("all"):
            if request.data.get("confirm") != "DELETE":
                return Response({"detail": "Tasdiqlash talab qilinadi."}, status=400)
            qs = self.get_queryset()
        else:
            ids = request.data.get("ids")
            if not isinstance(ids, list) or not ids or len(ids) > 1000:
                return Response({"detail": "O'chiriladigan natijalarni tanlang."}, status=400)
            try:
                ids = [uuid.UUID(str(i)) for i in ids]
            except ValueError:
                return Response({"detail": "Noto'g'ri identifikator."}, status=400)
            qs = Attempt.objects.filter(pk__in=ids)
        pks = list(qs.order_by().values_list("pk", flat=True))
        deleted = 0
        for start in range(0, len(pks), 500):  # chunks keep SQLite's variable limit happy
            deleted += Attempt.objects.filter(pk__in=pks[start:start + 500]).delete()[1].get("exams.Attempt", 0)
        return Response({"deleted": deleted})

    @action(detail=True, methods=["post"], url_path="allow-retake")
    def allow_retake(self, request, pk=None):
        attempt = self.get_object()
        attempt.retake_allowed = bool(request.data.get("allowed", True))
        attempt.save(update_fields=["retake_allowed"])
        return Response(AttemptListSerializer(attempt).data)

    @action(detail=True, methods=["post"])
    def annul(self, request, pk=None):
        """Cancel an attempt (e.g. a stuck one). The person can then start again."""
        attempt = self.get_object()
        if attempt.status != Attempt.Status.ANNULLED:
            attempt.status = Attempt.Status.ANNULLED
            attempt.finished_at = attempt.finished_at or timezone.now()
            attempt.save(update_fields=["status", "finished_at"])
        return Response(AttemptListSerializer(attempt).data)


# ----------------------------------------------------------------------------- catalog
class BranchViewSet(AdminMixin, viewsets.ModelViewSet):
    serializer_class = BranchSerializer
    pagination_class = None

    def get_queryset(self):
        qs = Branch.objects.annotate(attempts_count=Count("attempts")).order_by("sort_order", "name")
        if self.request.query_params.get("search"):
            qs = qs.filter(name__icontains=self.request.query_params["search"])
        return qs


class SubjectViewSet(AdminMixin, viewsets.ModelViewSet):
    serializer_class = SubjectSerializer
    pagination_class = None

    def get_queryset(self):
        return Subject.objects.select_related("parent").prefetch_related("stages").order_by("sort_order", "name")

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["question_counts"] = {
            (r["subject_id"], r["stage"]): r["n"]
            for r in Question.objects.filter(is_active=True).values("subject_id", "stage").annotate(n=Count("id"))
        }
        ctx["group_ids"] = set(Subject.objects.filter(parent__isnull=False).values_list("parent_id", flat=True))
        return ctx


class QuestionViewSet(AdminMixin, viewsets.ModelViewSet):
    serializer_class = QuestionSerializer

    def get_queryset(self):
        qs = Question.objects.select_related("subject", "subject__parent").prefetch_related("options")
        p = self.request.query_params
        if p.get("subject", "").isdigit():
            qs = qs.filter(Q(subject_id=p["subject"]) | Q(subject__parent_id=p["subject"]))
        if p.get("stage") in ("1", "2"):
            qs = qs.filter(stage=p["stage"])
        if p.get("difficulty") in Question.Difficulty.values:
            qs = qs.filter(difficulty=p["difficulty"])
        active = _bool_param(p.get("is_active"))
        if active is not None:
            qs = qs.filter(is_active=active)
        if p.get("search"):
            qs = qs.filter(text__icontains=p["search"].strip())
        return qs.order_by("subject__sort_order", "subject_id", "stage", "id")

    @action(detail=False, methods=["get"])
    def export(self, request):
        stamp = timezone.localtime().strftime("%Y%m%d_%H%M")
        return xlsx_response(excel.export_questions(self.get_queryset()), f"savollar_{stamp}.xlsx")

    @action(detail=False, methods=["get"])
    def template(self, request):
        return xlsx_response(excel.question_template(), "savollar_shablon.xlsx")

    @action(detail=False, methods=["post"], url_path="import")
    def import_file(self, request):
        upload = request.FILES.get("file")
        if not upload:
            return Response({"detail": "Fayl tanlanmagan."}, status=status.HTTP_400_BAD_REQUEST)
        if not upload.name.lower().endswith(".xlsx") or upload.size > 5 * 1024 * 1024:
            return Response({"detail": "Faqat 5 MB gacha bo'lgan .xlsx fayl."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            created = excel.import_questions(upload)
        except excel.ImportErrorList as exc:
            return Response({"detail": "Faylda xatolar bor, hech narsa import qilinmadi.", "errors": exc.errors},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response({"created": created}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="word-template")
    def word_template(self, request):
        response = HttpResponse(
            word.word_template(),
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        response["Content-Disposition"] = 'attachment; filename="test_namuna.docx"'
        return response

    @action(detail=False, methods=["post"], url_path="import-word")
    def import_word(self, request):
        """Attach questions from a Word file to one subject and stage.

        Form fields: file, subject, stage (1/2), points, difficulty, replace (0/1), preview (0/1).
        """
        data = request.data
        upload = request.FILES.get("file")
        if not upload:
            return Response({"detail": "Fayl tanlanmagan."}, status=status.HTTP_400_BAD_REQUEST)
        if not upload.name.lower().endswith(".docx") or upload.size > 5 * 1024 * 1024:
            return Response({"detail": "Faqat 5 MB gacha bo'lgan .docx (Word) fayl."},
                            status=status.HTTP_400_BAD_REQUEST)
        subject = Subject.objects.filter(pk=data.get("subject") if str(data.get("subject", "")).isdigit() else None).first()
        if not subject:
            return Response({"detail": "Fan tanlanmagan."}, status=status.HTTP_400_BAD_REQUEST)
        if Subject.objects.filter(parent=subject).exists():
            return Response({"detail": "Savollar guruhga emas, aniq yo'nalishga biriktiriladi."},
                            status=status.HTTP_400_BAD_REQUEST)
        stage = str(data.get("stage", "2"))
        if stage not in ("1", "2"):
            return Response({"detail": "Bosqich 1 yoki 2 bo'lsin."}, status=status.HTTP_400_BAD_REQUEST)
        stage = 1 if subject.is_academic else int(stage)
        try:
            points = int(data.get("points") or 1)
            if not 1 <= points <= 100:
                raise ValueError
        except ValueError:
            return Response({"detail": "Ball 1–100 oralig'ida bo'lsin."}, status=status.HTTP_400_BAD_REQUEST)
        difficulty = data.get("difficulty") or Question.Difficulty.MEDIUM
        if difficulty not in Question.Difficulty.values:
            return Response({"detail": "Qiyinlik noto'g'ri."}, status=status.HTTP_400_BAD_REQUEST)
        result = word.import_word(
            upload, subject=subject, stage=stage, points=points, difficulty=difficulty,
            replace=_bool_param(data.get("replace")) is True, preview=_bool_param(data.get("preview")) is True,
        )
        if result["problems"] and not _bool_param(data.get("preview")):
            return Response({"detail": "Faylda xatolar bor, hech narsa saqlanmadi.", **result},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK if "created" not in result else status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="bulk-active")
    def bulk_active(self, request):
        ids = [int(i) for i in request.data.get("ids", []) if str(i).isdigit()][:1000]
        value = bool(request.data.get("is_active", True))
        updated = 0
        for q in Question.objects.filter(id__in=ids):
            q.is_active = value
            q.save(update_fields=["is_active", "updated_at"])
            updated += 1
        return Response({"updated": updated})

    # Deleting a question is safe: attempts keep their own snapshot of it.


class SettingsView(AdminMixin, APIView):
    def get(self, request):
        return Response(SiteSettingsSerializer(SiteSettings.load()).data)

    def put(self, request):
        obj, _ = SiteSettings.objects.get_or_create(pk=1)
        serializer = SiteSettingsSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

