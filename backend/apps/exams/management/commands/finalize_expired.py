from django.core.management.base import BaseCommand

from apps.exams.services import finalize_expired


class Command(BaseCommand):
    help = "Close attempts whose time has run out (same as the Celery beat task)."

    def handle(self, *args, **options):
        self.stdout.write(f"Finalized: {finalize_expired()}")
