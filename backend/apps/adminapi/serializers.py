from django.db import transaction
from rest_framework import serializers

from apps.catalog.models import Branch, Option, Question, StageConfig, Subject
from apps.core.models import SiteSettings
from apps.exams.models import Attempt, AttemptAnswer, AttemptStage


class BranchSerializer(serializers.ModelSerializer):
    attempts_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Branch
        fields = ("id", "name", "address", "is_active", "sort_order", "attempts_count", "created_at")
        read_only_fields = ("created_at",)

    def validate_name(self, value):
        value = " ".join(value.split())
        if len(value) < 2:
            raise serializers.ValidationError("Nomi juda qisqa.")
        return value


def default_stages():
    """New subjects: stage 1 is the shared academic test, stage 2 is the subject's own test."""
    return [
        {"number": 1, "title": "Akademik test", "question_count": 20, "duration_minutes": 25,
         "source": StageConfig.Source.ACADEMIC, "is_enabled": True},
        {"number": 2, "title": "Fan testi", "question_count": 30, "duration_minutes": 40,
         "source": StageConfig.Source.SUBJECT, "is_enabled": True},
    ]


class StageConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = StageConfig
        fields = ("number", "title", "question_count", "duration_minutes", "source", "is_enabled")


class SubjectSerializer(serializers.ModelSerializer):
    stages = StageConfigSerializer(many=True, required=False)
    question_counts = serializers.SerializerMethodField()
    full_name = serializers.CharField(read_only=True)
    is_group = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = ("id", "name", "slug", "parent", "full_name", "description", "icon", "is_academic", "is_active",
                  "sort_order", "stages", "question_counts", "is_group")

    def get_question_counts(self, obj):
        counts = self.context.get("question_counts", {})
        c1, c2 = counts.get((obj.id, 1), 0), counts.get((obj.id, 2), 0)
        return {"1": c1, "2": c2, "total": c1 + c2}

    def validate(self, attrs):
        is_academic = attrs.get("is_academic", getattr(self.instance, "is_academic", False))
        parent = attrs.get("parent", getattr(self.instance, "parent", None))
        if is_academic:
            if parent is not None:
                raise serializers.ValidationError({"is_academic": "Akademik test banki guruh ichida bo'la olmaydi."})
            others = Subject.objects.filter(is_academic=True)
            if self.instance:
                others = others.exclude(pk=self.instance.pk)
            if others.exists():
                raise serializers.ValidationError({"is_academic": "Akademik test banki allaqachon mavjud."})
        return attrs

    def get_is_group(self, obj):
        return obj.id in self.context.get("group_ids", set())

    def validate_parent(self, parent):
        if parent is None:
            return parent
        if parent.parent_id:
            raise serializers.ValidationError("Faqat ikki darajali tuzilma qo'llab-quvvatlanadi.")
        if self.instance and parent.pk == self.instance.pk:
            raise serializers.ValidationError("Fan o'ziga o'zi asosiy bo'la olmaydi.")
        if parent.questions.exists():
            raise serializers.ValidationError("Savollari bor fanni guruhga aylantirib bo'lmaydi.")
        return parent

    def validate_stages(self, stages):
        numbers = [s["number"] for s in stages]
        if len(numbers) != len(set(numbers)):
            raise serializers.ValidationError("Bosqich raqamlari takrorlanmasin.")
        if stages and not any(s.get("is_enabled", True) for s in stages):
            raise serializers.ValidationError("Kamida bitta bosqich yoqilgan bo'lsin.")
        return stages

    def _save_stages(self, subject, stages):
        for data in stages:
            StageConfig.objects.update_or_create(subject=subject, number=data["number"], defaults=data)

    @transaction.atomic
    def create(self, validated_data):
        stages = validated_data.pop("stages", None)
        subject = super().create(validated_data)
        if stages is None:
            stages = default_stages()
        self._save_stages(subject, stages)
        return subject

    @transaction.atomic
    def update(self, instance, validated_data):
        stages = validated_data.pop("stages", None)
        subject = super().update(instance, validated_data)
        if stages is not None:
            self._save_stages(subject, stages)
        return subject


class OptionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = Option
        fields = ("id", "text", "is_correct")


