"""Exam business logic: starting attempts, saving answers, grading.

All state transitions lock the attempt row (SELECT ... FOR UPDATE), so
concurrent requests from the same participant (double clicks, retries after
a reconnect, the background sweeper) can never grade twice or lose answers.
"""
import hashlib
import hmac
import logging
import secrets
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.catalog.answer_order import correct_slots, place_correct
from apps.catalog.cache import stage_pool
from apps.catalog.models import Branch, StageConfig, Subject
from apps.core.models import SiteSettings
from apps.core.validators import normalize_name

from .models import Attempt, AttemptAnswer, AttemptStage

logger = logging.getLogger(__name__)
_rng = secrets.SystemRandom()


class ExamError(Exception):
    """Business rule violation; `code` maps to an HTTP status in the views."""

    def __init__(self, message, code="invalid", status=400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def identity_key(first_name, last_name, branch_id, subject_id) -> str:
    raw = f"{normalize_name(first_name)}|{normalize_name(last_name)}|{branch_id}|{subject_id}"
    return hashlib.sha256(raw.encode()).hexdigest()


def token_matches(attempt: Attempt, token: str) -> bool:
    return bool(token) and hmac.compare_digest(attempt.token_hash, hash_token(token))


def grace() -> timedelta:
    return timedelta(seconds=settings.EXAM["GRACE_SECONDS"])


@dataclass
class StartResult:
    attempt: Attempt
    token: str


# --------------------------------------------------------------------------- start
def start_attempt(*, first_name, last_name, branch_id, subject_id, ip=None, user_agent="") -> StartResult:
    site = SiteSettings.load()
    if not site.registration_open:
        raise ExamError("Hozircha test topshirish yopiq.", "closed", 403)

    branch = Branch.objects.filter(pk=branch_id, is_active=True).first()
    if not branch:
        raise ExamError("Filial topilmadi.", "branch", 400)
    subject = Subject.objects.filter(pk=subject_id, is_active=True).first()
    if not subject or subject.is_academic or Subject.objects.filter(parent=subject).exists():
        raise ExamError("Fan topilmadi yoki yo'nalish tanlanmagan.", "subject", 400)
    if subject.parent_id and not Subject.objects.filter(pk=subject.parent_id, is_active=True).exists():
        raise ExamError("Fan topilmadi.", "subject", 400)

    stage_configs = list(StageConfig.objects.filter(subject=subject, is_enabled=True).order_by("number"))
    if not stage_configs:
        raise ExamError("Bu fan uchun test bosqichlari sozlanmagan.", "no_stages", 409)

    # Pick questions first (outside the transaction: reads cached data only).
    picked: list[tuple[StageConfig, list[dict]]] = []
    for cfg in stage_configs:
        pool = stage_pool(subject.id, cfg)
        if not pool:
            raise ExamError("Bu fan bo'yicha savollar hali kiritilmagan.", "no_questions", 409)
        count = min(cfg.question_count, len(pool))
        if count < cfg.question_count:
            logger.warning("Subject %s stage %s: only %s of %s questions available",
                           subject.slug, cfg.number, len(pool), cfg.question_count)
        chosen = _rng.sample(pool, count)  # random selection, random order
        if cfg.source == StageConfig.Source.ACADEMIC:
            chosen.sort(key=lambda q: q["id"])  # academic test keeps the document's order (1, 2, 3 …)
        picked.append((cfg, chosen))

    key = identity_key(first_name, last_name, branch.id, subject.id)
    token = secrets.token_urlsafe(32)
    now = timezone.now()

    error = None
    attempt = None
    try:
        with transaction.atomic():
            previous = list(
                Attempt.objects.select_for_update().filter(identity_key=key).exclude(status=Attempt.Status.ANNULLED)
                .order_by("-started_at")
            )
            for prev in previous:
                if prev.status == Attempt.Status.ACTIVE:
                    _expire_if_needed(prev, now)
            active = [p for p in previous if p.status == Attempt.Status.ACTIVE]
            completed = [p for p in previous if p.status == Attempt.Status.COMPLETED]
            if active:
                error = ExamError(
                    "Sizda boshlangan, hali tugallanmagan test bor. Testni boshlagan qurilmangizda davom "
                    "ettiring yoki administratorga murojaat qiling.", "active_exists", 409)
            elif completed and not site.allow_retake and not completed[0].retake_allowed:
                error = ExamError(
                    "Siz bu fandan test topshirib bo'lgansiz. Qayta topshirish uchun administrator "
                    "ruxsati kerak.", "already_completed", 403)
            else:
                if completed and completed[0].retake_allowed:
                    completed[0].retake_allowed = False  # permission is used up
                    completed[0].save(update_fields=["retake_allowed"])
                attempt = _create_attempt(token, key, first_name, last_name, branch, subject, stage_configs,
                                          picked, ip, user_agent, now)
    except IntegrityError:
        # Two simultaneous "start" clicks for the same person.
        raise ExamError("Test allaqachon boshlangan. Sahifani yangilang.", "active_exists", 409)
    # Raised after commit, so expiring an old attempt above is kept.
    if error:
        raise error

    return StartResult(attempt=attempt, token=token)




def _create_attempt(token, key, first_name, last_name, branch, subject, stage_configs, picked, ip, user_agent, now):
    attempt = Attempt.objects.create(
        token_hash=hash_token(token), identity_key=key,
        first_name=first_name, last_name=last_name, branch=branch, subject=subject,
        current_stage=stage_configs[0].number, stage_count=len(stage_configs),
        ip_address=ip, user_agent=(user_agent or "")[:255],
    )
    stages, answers = [], []
    for index, (cfg, questions) in enumerate(picked):
        is_first = index == 0
        duration = cfg.duration_minutes * 60
        stages.append(AttemptStage(
            attempt=attempt, number=cfg.number, title=cfg.title, question_count=len(questions),
            duration_seconds=duration,
            started_at=now if is_first else None,
            deadline=now + timedelta(seconds=duration) if is_first else None,
            max_score=sum(q["points"] for q in questions),
        ))
        # Spread the right answer over A/B/C/D, never the same letter twice in a row.
        slots = correct_slots([len(q["options"]) for q in questions], _rng)
        for position, (q, slot) in enumerate(zip(questions, slots), start=1):
            options = place_correct(q["options"], lambda o: o["correct"], slot, _rng)
            answers.append(AttemptAnswer(
                attempt=attempt, stage=cfg.number, position=position, question_id=q["id"],
                question_text=q["text"], points=q["points"], difficulty=q["difficulty"],
                options=[{"id": o["id"], "text": o["text"]} for o in options],
                correct_option=next(o["id"] for o in options if o["correct"]),
            ))
    AttemptStage.objects.bulk_create(stages)
    AttemptAnswer.objects.bulk_create(answers)
    attempt.max_score = sum(s.max_score for s in stages)
    attempt.question_total = len(answers)
    attempt.save(update_fields=["max_score", "question_total"])
    return attempt


# --------------------------------------------------------------------------- helpers
def get_locked_attempt(attempt_id, token) -> Attempt:
    attempt = Attempt.objects.select_for_update().filter(pk=attempt_id).first()
    if not attempt or not token_matches(attempt, token):
        raise ExamError("Test topilmadi.", "not_found", 404)
    return attempt


def _stage(attempt: Attempt, number: int) -> AttemptStage | None:
    return AttemptStage.objects.filter(attempt=attempt, number=number).first()


def _expire_if_needed(attempt: Attempt, now=None) -> bool:
    """Auto-finish stages whose time ran out. Caller must hold the row lock."""
    if attempt.status != Attempt.Status.ACTIVE:
        return False
    now = now or timezone.now()
    changed = False
    stage = _stage(attempt, attempt.current_stage)
    while stage is not None and attempt.status == Attempt.Status.ACTIVE:
        if stage.started_at and stage.finished_at is None and now > stage.deadline + grace():
            _finish_stage(attempt, stage, AttemptStage.FinishReason.TIMEOUT, now=stage.deadline)
            changed = True
        elif stage.started_at is None:
            # Waiting between stages: close the attempt if the break is too long.
            prev = _stage(attempt, stage.number - 1)
            limit = timedelta(minutes=settings.EXAM["STAGE_BREAK_MAX_MINUTES"])
            if prev and prev.finished_at and now > prev.finished_at + limit:
                _finish_stage(attempt, stage, AttemptStage.FinishReason.ABANDONED, now=now)
                changed = True
            else:
                break
        else:
            break
        stage = _stage(attempt, attempt.current_stage) if attempt.status == Attempt.Status.ACTIVE else None
    return changed


def _grade_stage(attempt: Attempt, stage: AttemptStage):
    answers = list(AttemptAnswer.objects.filter(attempt=attempt, stage=stage.number))
    score = correct = wrong = blank = 0
    for a in answers:
        if a.selected_option is None:
            a.is_correct, a.points_awarded = None, 0
            blank += 1
        elif a.selected_option == a.correct_option:
            a.is_correct, a.points_awarded = True, a.points
            correct += 1
            score += a.points
        else:
            a.is_correct, a.points_awarded = False, 0
            wrong += 1
    AttemptAnswer.objects.bulk_update(answers, ["is_correct", "points_awarded"])
    stage.score, stage.correct_count, stage.wrong_count, stage.blank_count = score, correct, wrong, blank


def _finish_stage(attempt: Attempt, stage: AttemptStage, reason, now=None):
    now = now or timezone.now()
    _grade_stage(attempt, stage)
    stage.finished_at = now
    stage.finish_reason = reason
    stage.save()

    next_stage = _stage(attempt, stage.number + 1)
    if next_stage is not None:
        attempt.current_stage = next_stage.number
        attempt.save(update_fields=["current_stage"])
    else:
        _complete_attempt(attempt, now)


def _complete_attempt(attempt: Attempt, now):
    stages = list(AttemptStage.objects.filter(attempt=attempt))
    by_number = {s.number: s for s in stages}
    s1, s2 = by_number.get(1), by_number.get(2)
    attempt.stage1_score = s1.score if s1 else 0
    attempt.stage1_correct = s1.correct_count if s1 else 0
    attempt.stage2_score = s2.score if s2 else 0
    attempt.stage2_correct = s2.correct_count if s2 else 0
    attempt.total_score = sum(s.score for s in stages)
    attempt.max_score = sum(s.max_score for s in stages)
    attempt.correct_count = sum(s.correct_count for s in stages)
    attempt.wrong_count = sum(s.wrong_count for s in stages)
    attempt.blank_count = sum(s.blank_count for s in stages)
    # Time actually spent answering (pause between stages is not counted).
    spent = 0
    for s in stages:
        if s.started_at and s.finished_at:
            spent += max(0, int((min(s.finished_at, s.deadline) - s.started_at).total_seconds()))
    attempt.duration_seconds = spent
    attempt.finished_at = now
    attempt.status = Attempt.Status.COMPLETED
    attempt.save()


def _apply_answers(attempt: Attempt, stage_number: int, items, now, strict: bool):
    """Store selections. `items` = [{"id": answer_id, "option": uuid|None}]."""
    if not items:
        return 0
    wanted = {}
    for item in items:
        wanted[int(item["id"])] = item.get("option")
    rows = list(AttemptAnswer.objects.filter(attempt=attempt, stage=stage_number, id__in=wanted.keys()))
    if strict and len(rows) != len(wanted):
        raise ExamError("Noto'g'ri savol identifikatori.", "bad_question", 400)
    changed = []
    for row in rows:
        option = wanted[row.id]
        option = str(option) if option else None
        valid_ids = {o["id"] for o in row.options}
        if option is not None and option not in valid_ids:
            if strict:
                raise ExamError("Noto'g'ri javob varianti.", "bad_option", 400)
            continue
        current = str(row.selected_option) if row.selected_option else None
        if current != option:
            row.selected_option = option
            row.answered_at = now
            changed.append(row)
    if changed:
        AttemptAnswer.objects.bulk_update(changed, ["selected_option", "answered_at"])
    return len(changed)


# --------------------------------------------------------------------------- public API
@transaction.atomic
def load_state(attempt_id, token) -> Attempt:
    attempt = get_locked_attempt(attempt_id, token)
    _expire_if_needed(attempt)
    return attempt


def save_answers(attempt_id, token, stage_number: int, items) -> Attempt:
    error = None
    with transaction.atomic():
        attempt = get_locked_attempt(attempt_id, token)
        now = timezone.now()
        _expire_if_needed(attempt, now)
        stage = _stage(attempt, stage_number)
        if attempt.status != Attempt.Status.ACTIVE:
            error = ExamError("Test yakunlangan.", "finished", 409)
        elif attempt.current_stage != stage_number:
            error = ExamError("Bu bosqich yakunlangan.", "stage_closed", 409)
        elif stage is None or stage.started_at is None:
            error = ExamError("Bosqich hali boshlanmagan.", "stage_not_started", 409)
        else:
            _apply_answers(attempt, stage_number, items, now, strict=True)
    if error:  # raised after commit so an automatic time-out is persisted
        raise error
    return attempt


@transaction.atomic
def finish_stage(attempt_id, token, stage_number: int, items) -> Attempt:
    attempt = get_locked_attempt(attempt_id, token)
    now = timezone.now()
    stage = _stage(attempt, stage_number)
    if stage is None:
        raise ExamError("Bosqich topilmadi.", "not_found", 404)
    if attempt.status != Attempt.Status.ACTIVE or stage.finished_at is not None:
        return attempt  # idempotent: a retried finish request is harmless
    if attempt.current_stage != stage_number or stage.started_at is None:
        raise ExamError("Bosqich faol emas.", "stage_closed", 409)
    in_time = now <= stage.deadline + grace()
    if in_time:
        _apply_answers(attempt, stage_number, items, now, strict=False)
        _finish_stage(attempt, stage, AttemptStage.FinishReason.SUBMITTED, now=min(now, stage.deadline))
    else:
        _finish_stage(attempt, stage, AttemptStage.FinishReason.TIMEOUT, now=stage.deadline)
    return attempt


def start_stage(attempt_id, token, stage_number: int) -> Attempt:
    error = None
    with transaction.atomic():
        attempt = get_locked_attempt(attempt_id, token)
        now = timezone.now()
        _expire_if_needed(attempt, now)
        stage = _stage(attempt, stage_number)
        if attempt.status != Attempt.Status.ACTIVE:
            error = ExamError("Test yakunlangan.", "finished", 409)
        elif stage is None or attempt.current_stage != stage_number:
            error = ExamError("Bu bosqichni boshlab bo'lmaydi.", "stage_closed", 409)
        elif stage.started_at is None:
            stage.started_at = now
            stage.deadline = now + timedelta(seconds=stage.duration_seconds)
            stage.save(update_fields=["started_at", "deadline"])
    if error:
        raise error
    return attempt


def finalize_expired(limit=500) -> int:
    """Close attempts whose time has run out (used by the Celery beat task)."""
    now = timezone.now()
    break_limit = timedelta(minutes=settings.EXAM["STAGE_BREAK_MAX_MINUTES"])
    candidates = set(
        AttemptStage.objects.filter(
            attempt__status=Attempt.Status.ACTIVE, started_at__isnull=False, finished_at__isnull=True,
            deadline__lt=now - grace(),
        ).values_list("attempt_id", flat=True)[:limit]
    )
    candidates |= set(
        AttemptStage.objects.filter(
            attempt__status=Attempt.Status.ACTIVE, started_at__isnull=True,
            number__gt=1,
        ).filter(
            attempt__stages__finished_at__lt=now - break_limit,
        ).values_list("attempt_id", flat=True)[:limit]
    )
    done = 0
    for attempt_id in candidates:
        with transaction.atomic():
            attempt = Attempt.objects.select_for_update(skip_locked=True).filter(pk=attempt_id).first()
            if attempt and _expire_if_needed(attempt, now):
                done += 1
    return done


# --------------------------------------------------------------------------- serialisation
def serialize_state(attempt: Attempt) -> dict:
    site = SiteSettings.load()
    stages = list(AttemptStage.objects.filter(attempt=attempt).order_by("number"))
    data = {
        "id": str(attempt.id),
        "status": attempt.status,
        "first_name": attempt.first_name,
        "last_name": attempt.last_name,
        "branch": attempt.branch.name,
        "subject": str(attempt.subject),
        "current_stage": attempt.current_stage,
        "server_time": timezone.now().isoformat(),
        "stages": [
            {
                "number": s.number, "title": s.title, "question_count": s.question_count,
                "duration_seconds": s.duration_seconds,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "deadline": s.deadline.isoformat() if s.deadline else None,
                "finished": s.finished_at is not None,
                "finish_reason": s.finish_reason or None,
            }
            for s in stages
        ],
        "questions": [],
        "result": None,
        "review": None,
    }
    if attempt.status == Attempt.Status.ACTIVE:
        current = next((s for s in stages if s.number == attempt.current_stage), None)
        # Questions of a stage are only sent once that stage is running.
        if current and current.started_at and not current.finished_at:
            rows = AttemptAnswer.objects.filter(attempt=attempt, stage=current.number).only(
                "id", "position", "question_text", "options", "selected_option"
            ).order_by("position")
            data["questions"] = [
                {
                    "id": r.id, "position": r.position, "text": r.question_text, "options": r.options,
                    "selected": str(r.selected_option) if r.selected_option else None,
                }
                for r in rows
            ]
    elif attempt.status == Attempt.Status.COMPLETED:
        if site.show_score:
            data["result"] = {
                "total_score": attempt.total_score, "max_score": attempt.max_score,
                "percent": attempt.percent, "correct": attempt.correct_count,
                "wrong": attempt.wrong_count, "blank": attempt.blank_count,
                "question_total": attempt.question_total,
                "stages": [
                    {"number": s.number, "title": s.title, "score": s.score, "max_score": s.max_score,
                     "correct": s.correct_count, "total": s.question_count}
                    for s in stages
                ],
            }
        if site.show_answer_review:
            rows = AttemptAnswer.objects.filter(attempt=attempt).order_by("stage", "position")
            data["review"] = [
                {
                    "stage": r.stage, "position": r.position, "text": r.question_text, "options": r.options,
                    "selected": str(r.selected_option) if r.selected_option else None,
                    "correct": str(r.correct_option),
                }
                for r in rows
            ]
    return data
