import uuid

from django.db import models
from django.db.models import Q

from apps.catalog.models import Branch, Question, Subject


class Attempt(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Jarayonda"
        COMPLETED = "completed", "Yakunlangan"
        ANNULLED = "annulled", "Bekor qilingan"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    token_hash = models.CharField(max_length=64, editable=False)
    identity_key = models.CharField(max_length=64, db_index=True, editable=False)

    first_name = models.CharField("Ism", max_length=50)
    last_name = models.CharField("Familiya", max_length=50)
    branch = models.ForeignKey(Branch, verbose_name="Filial", on_delete=models.PROTECT, related_name="attempts")
    subject = models.ForeignKey(Subject, verbose_name="Fan", on_delete=models.PROTECT, related_name="attempts")

    status = models.CharField("Holat", max_length=12, choices=Status.choices, default=Status.ACTIVE)
    current_stage = models.PositiveSmallIntegerField(default=1)
    stage_count = models.PositiveSmallIntegerField(default=2)

    started_at = models.DateTimeField("Boshlangan", auto_now_add=True)
    finished_at = models.DateTimeField("Tugagan", null=True, blank=True)
    duration_seconds = models.PositiveIntegerField("Sarflangan vaqt (s)", null=True, blank=True)

    # Denormalised results for fast listing, sorting and export.
    stage1_score = models.PositiveIntegerField(default=0)
    stage1_correct = models.PositiveSmallIntegerField(default=0)
    stage2_score = models.PositiveIntegerField(default=0)
    stage2_correct = models.PositiveSmallIntegerField(default=0)
    total_score = models.PositiveIntegerField("Umumiy ball", default=0, db_index=True)
    max_score = models.PositiveIntegerField(default=0)
    correct_count = models.PositiveSmallIntegerField(default=0)
    wrong_count = models.PositiveSmallIntegerField(default=0)
    blank_count = models.PositiveSmallIntegerField(default=0)
    question_total = models.PositiveSmallIntegerField(default=0)

    retake_allowed = models.BooleanField("Qayta topshirishga ruxsat", default=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ("-started_at",)
        indexes = [
            models.Index(fields=["status", "started_at"]),
            models.Index(fields=["branch", "subject"]),
            models.Index(fields=["last_name", "first_name"]),
        ]
        constraints = [
            # One running attempt per person + branch + subject (race-safe).
            models.UniqueConstraint(
                fields=["identity_key"], condition=Q(status="active"), name="one_active_attempt_per_identity"
            ),
        ]
        verbose_name = "Test topshirish"
        verbose_name_plural = "Test topshirishlar"

    def __str__(self):
        return f"{self.last_name} {self.first_name} — {self.subject}"

    @property
    def percent(self):
        return round(self.total_score * 100 / self.max_score, 1) if self.max_score else 0.0

    def stage_percent(self, number):
        """Percent for one stage, or None if the attempt has no such stage. Prefetch `stages` for lists."""
        for stage in self.stages.all():
            if stage.number == number:
                return round(stage.score * 100 / stage.max_score, 1) if stage.max_score else 0.0
        return None


class AttemptStage(models.Model):
    class FinishReason(models.TextChoices):
        SUBMITTED = "submitted", "Foydalanuvchi yakunladi"
        TIMEOUT = "timeout", "Vaqt tugadi"
        ABANDONED = "abandoned", "Boshlanmadi / tashlab ketildi"

    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name="stages")
    number = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=80)
    question_count = models.PositiveSmallIntegerField()
    duration_seconds = models.PositiveIntegerField()
    started_at = models.DateTimeField(null=True, blank=True)
    deadline = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    finish_reason = models.CharField(max_length=12, choices=FinishReason.choices, blank=True)
    score = models.PositiveIntegerField(default=0)
    max_score = models.PositiveIntegerField(default=0)
    correct_count = models.PositiveSmallIntegerField(default=0)
    wrong_count = models.PositiveSmallIntegerField(default=0)
    blank_count = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("attempt", "number")
        unique_together = ("attempt", "number")

    def __str__(self):
        return f"{self.attempt_id} / {self.number}"


class AttemptAnswer(models.Model):
    """One assigned question of an attempt.

    The question text, options (in this participant's shuffled order) and the
    answer key are snapshotted at start, so later edits to the question bank
    never change an existing result.
    """

    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name="answers")
    stage = models.PositiveSmallIntegerField()
    position = models.PositiveSmallIntegerField()
    question = models.ForeignKey(Question, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    question_text = models.TextField()
    options = models.JSONField()  # [{"id": uid, "text": str}] in display order
    correct_option = models.UUIDField()
    points = models.PositiveSmallIntegerField(default=1)
    difficulty = models.CharField(max_length=10, blank=True)

    selected_option = models.UUIDField(null=True, blank=True)
    answered_at = models.DateTimeField(null=True, blank=True)
    is_correct = models.BooleanField(null=True)
    points_awarded = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("attempt", "stage", "position")
        unique_together = ("attempt", "stage", "position")

    def __str__(self):
        return f"{self.attempt_id} #{self.stage}.{self.position}"
