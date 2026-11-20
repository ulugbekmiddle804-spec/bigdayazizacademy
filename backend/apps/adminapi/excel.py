"""Excel (xlsx) export of results and import/export of the question bank."""
import io
from datetime import datetime

from django.db import transaction
from django.utils import timezone
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from apps.catalog.models import Option, Question, Subject

LETTERS = "ABCDEF"
HEADER_FILL = PatternFill("solid", fgColor="4F46E5")
HEADER_FONT = Font(bold=True, color="FFFFFF")
STATUS_LABELS = {"active": "Jarayonda", "completed": "Yakunlangan", "annulled": "Bekor qilingan"}
DIFFICULTY_IN = {
    "oson": "easy", "easy": "easy",
    "o'rta": "medium", "orta": "medium", "o‘rta": "medium", "medium": "medium",
    "qiyin": "hard", "hard": "hard",
}
DIFFICULTY_OUT = {"easy": "oson", "medium": "o'rta", "hard": "qiyin"}
QUESTION_HEADERS = ["Fan kodi", "Bosqich", "Savol", "A", "B", "C", "D", "E", "F", "To'g'ri javob", "Ball",
                    "Qiyinlik", "Faol"]


def safe(value):
    """Identity marker for user-provided text; see `append_row`."""
    return value


def append_row(ws, values):
    """Append a row and make sure no user text is stored as a formula.

    openpyxl treats strings starting with '=' as formulas; forcing the cell type
    to string prevents spreadsheet formula injection without altering the text.
    """
    ws.append(values)
    for cell in ws[ws.max_row]:
        if cell.data_type == "f":
            cell.data_type = "s"


def local(dt):
    if not dt:
        return None
    return timezone.localtime(dt).replace(tzinfo=None)


def fmt_duration(seconds):
    if seconds is None:
        return ""
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def _style_header(ws, widths):
    for idx, width in enumerate(widths, start=1):
        cell = ws.cell(row=1, column=idx)
        cell.fill, cell.font = HEADER_FILL, HEADER_FONT
        cell.alignment = Alignment(vertical="center", wrap_text=True)
        ws.column_dimensions[get_column_letter(idx)].width = width
    ws.freeze_panes = "A2"


def _to_bytes(wb) -> bytes:
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def subject_label(s):
    return f"{s.parent.name} — {s.name}" if s.parent_id else s.name


def export_attempts(queryset, include_answers=False) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Natijalar"
    headers = ["№", "Familiya", "Ism", "Filial", "Fan", "Holat", "Boshlangan", "Tugagan", "Sarflangan vaqt",
               "1-bosqich ball", "1-bosqich to'g'ri", "1-bosqich %", "2-bosqich ball", "2-bosqich to'g'ri",
               "2-bosqich %", "Umumiy ball", "Maks. ball", "Umumiy %", "To'g'ri", "Noto'g'ri", "Bo'sh", "Savollar"]
    ws.append(headers)
    _style_header(ws, [6, 18, 16, 20, 26, 14, 19, 19, 14, 12, 12, 11, 12, 12, 11, 12, 11, 10, 9, 10, 8, 10])
    attempts = list(queryset.select_related("branch", "subject", "subject__parent").prefetch_related("stages"))
    for i, a in enumerate(attempts, start=1):
        append_row(ws, [
            i, safe(a.last_name), safe(a.first_name), safe(a.branch.name), safe(subject_label(a.subject)),
            STATUS_LABELS.get(a.status, a.status), local(a.started_at), local(a.finished_at),
            fmt_duration(a.duration_seconds), a.stage1_score, a.stage1_correct, a.stage_percent(1),
            a.stage2_score, a.stage2_correct, a.stage_percent(2),
            a.total_score, a.max_score, a.percent, a.correct_count, a.wrong_count, a.blank_count, a.question_total,
        ])
    for row in ws.iter_rows(min_row=2, min_col=7, max_col=8):
        for cell in row:
            cell.number_format = "dd.mm.yyyy hh:mm"
    ws.auto_filter.ref = ws.dimensions

    if include_answers:
        ws2 = wb.create_sheet("Javoblar")
        ws2.append(["Familiya", "Ism", "Fan", "Bosqich", "№", "Savol", "Tanlangan javob", "To'g'ri javob",
                    "Natija", "Ball"])
        _style_header(ws2, [18, 16, 24, 9, 6, 60, 30, 30, 12, 7])
        from apps.exams.models import AttemptAnswer

        by_id = {a.id: a for a in attempts}
        rows = AttemptAnswer.objects.filter(attempt_id__in=by_id.keys()).order_by("attempt_id", "stage", "position")
        for r in rows.iterator(chunk_size=2000):
            a = by_id[r.attempt_id]
            texts = {o["id"]: o["text"] for o in r.options}
            selected = texts.get(str(r.selected_option), "") if r.selected_option else ""
            result = "Bo'sh" if r.selected_option is None else ("To'g'ri" if r.is_correct else "Noto'g'ri")
            if a.status == "active":
                result = "Jarayonda"
            append_row(ws2, [safe(a.last_name), safe(a.first_name), safe(subject_label(a.subject)), r.stage, r.position,
                        safe(r.question_text), safe(selected), safe(texts.get(str(r.correct_option), "")),
                        result, r.points_awarded])
    return _to_bytes(wb)


