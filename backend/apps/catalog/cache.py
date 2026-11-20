"""Redis-backed caches for read-heavy, rarely changing data.

Every write to a Branch/Subject/StageConfig/Question/Option bumps a version
number, so cached entries are invalidated without key scans.
"""
from django.conf import settings
from django.core.cache import cache

CATALOG_VERSION_KEY = "catalog:version"


def catalog_version() -> int:
    version = cache.get(CATALOG_VERSION_KEY)
    if version is None:
        version = 1
        cache.add(CATALOG_VERSION_KEY, version, None)
    return version


def bump_catalog_version():
    try:
        cache.incr(CATALOG_VERSION_KEY)
    except ValueError:
        cache.set(CATALOG_VERSION_KEY, 2, None)


def academic_subject_id() -> int | None:
    """Id of the shared academic question bank (one per site), if any."""
    from .models import Subject

    key = f"academic-id:{catalog_version()}"
    value = cache.get(key)
    if value is None:
        value = Subject.objects.filter(is_academic=True, is_active=True).values_list("id", flat=True).first() or 0
        cache.set(key, value, 600)
    return value or None


def stage_pool(subject_id: int, stage_config) -> list[dict]:
    """Question pool for one stage of a subject, following the stage's source setting."""
    if stage_config.source == stage_config.Source.ACADEMIC:
        bank = academic_subject_id()
        return question_pool(bank, None) if bank else []
    return question_pool(subject_id, stage_config.number)


def question_pool(subject_id: int, stage: int | None) -> list[dict]:
    """All active questions (with options and the answer key) of a subject stage
    (or of every stage when `stage` is None, used for the academic bank).

    Server-side only: this structure contains `correct` flags and is never sent
    to participants as-is.
    """
    from .models import Question

    key = f"qpool:{catalog_version()}:{subject_id}:{stage or 'all'}"
    pool = cache.get(key)
    if pool is not None:
        return pool
    questions = Question.objects.filter(subject_id=subject_id, is_active=True)
    if stage is not None:
        questions = questions.filter(stage=stage)
    questions = questions.prefetch_related("options").order_by("id")
    pool = []
    for q in questions:
        options = [{"id": str(o.uid), "text": o.text, "correct": o.is_correct} for o in q.options.all()]
        # Only usable questions: at least 2 options and exactly one correct.
        if len(options) >= 2 and sum(o["correct"] for o in options) == 1:
            pool.append({"id": q.id, "text": q.text, "points": q.points, "difficulty": q.difficulty,
                         "options": options})
    cache.set(key, pool, settings.EXAM["QUESTION_POOL_CACHE_SECONDS"])
    return pool


def public_catalog() -> dict:
    """Branches, subjects and stage settings for the entry form (no secrets)."""
    from apps.core.models import SiteSettings

    from .models import Branch, StageConfig, Subject

    key = f"public-catalog:{catalog_version()}"
    data = cache.get(key)
    if data is None:
        branches = [
            {"id": b.id, "name": b.name, "address": b.address}
            for b in Branch.objects.filter(is_active=True)
        ]
        stages_by_subject: dict[int, list] = {}
        for s in StageConfig.objects.filter(is_enabled=True).order_by("number"):
            stages_by_subject.setdefault(s.subject_id, []).append(
                {"number": s.number, "title": s.title, "question_count": s.question_count,
                 "duration_minutes": s.duration_minutes, "source": s.source}
            )
        subjects = list(Subject.objects.filter(is_active=True, is_academic=False).order_by("sort_order", "name"))
        children: dict[int, list] = {}
        for s in subjects:
            if s.parent_id:
                children.setdefault(s.parent_id, []).append(s)

        group_ids = set(
            Subject.objects.filter(parent__isnull=False).values_list("parent_id", flat=True)
        )

        def node(s):
            kids = children.get(s.id, [])
            return {
                "id": s.id, "name": s.name, "slug": s.slug, "description": s.description, "icon": s.icon,
                "selectable": s.id not in group_ids,
                "stages": stages_by_subject.get(s.id, []),
                "children": [node(k) for k in kids],
            }

        roots = [node(s) for s in subjects if not s.parent_id]
        data = {
            "branches": branches,
            # A group whose directions are all inactive is hidden.
            "subjects": [n for n in roots if n["selectable"] or n["children"]],
        }
        cache.set(key, data, 600)
    site = SiteSettings.load()
    return {**data, "site": {"title": site.site_title, "registration_open": site.registration_open}}
