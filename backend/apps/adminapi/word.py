"""Attach questions to a subject from a Word (.docx) file, and a sample file for admins."""
import io

from django.db import transaction
from docx import Document
from docx.shared import Pt

from apps.catalog.models import Option, Question
from apps.catalog.wordimport import parse_docx

MAX_QUESTIONS = 1000
LETTERS = "ABCDEF"


def import_word(fileobj, *, subject, stage: int, points: int, difficulty: str, replace: bool,
                preview: bool) -> dict:
    """Parse the file; unless `preview`, save every question or none.

    Returns {"title", "count", "problems", "questions"(preview only), "created", "replaced"}.
    """
    result = parse_docx(fileobj)
    out = {"title": result.title, "count": len(result.questions), "problems": result.problems}
    if len(result.questions) > MAX_QUESTIONS:
        out["problems"] = out["problems"] + [{"question": 0, "error": f"Bitta faylda ko'pi bilan {MAX_QUESTIONS} ta savol"}]
    if preview:
        out["questions"] = [
            {"number": q.number, "text": q.text, "options": q.options, "correct": q.correct}
            for q in result.questions[:300]
        ]
        return out
    if out["problems"]:
        return out
    with transaction.atomic():
        replaced = 0
        if replace:
            replaced, _ = Question.objects.filter(subject=subject, stage=stage).delete()
        for q in result.questions:
            question = Question.objects.create(subject=subject, stage=stage, text=q.text, points=points,
                                               difficulty=difficulty)
            Option.objects.bulk_create([
                Option(question=question, text=text, is_correct=(i == q.correct), sort_order=i)
                for i, text in enumerate(q.options)
            ])
    out.update(created=len(result.questions), replaced=replaced)
    return out


def word_template() -> bytes:
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)
    doc.add_heading("FAN NOMI — TEST", level=1)
    doc.add_paragraph(
        "Qoidalar: har bir savol raqam va nuqta bilan boshlanadi (1. 2. 3.). Variantlar A) B) C) D) "
        "(E, F ham mumkin) ko'rinishida alohida qatorda yoziladi. Savol matni bir necha qatordan iborat "
        "bo'lishi mumkin (masalan, kod yoki matn parchasi). To'g'ri javob oxiridagi kalit jadvalida "
        "ko'rsatiladi yoki variant oldiga * belgisi qo'yiladi (*B) ...). Bu izohli qatorni o'chirib "
        "yuborishingiz mumkin."
    )
    sample = [
        ("Quyidagilardan qaysi biri tub son?", ["21", "27", "29", "33"], 2),
        ("Quyidagi kodning natijasi qanday?\nconsole.log(2 + '2');", ["4", "22", "NaN", "Xato"], 1),
        ("O'zbekiston poytaxti qaysi shahar?", ["Samarqand", "Buxoro", "Toshkent", "Xiva"], 2),
    ]
    for n, (text, options, _correct) in enumerate(sample, start=1):
        lines = text.split("\n")
        doc.add_paragraph(f"{n}. {lines[0]}")
        for line in lines[1:]:
            doc.add_paragraph(line)
        for i, opt in enumerate(options):
            doc.add_paragraph(f"{LETTERS[i]}) {opt}")
    doc.add_paragraph("JAVOBLAR KALITI")
    table = doc.add_table(rows=2, cols=len(sample))
    table.style = "Table Grid"
    for i, (_t, _o, correct) in enumerate(sample):
        table.cell(0, i).text = str(i + 1)
        table.cell(1, i).text = LETTERS[correct]
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