class QuestionSerializer(serializers.ModelSerializer):
    options = OptionSerializer(many=True)
    subject_name = serializers.CharField(source="subject.full_name", read_only=True)

    class Meta:
        model = Question
        fields = ("id", "subject", "subject_name", "stage", "text", "difficulty", "points", "is_active",
                  "options", "created_at", "updated_at")
        read_only_fields = ("created_at", "updated_at")

    def validate_text(self, value):
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("Savol matni juda qisqa.")
        return value

    def validate_subject(self, subject):
        if Subject.objects.filter(parent=subject).exists():
            raise serializers.ValidationError("Savol guruhga emas, aniq yo'nalishga biriktirilsin.")
        return subject

    def validate_options(self, options):
        cleaned = []
        for o in options:
            text = o["text"].strip()
            if not text:
                raise serializers.ValidationError("Javob matni bo'sh bo'lmasin.")
            cleaned.append({**o, "text": text})
        if not 2 <= len(cleaned) <= 6:
            raise serializers.ValidationError("Javob variantlari 2 tadan 6 tagacha bo'lsin.")
        if sum(1 for o in cleaned if o.get("is_correct")) != 1:
            raise serializers.ValidationError("Aynan bitta to'g'ri javob belgilang.")
        texts = [o["text"].casefold() for o in cleaned]
        if len(texts) != len(set(texts)):
            raise serializers.ValidationError("Javob variantlari takrorlanmasin.")
        return cleaned

    @transaction.atomic
    def create(self, validated_data):
        options = validated_data.pop("options")
        question = Question.objects.create(**validated_data)
        Option.objects.bulk_create(
            [Option(question=question, text=o["text"], is_correct=o.get("is_correct", False), sort_order=i)
             for i, o in enumerate(options)]
        )
        return question

    @transaction.atomic
    def update(self, instance, validated_data):
        options = validated_data.pop("options", None)
        instance = super().update(instance, validated_data)
        if options is not None:
            existing = {o.id: o for o in instance.options.all()}
            keep = set()
            for i, data in enumerate(options):
                opt = existing.get(data.get("id"))
                if opt:
                    opt.text, opt.is_correct, opt.sort_order = data["text"], data.get("is_correct", False), i
                    opt.save()
                    keep.add(opt.id)
                else:
                    Option.objects.create(question=instance, text=data["text"],
                                          is_correct=data.get("is_correct", False), sort_order=i)
            instance.options.exclude(id__in=keep).filter(id__in=existing.keys()).delete()
        return instance


class SiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSettings
        fields = ("site_title", "registration_open", "show_score", "show_answer_review", "allow_retake",
                  "updated_at")
        read_only_fields = ("updated_at",)


class AttemptListSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    subject_name = serializers.SerializerMethodField()
    percent = serializers.FloatField(read_only=True)
    stage1_percent = serializers.SerializerMethodField()
    stage2_percent = serializers.SerializerMethodField()

    class Meta:
        model = Attempt
        fields = ("id", "first_name", "last_name", "branch", "branch_name", "subject", "subject_name", "status",
                  "current_stage", "started_at", "finished_at", "duration_seconds", "stage1_score",
                  "stage1_correct", "stage2_score", "stage2_correct", "total_score", "max_score", "percent",
                  "stage1_percent", "stage2_percent", "stage_count", "correct_count", "wrong_count", "blank_count", "question_total", "retake_allowed")

    def get_stage1_percent(self, obj):
        return obj.stage_percent(1)

    def get_stage2_percent(self, obj):
        return obj.stage_percent(2)

    def get_subject_name(self, obj):
        s = obj.subject
        return f"{s.parent.name} — {s.name}" if s.parent_id else s.name


class AttemptStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttemptStage
        fields = ("number", "title", "question_count", "duration_seconds", "started_at", "deadline",
                  "finished_at", "finish_reason", "score", "max_score", "correct_count", "wrong_count",
                  "blank_count")


class AttemptAnswerSerializer(serializers.ModelSerializer):
    result = serializers.SerializerMethodField()

    class Meta:
        model = AttemptAnswer
        fields = ("id", "stage", "position", "question", "question_text", "options", "correct_option",
                  "selected_option", "answered_at", "is_correct", "points", "points_awarded", "difficulty",
                  "result")

    def get_result(self, obj):
        if obj.selected_option is None:
            return "blank"
        if obj.is_correct is None:
            return "pending"
        return "correct" if obj.is_correct else "wrong"


class AttemptDetailSerializer(AttemptListSerializer):
    stages = AttemptStageSerializer(many=True, read_only=True)
    answers = AttemptAnswerSerializer(many=True, read_only=True)

    class Meta(AttemptListSerializer.Meta):
        fields = AttemptListSerializer.Meta.fields + ("ip_address", "user_agent", "stages", "answers")
