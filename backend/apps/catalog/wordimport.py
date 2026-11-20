"""Parse a test written in Word (.docx) into questions.

Supported layout (the same one teachers already use):

    1. Question text            <- "1." or "1)"; extra lines (code, a passage) are kept
    A) option                   <- A–F, Cyrillic А–Е, ①–⑥ or a), b) ...
    B) option
    ...
    JAVOBLAR KALITI             <- optional heading
    | 1 | 2 | 3 |  ...          <- key as a table (number row + letter row)
    | A | C | B |  ...             or as text: "1-A, 2-C", "1) A", "1.A"

Instead of a key, the correct option may be marked inline with a leading "*"
or "+", e.g. "*B) option" / "+B) option".

The parser never touches the database: it returns the questions plus a list of
problems with question numbers, so the caller can import all-or-nothing.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from docx import Document
from docx.oxml.ns import qn

MAX_OPTIONS = 6

# Option label alphabets. A question's options must follow one of them in order
# (A, B, C... / а, б, в... / ①, ②...); the answer key is read with the same one.
_SEQUENCES = {
    "latin": "abcdef",
    "cyr_lookalike": "авсdеf",   # Cyrillic А, В, С typed instead of Latin A, B, C
    "russian": "абвгде",
    "circled": "①②③④⑤⑥",
    "arabic": "أبجدهو",
}
_LABEL_CHARS = "".join(sorted(set("".join(_SEQUENCES.values()) + "".join(_SEQUENCES.values()).upper())))

_QUESTION_RE = re.compile(r"^\s*(\d{1,3})\s*[.)]\s*(\S.*)$", re.S)
_OPTION_RE = re.compile(r"^\s*([*+])?\s*([" + re.escape(_LABEL_CHARS) + r"])\s*[).]\s*(.*)$", re.S)
_KEY_HEADING_RE = re.compile(
    r"(kalit|калит|ключ|answer\s*key|key\b|정답|مفتاح|anahtar|javoblar|жавоблар|ответ)", re.I
)
_KEY_PAIR_RE = re.compile(r"(\d{1,3})\s*[-–—.:)=]?\s*([" + re.escape(_LABEL_CHARS) + r"])(?![A-Za-zА-Яа-я])")
_EASTERN_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


@dataclass
class ParsedQuestion:
    number: int
    text: str
    options: list[str] = field(default_factory=list)
    correct: int | None = None
    sequences: list[str] = field(default_factory=lambda: list(_SEQUENCES))


@dataclass
class ParseResult:
    title: str = ""
    questions: list[ParsedQuestion] = field(default_factory=list)
    problems: list[dict] = field(default_factory=list)


def _blocks(document):
    """Yield ('p', text) for paragraphs and ('t', rows) for tables in body order."""
    body = document.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            yield "p", _paragraph_text(child)
        elif child.tag == qn("w:tbl"):
            rows = []
            for tr in child.iter(qn("w:tr")):
                rows.append([_paragraph_text_all(tc) for tc in tr.iter(qn("w:tc"))])
            yield "t", rows


def _paragraph_text(p) -> str:
    parts = []
    for node in p.iter(qn("w:t"), qn("w:tab"), qn("w:br")):
        if node.tag == qn("w:t"):
            parts.append(node.text or "")
        elif node.tag == qn("w:tab"):
            parts.append(" ")
        else:
            parts.append("\n")
    return "".join(parts)


def _paragraph_text_all(tc) -> str:
    return " ".join(_paragraph_text(p) for p in tc.iter(qn("w:p"))).strip()


def _matching_sequences(label: str, position: int, candidates) -> list[str]:
    label = label.casefold()
    return [name for name in candidates
            if position < len(_SEQUENCES[name]) and _SEQUENCES[name][position] == label]


_LOOKALIKE_FAMILY = ("latin", "cyr_lookalike")  # A/А, B/В, C/С look the same; a key may use either


def _label_index(label: str, sequences) -> int | None:
    label = label.casefold()
    names = list(sequences)
    if any(n in _LOOKALIKE_FAMILY for n in names):
        names += [n for n in _LOOKALIKE_FAMILY if n not in names]
    for name in names:
        if label in _SEQUENCES[name]:
            return _SEQUENCES[name].index(label)
    return None


def _parse_key_text(text: str, key: dict[int, str]):
    for num, label in _KEY_PAIR_RE.findall(text.translate(_EASTERN_DIGITS)):
        key.setdefault(int(num), label)


def _parse_key_table(rows: list[list[str]], key: dict[int, str]):
    rows = [[c.translate(_EASTERN_DIGITS).strip() for c in r] for r in rows]
    rows = [r for r in rows if any(r)]
    i = 0
    while i < len(rows):
        row = rows[i]
        if all(re.fullmatch(r"\d{1,3}", c) for c in row if c) and i + 1 < len(rows):
            letters = rows[i + 1]
            for num, label in zip(row, letters):
                label = label.strip().rstrip(")").strip()
                if num and len(label) == 1 and label in _LABEL_CHARS:
                    key.setdefault(int(num), label)
            i += 2
            continue
        # Two-column layout: | 1 | A |  or single cells like "1-A".
        _parse_key_text("  ".join(row), key)
        i += 1


def parse_docx(fileobj) -> ParseResult:
    try:
        document = Document(fileobj)
    except Exception:
        return ParseResult(problems=[{"question": 0, "error": "Fayl o'qilmadi. .docx formatidagi Word faylni yuklang."}])
    return parse_blocks(_blocks(document))


def parse_blocks(blocks) -> ParseResult:
    result = ParseResult()
    current: ParsedQuestion | None = None
    in_key = False
    key: dict[int, str] = {}
    inline_marks: dict[int, list[int]] = {}

    def close():
        if current is not None:
            current.text = current.text.strip()
            current.options = [o.strip() for o in current.options]
            result.questions.append(current)

    for kind, value in blocks:
        if kind == "t":
            # Tables before the first question are ignored (headers, logos); after it they are the key.
            if result.questions or current is not None:
                if current is not None and len(current.options) >= 2:
                    close()
                    current = None
                    in_key = True
                if in_key:
                    _parse_key_table(value, key)
            continue

        for line in value.split("\n"):
            raw = line.rstrip()
            text = raw.strip()
            if not text:
                continue
            if in_key:
                _parse_key_text(text, key)
                continue
            have_question = current is not None
            options_started = have_question and len(current.options) > 0
            if have_question and len(current.options) >= 2 and _KEY_HEADING_RE.search(text) \
                    and not _OPTION_RE.match(text) and not _QUESTION_RE.match(text):
                close()
                current = None
                in_key = True
                _parse_key_text(text, key)
                continue

            q_match = _QUESTION_RE.match(text.translate(_EASTERN_DIGITS))
            expected = (result.questions[-1].number + 1) if result.questions else None
            if q_match:
                number = int(q_match.group(1))
                starts_new = (
                    current is None and (expected is None or number == expected)
                ) or (
                    current is not None and len(current.options) >= 2 and number == current.number + 1
                )
                if starts_new:
                    close()
                    current = ParsedQuestion(number=number, text=q_match.group(2))
                    continue

            o_match = _OPTION_RE.match(text)
            if have_question and o_match:
                mark, label, body = o_match.groups()
                idx = len(current.options)
                seqs = _matching_sequences(label, idx, current.sequences)
                if seqs and body.strip():
                    current.sequences = seqs
                    if mark:
                        inline_marks.setdefault(current.number, []).append(idx)
                    current.options.append(body)
                    continue

            if not have_question:
                if not result.title:
                    result.title = text
                continue
            if options_started:
                # A wrapped option line: glue it to the last option.
                current.options[-1] += " " + text
            else:
                current.text += "\n" + raw.rstrip()
    if current is not None and not in_key:
        close()

    numbers = [q.number for q in result.questions]
    for q in result.questions:
        if q.number in inline_marks:
            marks = inline_marks[q.number]
            if len(marks) == 1:
                q.correct = marks[0]
            else:
                result.problems.append({"question": q.number, "error": "Bir nechta variant to'g'ri deb belgilangan"})
        if q.number in key:
            from_key = _label_index(key[q.number], q.sequences)
            if from_key is None:
                result.problems.append({"question": q.number, "error": f"Kalitdagi '{key[q.number]}' javobi tanilmadi"})
                continue
            if q.correct is not None and q.correct != from_key:
                result.problems.append({"question": q.number,
                                        "error": "Belgilangan javob kalitdagi javobga mos emas"})
            q.correct = from_key

    for q in result.questions:
        problems = []
        if len(q.text) < 2:
            problems.append("Savol matni bo'sh")
        if len(q.options) < 2:
            problems.append("Kamida 2 ta javob varianti kerak")
        if len(q.options) > MAX_OPTIONS:
            problems.append(f"Ko'pi bilan {MAX_OPTIONS} ta variant bo'lishi mumkin")
        if len({o.casefold() for o in q.options}) != len(q.options):
            problems.append("Javob variantlari takrorlanmoqda")
        if q.correct is None:
            problems.append("To'g'ri javob ko'rsatilmagan (kalitda yo'q)")
        elif q.correct >= len(q.options):
            problems.append("Kalitdagi javob harfiga mos variant yo'q")
        if len(q.text) > 2000 or any(len(o) > 500 for o in q.options):
            problems.append("Matn juda uzun")
        for p in problems:
            result.problems.append({"question": q.number, "error": p})
    if len(set(numbers)) != len(numbers):
        result.problems.append({"question": 0, "error": "Savol raqamlari takrorlanmoqda"})
    extra = sorted(set(key) - set(numbers))
    if extra and result.questions:
        result.problems.append({"question": 0, "error": f"Kalitda ortiqcha raqamlar bor: {extra[:10]}"})
    if not result.questions and not result.problems:
        result.problems.append({"question": 0, "error": "Faylda savollar topilmadi. Namuna faylga qarang."})
    result.problems.sort(key=lambda p: p["question"])
    return result
