import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Branch(models.Model):
    name = models.CharField("Nomi", max_length=120, unique=True)
    address = models.CharField("Manzil", max_length=255, blank=True)
    is_active = models.BooleanField("Faol", default=True)
    sort_order = models.PositiveIntegerField("Tartib", default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("sort_order", "name")
        verbose_name = "Filial"
        verbose_name_plural = "Filiallar"

    def __str__(self):
        return self.name


class Subject(models.Model):
    """A subject. Subjects with a parent (e.g. IT → Frontend) are selectable
    directions; a parent subject only groups its children."""

    name = models.CharField("Nomi", max_length=120)
    slug = models.SlugField("Kod", max_length=60, unique=True)
    parent = models.ForeignKey(
        "self", verbose_name="Asosiy fan", null=True, blank=True,
        on_delete=models.PROTECT, related_name="children",
    )
    description = models.CharField("Qisqa tavsif", max_length=255, blank=True)
    icon = models.CharField("Ikonka kodi", max_length=40, blank=True, default="book")
    is_academic = models.BooleanField(
        "Akademik test banki", default=False,
        help_text="Barcha fanlar uchun umumiy savollar banki. Kirish sahifasida ko'rinmaydi.",
    )
    is_active = models.BooleanField("Faol", default=True)
    sort_order = models.PositiveIntegerField("Tartib", default=0)

    class Meta:
        ordering = ("sort_order", "name")
        constraints = [
            models.UniqueConstraint(fields=["is_academic"], condition=models.Q(is_academic=True),
                                    name="single_academic_bank"),
        ]
        verbose_name = "Fan"
        verbose_name_plural = "Fanlar"

    def __str__(self):
        return f"{self.parent.name} — {self.name}" if self.parent_id else self.name

    @property
    def full_name(self):
        return str(self)

    def is_group(self):
        return self.children.exists()


class StageConfig(models.Model):
    """Per-subject settings for each test stage (number of questions, time, question source)."""

    class Source(models.TextChoices):
        SUBJECT = "subject", "Fanning o'z savollari"
        ACADEMIC = "academic", "Akademik test banki"

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="stages")
    number = models.PositiveSmallIntegerField("Bosqich", validators=[MinValueValidator(1), MaxValueValidator(2)])
    title = models.CharField("Nomi", max_length=80)
    question_count = models.PositiveSmallIntegerField(
        "Savollar soni", validators=[MinValueValidator(1), MaxValueValidator(200)]
    )
    duration_minutes = models.PositiveSmallIntegerField(
        "Vaqt (daqiqa)", validators=[MinValueValidator(1), MaxValueValidator(600)]
    )
    source = models.CharField("Savollar manbai", max_length=10, choices=Source.choices, default=Source.SUBJECT)
    is_enabled = models.BooleanField("Yoqilgan", default=True)

    class Meta:
        ordering = ("subject", "number")
        unique_together = ("subject", "number")
        verbose_name = "Test bosqichi"
        verbose_name_plural = "Test bosqichlari"

    def __str__(self):
        return f"{self.subject} — {self.number}-bosqich"


class Question(models.Model):
    class Difficulty(models.TextChoices):
        EASY = "easy", "Oson"
        MEDIUM = "medium", "O'rta"
        HARD = "hard", "Qiyin"

    subject = models.ForeignKey(Subject, verbose_name="Fan", on_delete=models.PROTECT, related_name="questions")
    stage = models.PositiveSmallIntegerField(
        "Bosqich", default=1, validators=[MinValueValidator(1), MaxValueValidator(2)]
    )
    text = models.TextField("Savol matni", max_length=2000)
    difficulty = models.CharField("Qiyinlik", max_length=10, choices=Difficulty.choices, default=Difficulty.MEDIUM)
    points = models.PositiveSmallIntegerField(
        "Ball", default=1, validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    is_active = models.BooleanField("Faol", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("subject", "stage", "id")
        indexes = [models.Index(fields=["subject", "stage", "is_active"])]
        verbose_name = "Savol"
        verbose_name_plural = "Savollar"

    def __str__(self):
        return self.text[:80]


class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    # Random public id: sequential ids could leak which option was created first.
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    text = models.CharField("Javob matni", max_length=500)
    is_correct = models.BooleanField("To'g'ri javob", default=False)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("question", "sort_order", "id")
        verbose_name = "Javob varianti"
        verbose_name_plural = "Javob variantlari"

    def __str__(self):
        return self.text[:60]
