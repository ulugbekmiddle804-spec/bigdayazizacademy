import logging

from celery import shared_task

from .services import finalize_expired

logger = logging.getLogger(__name__)


@shared_task(name="apps.exams.tasks.finalize_expired_attempts", ignore_result=True)
def finalize_expired_attempts():
    count = finalize_expired()
    if count:
        logger.info("Finalized %s expired attempts", count)
    return count
