from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .cache import bump_catalog_version
from .models import Branch, Option, Question, StageConfig, Subject


@receiver([post_save, post_delete], sender=Branch)
@receiver([post_save, post_delete], sender=Subject)
@receiver([post_save, post_delete], sender=StageConfig)
@receiver([post_save, post_delete], sender=Question)
@receiver([post_save, post_delete], sender=Option)
def invalidate_catalog(sender, **kwargs):
    bump_catalog_version()
