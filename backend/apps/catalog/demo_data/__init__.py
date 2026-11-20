"""Initial content: branches, the subject list, the academic bank and the question banks.

Stage 1 of every subject is the shared academic test (questions from the academic
bank). Stage 2 is the subject's own test. "Boshqa" has only the academic test.
"""
from . import (academic, arabic, biology, chemistry, english, history, it_backend, it_frontend, korean, math,
               mental, mother_tongue, nursing, primary, russian, turkish)

BRANCHES = [
    ("Niyozbosh", ""),
    ("Xalqabod", ""),
    ("Gulbahor", ""),
    ("Kasblar", ""),
    ("Kids 1", ""),
    ("Kids 2", ""),
    ("Do‘stobod", ""),
    ("Olmazor", ""),
    ("Chinoz", ""),
    ("Krasin", ""),
    ("Pitiletka", ""),
    ("Qo‘rg‘oncha", ""),
    ("Kids 3", ""),
    ("Oqqo‘rg‘on", ""),
    ("Qo‘shyog‘och", ""),
]

ACADEMIC = ("academic", "Akademik test", "Barcha fanlar uchun umumiy 1-bosqich savollari", "academic", academic)

# slug, name, description, icon, question module (None = academic test only)
SUBJECTS = [
    ("english", "Ingliz tili", "Grammatika, lug'at va o'qitish metodikasi", "english", english),
    ("russian", "Rus tili", "Leksika, grammatika va nutq madaniyati", "russian", russian),
    ("arabic", "Arab tili", "Nahv, sarf, balog'at va metodika", "arabic", arabic),
    ("korean", "Koreys tili", "TOPIK II: grammatika, lug'at, o'qish", "korean", korean),
    ("uzbek", "Ona tili", "O'zbek tili va adabiyoti", "uzbek", mother_tongue),
    ("turkish", "Turk tili", "Dil bilgisi, söz varlığı va metodika", "turkish", turkish),
    ("chemistry", "Kimyo", "Umumiy, anorganik va organik kimyo", "chemistry", chemistry),
    ("biology", "Biologiya", "Genetika, sitologiya, odam va ekologiya", "biology", biology),
    ("math", "Matematika", "Algebra, geometriya va analiz asoslari", "math", math),
    ("mental", "Mental arifmetika", "Abakus, og'zaki hisob va metodika", "mental", mental),
    ("it-frontend", "IT (Frontend)", "HTML, CSS, JavaScript, React", "frontend", it_frontend),
    ("it-backend", "IT (Backend)", "HTTP, SQL, Node.js/Python, xavfsizlik", "backend", it_backend),
    ("nursing", "Hamshiralik", "Hamshiralik ishi va birinchi tez yordam", "nursing", nursing),
    ("primary", "Boshlang'ich ta'lim", "Ona tili va matematika metodikasi, tarbiya", "primary", primary),
    ("history", "Tarix", "O'zbekiston va jahon tarixi", "history", history),
    ("other", "Boshqa", "Faqat akademik test (1 bosqich)", "other", None),
]

ACADEMIC_STAGE = {"number": 1, "title": "Akademik test", "question_count": 20, "duration_minutes": 25,
                  "source": "academic", "is_enabled": True}
SUBJECT_STAGE = {"number": 2, "title": "Fan testi", "question_count": 30, "duration_minutes": 40,
                 "source": "subject", "is_enabled": True}

POINTS = {1: 1, 2: 1}  # every question is worth 1 point


BANK_SIZE = 30  # questions per subject on the platform (stage 2 asks all 30, shuffled)


def _spread(seq, n):
    """Pick n items evenly across seq, so every topic block keeps some questions."""
    if n >= len(seq):
        return list(seq)
    if n <= 0:
        return []
    step = len(seq) / n
    return [seq[int(i * step)] for i in range(n)]


def all_items(module):
    """Every question written for a module, before the 30-question selection."""
    out = []
    for text, options, correct in module.ORIGINAL:
        out.append(("medium", text, list(options), correct))
    for text, correct, *wrong in module.EXTRA:
        out.append(("hard", text, [correct, *wrong], 0))
    return out


def items(module, limit=BANK_SIZE):
    """The questions that go on the platform, as (difficulty, text, options, correct index).

    Exactly `limit` per bank: the harder new questions first, topped up with questions from the
    supplied file (spread evenly over the file, so all its topics stay covered).
    """
    original = [("medium", t, list(o), c) for t, o, c in module.ORIGINAL]
    extra = [("hard", t, [c, *w], 0) for t, c, *w in module.EXTRA]
    chosen_extra = _spread(extra, limit)
    return chosen_extra + _spread(original, limit - len(chosen_extra))


def all_banks():
    yield ACADEMIC[0], ACADEMIC[4]
    for slug, *_rest, module in SUBJECTS:
        if module is not None:
            yield slug, module


def validate():
    """Sanity checks for the question banks (also run by the test suite)."""
    problems = []
    for slug, module in all_banks():
        seen = set()
        for i, (_diff, text, options, correct) in enumerate(all_items(module), start=1):
            where = f"{slug} #{i} ({text[:40]!r})"
            if not text.strip():
                problems.append(f"{where}: empty question")
            if not 2 <= len(options) <= 6:
                problems.append(f"{where}: 2-6 options expected")
            if len({o.strip().casefold() for o in options}) != len(options) or not all(o.strip() for o in options):
                problems.append(f"{where}: options must be unique and non-empty")
            if not 0 <= correct < len(options):
                problems.append(f"{where}: bad correct index")
            if len(text) > 2000 or any(len(o) > 500 for o in options):
                problems.append(f"{where}: text too long")
            key = " ".join(text.split()).casefold()
            if key in seen:
                problems.append(f"{where}: duplicate question")
            seen.add(key)
    return problems
