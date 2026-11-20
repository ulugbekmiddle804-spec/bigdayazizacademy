from django.core.cache import cache
from django.db import models

SETTINGS_CACHE_KEY = "site-settings:v1"


class SiteSettings(models.Model):
    """Singleton with platform-wide switches the admin controls."""

    site_title = models.CharField("Sayt nomi", max_length=120, default="Aziz Academy")
    registration_open = models.BooleanField("Test topshirish ochiq", default=True)
    show_score = models.BooleanField(
        "Foydalanuvchiga ball va to'g'ri javoblar sonini ko'rsatish", default=False
    )
    show_answer_review = models.BooleanField(
        "Foydalanuvchiga javoblar kalitini ko'rsatish", default=False
    )
    allow_retake = models.BooleanField(
        "Hamma uchun qayta topshirishga ruxsat", default=False,
        help_text="O'chiq bo'lsa, qayta topshirishga faqat admin alohida ruxsat beradi.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Platforma sozlamalari"
        verbose_name_plural = "Platforma sozlamalari"

    def __str__(self):
        return self.site_title

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        cache.delete(SETTINGS_CACHE_KEY)

    def delete(self, *args, **kwargs):  # pragma: no cover - singleton is never deleted
        return None

    @classmethod
    def load(cls):
        obj = cache.get(SETTINGS_CACHE_KEY)
        if obj is None:
            obj, _ = cls.objects.get_or_create(pk=1)
            cache.set(SETTINGS_CACHE_KEY, obj, 300)
        return obj
