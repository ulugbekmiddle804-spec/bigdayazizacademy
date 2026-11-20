from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.core.validators import clean_person_name


class StartAttemptSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=60)
    last_name = serializers.CharField(max_length=60)
    branch_id = serializers.IntegerField(min_value=1)
    subject_id = serializers.IntegerField(min_value=1)

    def _name(self, value, label):
        try:
            return clean_person_name(value, label)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages[0])

    def validate_first_name(self, value):
        return self._name(value, "Ism")

    def validate_last_name(self, value):
        return self._name(value, "Familiya")


class AnswerItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(min_value=1)
    option = serializers.UUIDField(allow_null=True)


class AnswersSerializer(serializers.Serializer):
    stage = serializers.IntegerField(min_value=1, max_value=2)
    answers = AnswerItemSerializer(many=True, max_length=200)


class FinishSerializer(serializers.Serializer):
    answers = AnswerItemSerializer(many=True, max_length=200, required=False, default=list)
