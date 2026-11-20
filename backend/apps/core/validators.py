import re

from django.core.exceptions import ValidationError

# Letters of any script (Latin, Cyrillic, Arabic...), spaces, hyphens and the
# apostrophe variants used in Uzbek (o', g', ʻ, ʼ, ’).
NAME_RE = re.compile(r"^[^\W\d_]+(?:[ \-'ʻʼ’‘`][^\W\d_]*)*$", re.UNICODE)


def clean_person_name(value: str, field_label: str) -> str:
    value = " ".join((value or "").split())
    if len(value) < 2:
        raise ValidationError(f"{field_label} kamida 2 ta harfdan iborat bo'lsin.")
    if len(value) > 50:
        raise ValidationError(f"{field_label} 50 ta belgidan oshmasin.")
    if not NAME_RE.match(value):
        raise ValidationError(f"{field_label} faqat harflardan iborat bo'lishi kerak.")
    return value


def normalize_name(value: str) -> str:
    value = " ".join(value.split()).casefold()
    for ch in "ʻʼ’‘`":
        value = value.replace(ch, "'")
    return value
