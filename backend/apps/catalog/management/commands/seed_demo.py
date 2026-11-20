import random

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.catalog import demo_data
from apps.catalog.answer_order import correct_slots, place_correct
from apps.catalog.models import Branch, Option, Question, StageConfig, Subject
from apps.core.models import SiteSettings


class Command(BaseCommand):
    help = ("Create branches, subjects, stage settings, the academic bank and the question banks. "
            "Idempotent: existing records (and admin changes) are left alone.")

    def add_arguments(self, parser):
        parser.add_argument("--reset-questions", action="store_true",
                            help="Delete all questions of the seeded subjects and load them again.")

    @transaction.atomic
    def handle(self, *args, **options):
        problems = demo_data.validate()
        if problems:
            raise CommandError("Question bank is invalid:\n" + "\n".join(problems))

        SiteSettings.load()
        for order, (name, address) in enumerate(demo_data.BRANCHES):
            Branch.objects.get_or_create(name=name, defaults={"address": address, "sort_order": order})

        rng = random.Random(2024)
        created_q = 0

        def load_questions(subject, module, stage_no):
            nonlocal created_q
            if options["reset_questions"]:
                Question.objects.filter(subject=subject).delete()
            if Question.objects.filter(subject=subject).exists():
                return
            items = demo_data.items(module)
            # Stored order: right answer spread over the letters, never the same letter twice in a row.
            # Participants still get their own order (see apps.exams.services).
            slots = correct_slots([len(opts) for _d, _t, opts, _c in items], rng)
            for (diff, text, opts, correct), slot in zip(items, slots):
                q = Question.objects.create(subject=subject, stage=stage_no, text=text, difficulty=diff,
                                            points=demo_data.POINTS[stage_no])
                pairs = place_correct([(t, i == correct) for i, t in enumerate(opts)], lambda p: p[1], slot, rng)
                Option.objects.bulk_create(
                    [Option(question=q, text=t, is_correct=c, sort_order=i) for i, (t, c) in enumerate(pairs)]
                )
                created_q += 1

        slug, name, desc, icon, module = demo_data.ACADEMIC
        academic = Subject.objects.filter(is_academic=True).first()
        if academic is None:
            academic, _ = Subject.objects.get_or_create(
                slug=slug, defaults={"name": name, "description": desc, "icon": icon, "sort_order": 0,
                                     "is_academic": True})
        load_questions(academic, module, 1)

        for order, (slug, name, desc, icon, module) in enumerate(demo_data.SUBJECTS, start=1):
            subject, _ = Subject.objects.get_or_create(
                slug=slug, defaults={"name": name, "description": desc, "icon": icon, "sort_order": order})
            StageConfig.objects.get_or_create(subject=subject, number=1, defaults=demo_data.ACADEMIC_STAGE)
            if module is None:
                continue
            StageConfig.objects.get_or_create(subject=subject, number=2, defaults=demo_data.SUBJECT_STAGE)
            load_questions(subject, module, 2)

        self.stdout.write(self.style.SUCCESS(
            f"Data ready: {Branch.objects.count()} branches, {Subject.objects.count()} subjects, "
            f"{created_q} new questions (total {Question.objects.count()})."
        ))