def export_questions(queryset) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Savollar"
    ws.append(QUESTION_HEADERS)
    _style_header(ws, [16, 8, 60, 24, 24, 24, 24, 18, 18, 12, 7, 10, 7])
    for q in queryset.select_related("subject").prefetch_related("options"):
        opts = list(q.options.all())[:6]
        cells = [safe(o.text) for o in opts] + [None] * (6 - len(opts))
        correct = next((LETTERS[i] for i, o in enumerate(opts) if o.is_correct), "")
        append_row(ws, [q.subject.slug, q.stage, safe(q.text), *cells, correct, q.points,
                   DIFFICULTY_OUT.get(q.difficulty, q.difficulty), "ha" if q.is_active else "yo'q"])
    return _to_bytes(wb)


def question_template() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Savollar"
    ws.append(QUESTION_HEADERS)
    _style_header(ws, [16, 8, 60, 24, 24, 24, 24, 18, 18, 12, 7, 10, 7])
    ws.append(["math", 1, "5 + 7 = ?", "12", "11", "13", "10", None, None, "A", 1, "oson", "ha"])
    info = wb.create_sheet("Yo'riqnoma")
    for line in [
        "Fan kodi — admin paneldagi fan kodi (masalan: english, math, it-frontend).",
        "Bosqich — 1 yoki 2.",
        "A–F — javob variantlari (kamida 2 ta).",
        "To'g'ri javob — to'g'ri variant harfi (A, B, C ...).",
        "Ball — 1 dan 100 gacha butun son (bo'sh bo'lsa 1).",
        "Qiyinlik — oson / o'rta / qiyin (bo'sh bo'lsa o'rta).",
        "Faol — ha / yo'q (bo'sh bo'lsa ha).",
    ]:
        info.append([line])
    info.column_dimensions["A"].width = 90
    return _to_bytes(wb)


class ImportErrorList(Exception):
    def __init__(self, errors):
        super().__init__("import failed")
        self.errors = errors


def _cell_str(v):
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    if isinstance(v, datetime):
        return v.isoformat()
    return str(v).strip()


def import_questions(fileobj) -> int:
    """Validate every row first; import all rows or none."""
    try:
        wb = load_workbook(fileobj, read_only=True, data_only=True)
    except Exception:
        raise ImportErrorList([{"row": 0, "error": "Fayl o'qilmadi. .xlsx formatidagi faylni yuklang."}])
    ws = wb.worksheets[0]
    subjects = {s.slug: s for s in Subject.objects.all()}
    group_ids = set(Subject.objects.filter(parent__isnull=False).values_list("parent_id", flat=True))
    errors, parsed = [], []
    for idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        row = list(row) + [None] * 13
        values = [_cell_str(v) for v in row[:13]]
        if not any(values):
            continue
        slug, stage, text = values[0], values[1], values[2]
        options = [v for v in values[3:9]]
        correct, points, difficulty, active = values[9].upper(), values[10], values[11].lower(), values[12].lower()
        row_errors = []
        subject = subjects.get(slug)
        if not subject:
            row_errors.append(f"'{slug}' kodli fan topilmadi")
        elif subject.id in group_ids:
            row_errors.append("Fan guruh, aniq yo'nalish kodini kiriting")
        if stage not in ("1", "2"):
            row_errors.append("Bosqich 1 yoki 2 bo'lsin")
        if len(text) < 3:
            row_errors.append("Savol matni bo'sh")
        filled = [(LETTERS[i], o) for i, o in enumerate(options) if o]
        if len(filled) < 2:
            row_errors.append("Kamida 2 ta javob varianti kerak")
        if len({o.casefold() for _, o in filled}) != len(filled):
            row_errors.append("Javob variantlari takrorlanmoqda")
        if correct not in {letter for letter, _ in filled}:
            row_errors.append("To'g'ri javob harfi noto'g'ri yoki o'sha variant bo'sh")
        try:
            points_val = int(points or 1)
            if not 1 <= points_val <= 100:
                raise ValueError
        except ValueError:
            row_errors.append("Ball 1–100 oralig'idagi son bo'lsin")
            points_val = 1
        diff = DIFFICULTY_IN.get(difficulty or "o'rta")
        if not diff:
            row_errors.append("Qiyinlik: oson / o'rta / qiyin")
        if any(len(o) > 500 for _, o in filled) or len(text) > 2000:
            row_errors.append("Matn juda uzun")
        if row_errors:
            errors.append({"row": idx, "error": "; ".join(row_errors)})
            continue
        parsed.append({
            "subject": subject, "stage": int(stage), "text": text, "points": points_val, "difficulty": diff,
            "is_active": active not in ("yo'q", "yoq", "no", "0", "false"),
            "options": [(o, letter == correct) for letter, o in filled],
        })
    if errors:
        raise ImportErrorList(errors[:200])
    if not parsed:
        raise ImportErrorList([{"row": 0, "error": "Faylda savollar topilmadi."}])
    with transaction.atomic():
        for item in parsed:
            options = item.pop("options")
            q = Question.objects.create(**item)
            Option.objects.bulk_create(
                [Option(question=q, text=t, is_correct=c, sort_order=i) for i, (t, c) in enumerate(options)]
            )
    return len(parsed)
