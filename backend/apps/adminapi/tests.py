import io

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from openpyxl import Workbook, load_workbook
from rest_framework.test import APIClient

from apps.catalog.models import Branch, Question, Subject
from apps.exams.models import Attempt


class AdminApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)
        User = get_user_model()
        cls.admin = User.objects.create_user("boss", password="S3cure-pass!", is_staff=True)
        cls.user = User.objects.create_user("user", password="S3cure-pass!")

    def setUp(self):
        cache.clear()
        self.client = APIClient(enforce_csrf_checks=True)

    def login(self):
        self.client.get("/api/admin/auth/csrf/")
        csrf = self.client.cookies["csrftoken"].value
        res = self.client.post("/api/admin/auth/login/", {"username": "boss", "password": "S3cure-pass!"},
                               format="json", HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(res.status_code, 200, res.data)
        self.csrf = self.client.cookies["csrftoken"].value
        return res

    def make_attempt(self, first="Ali", last="Valiyev"):
        public = APIClient()
        res = public.post("/api/attempts/", {"first_name": first, "last_name": last,
                                             "branch_id": Branch.objects.first().id,
                                             "subject_id": Subject.objects.get(slug="english").id}, format="json")
        token, attempt_id = res.data["token"], res.data["state"]["id"]
        h = {"HTTP_X_ATTEMPT_TOKEN": token}
        public.post(f"/api/attempts/{attempt_id}/stages/1/finish/", {}, format="json", **h)
        public.post(f"/api/attempts/{attempt_id}/stages/2/start/", {}, format="json", **h)
        public.post(f"/api/attempts/{attempt_id}/stages/2/finish/", {}, format="json", **h)
        return attempt_id

    def test_admin_endpoints_require_staff(self):
        self.assertEqual(self.client.get("/api/admin/attempts/").status_code, 403)
        self.assertEqual(self.client.get("/api/admin/auth/me/").status_code, 401)
        plain = APIClient()
        plain.force_login(self.user)
        self.assertEqual(plain.get("/api/admin/dashboard/").status_code, 403)

    def test_login_rejects_bad_password_and_non_staff(self):
        self.client.get("/api/admin/auth/csrf/")
        csrf = self.client.cookies["csrftoken"].value
        bad = self.client.post("/api/admin/auth/login/", {"username": "boss", "password": "x"}, format="json",
                               HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(bad.status_code, 400)
        non_staff = self.client.post("/api/admin/auth/login/", {"username": "user", "password": "S3cure-pass!"},
                                     format="json", HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(non_staff.status_code, 400)

    def test_csrf_is_enforced_for_admin_writes(self):
        self.login()
        res = self.client.post("/api/admin/branches/", {"name": "Yangi filial"}, format="json")
        self.assertEqual(res.status_code, 403)
        ok = self.client.post("/api/admin/branches/", {"name": "Yangi filial"}, format="json",
                              HTTP_X_CSRFTOKEN=self.csrf)
        self.assertEqual(ok.status_code, 201)

    def test_results_list_search_filter_sort_and_detail(self):
        a1 = self.make_attempt("Ali", "Valiyev")
        self.make_attempt("Bobur", "Karimov")
        Attempt.objects.filter(pk=a1).update(total_score=50)
        self.login()
        res = self.client.get("/api/admin/attempts/?last_name=kar")
        self.assertEqual(res.data["count"], 1)
        res = self.client.get("/api/admin/attempts/?ordering=-total_score")
        self.assertEqual(res.data["results"][0]["id"], a1)
        res = self.client.get(f"/api/admin/attempts/?subject={Subject.objects.get(slug='math').id}")
        self.assertEqual(res.data["count"], 0)
        detail = self.client.get(f"/api/admin/attempts/{a1}/")
        self.assertEqual(len(detail.data["answers"]), 50)
        self.assertIn("correct_option", detail.data["answers"][0])
        self.assertEqual(detail.data["answers"][0]["result"], "blank")

    def test_excel_export(self):
        self.make_attempt()
        self.login()
        res = self.client.get("/api/admin/attempts/export/?answers=1")
        self.assertEqual(res.status_code, 200)
        wb = load_workbook(io.BytesIO(res.content))
        self.assertEqual(wb.sheetnames, ["Natijalar", "Javoblar"])
        self.assertEqual(wb["Natijalar"].max_row, 2)
        self.assertEqual(wb["Javoblar"].max_row, 51)

    def test_list_has_stage_percents(self):
        self.make_attempt()
        self.login()
        row = self.client.get("/api/admin/attempts/").data["results"][0]
        self.assertEqual(row["stage1_percent"], 0.0)  # submitted without answers
        self.assertEqual(row["stage2_percent"], 0.0)
        self.assertEqual(row["percent"], 0.0)
        self.assertEqual(row["stage_count"], 2)

    def test_bulk_delete_selected_and_all(self):
        a = self.make_attempt("Ali", "Valiyev")
        b = self.make_attempt("Vali", "Aliyev")
        c = self.make_attempt("Soli", "Karimov")
        self.login()
        url = "/api/admin/attempts/bulk-delete/"
        res = self.client.post(url, {"ids": [a]}, format="json", HTTP_X_CSRFTOKEN=self.csrf)
        self.assertEqual(res.data["deleted"], 1)
        # "all" needs the confirmation word and respects the list filters
        res = self.client.post(url, {"all": True}, format="json", HTTP_X_CSRFTOKEN=self.csrf)
        self.assertEqual(res.status_code, 400)
        res = self.client.post(url + "?last_name=Karim", {"all": True, "confirm": "DELETE"}, format="json",
                               HTTP_X_CSRFTOKEN=self.csrf)
        self.assertEqual(res.data["deleted"], 1)
        self.assertEqual(list(Attempt.objects.values_list("id", flat=True)), [__import__("uuid").UUID(b)])
        res = self.client.post(url, {"all": True, "confirm": "DELETE"}, format="json", HTTP_X_CSRFTOKEN=self.csrf)
        self.assertEqual(res.data["deleted"], 1)
        self.assertFalse(Attempt.objects.exists())
        self.assertEqual(self.client.post(url, {"ids": ["bad"]}, format="json",
                                          HTTP_X_CSRFTOKEN=self.csrf).status_code, 400)

    def test_allow_retake_and_annul(self):
        attempt_id = self.make_attempt()
        self.login()
        res = self.client.post(f"/api/admin/attempts/{attempt_id}/allow-retake/", {"allowed": True},
                               format="json", HTTP_X_CSRFTOKEN=self.csrf)
        self.assertTrue(res.data["retake_allowed"])
        res = self.client.post(f"/api/admin/attempts/{attempt_id}/annul/", {}, format="json",
                               HTTP_X_CSRFTOKEN=self.csrf)
        self.assertEqual(res.data["status"], "annulled")

    def test_question_crud_validation(self):
        self.login()
        math = Subject.objects.get(slug="math")
        payload = {"subject": math.id, "stage": 1, "text": "2 + 2 = ?", "difficulty": "easy", "points": 1,
                   "is_active": True, "options": [{"text": "4", "is_correct": True}, {"text": "5", "is_correct": True}]}
        bad = self.client.post("/api/admin/questions/", payload, format="json", HTTP_X_CSRFTOKEN=self.csrf)
        self.assertEqual(bad.status_code, 400)
        payload["options"][1]["is_correct"] = False
        ok = self.client.post("/api/admin/questions/", payload, format="json", HTTP_X_CSRFTOKEN=self.csrf)
        self.assertEqual(ok.status_code, 201, ok.data)
        qid = ok.data["id"]
        opt_ids = [o["id"] for o in ok.data["options"]]
        upd = self.client.patch(f"/api/admin/questions/{qid}/", {
            "options": [{"id": opt_ids[0], "text": "4", "is_correct": True}, {"text": "3", "is_correct": False},
                        {"text": "22", "is_correct": False}]}, format="json", HTTP_X_CSRFTOKEN=self.csrf)
        self.assertEqual(upd.status_code, 200, upd.data)
        self.assertEqual(len(upd.data["options"]), 3)
        self.assertEqual(upd.data["options"][0]["id"], opt_ids[0])  # kept (uid preserved)
        group = Subject.objects.create(name="Guruh", slug="group")
        Subject.objects.create(name="Yo'nalish", slug="group-a", parent=group)
        payload["subject"] = group.id
        self.assertEqual(self.client.post("/api/admin/questions/", payload, format="json",
                                          HTTP_X_CSRFTOKEN=self.csrf).status_code, 400)
        self.assertEqual(self.client.delete(f"/api/admin/questions/{qid}/", HTTP_X_CSRFTOKEN=self.csrf).status_code,
                         204)

    def test_question_import_export_roundtrip(self):
        self.login()
        res = self.client.get("/api/admin/questions/export/?subject=" + str(Subject.objects.get(slug="math").id))
        wb = load_workbook(io.BytesIO(res.content))
        self.assertEqual(wb.active.max_row, Question.objects.filter(subject__slug="math").count() + 1)

        good = Workbook()
        ws = good.active
        ws.append(["Fan kodi", "Bosqich", "Savol", "A", "B", "C", "D", "E", "F", "To'g'ri javob", "Ball",
                   "Qiyinlik", "Faol"])
        ws.append(["math", 1, "placeholder", "2", "-3", None, None, None, None, "A", 1, "oson", "ha"])
        ws["C2"].value = "=1+1 nechiga teng?"
        ws["C2"].data_type = "s"  # typed as text in Excel
        ws.append(["math", 2, "10 − 4 = ?", 6, 5, 4, None, None, None, "a", 2, "o'rta", None])
        buf = io.BytesIO()
        good.save(buf)
        buf.seek(0)
        buf.name = "q.xlsx"
        before = Question.objects.count()
        res = self.client.post("/api/admin/questions/import/", {"file": buf}, format="multipart",
                               HTTP_X_CSRFTOKEN=self.csrf)
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(Question.objects.count(), before + 2)
        q = Question.objects.get(text="=1+1 nechiga teng?")
        self.assertEqual(sorted(o.text for o in q.options.all()), ["-3", "2"])

        # Export must not turn text starting with '=' into a formula.
        res = self.client.get("/api/admin/questions/export/?search=nechiga")
        cell = load_workbook(io.BytesIO(res.content)).active["C2"]
        self.assertEqual(cell.data_type, "s")
        self.assertEqual(cell.value, "=1+1 nechiga teng?")

        bad = Workbook()
        ws = bad.active
        ws.append(["h"] * 13)
        ws.append(["nope", 3, "", "1", None, None, None, None, None, "C", 500, "x", "ha"])
        buf = io.BytesIO()
        bad.save(buf)
        buf.seek(0)
        buf.name = "bad.xlsx"
        res = self.client.post("/api/admin/questions/import/", {"file": buf}, format="multipart",
                               HTTP_X_CSRFTOKEN=self.csrf)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["errors"][0]["row"], 2)

    def test_subject_stage_settings_update(self):
        self.login()
        subject = Subject.objects.get(slug="english")
        res = self.client.patch(f"/api/admin/subjects/{subject.id}/", {"stages": [
            {"number": 1, "title": "Kirish", "question_count": 10, "duration_minutes": 15, "is_enabled": True},
            {"number": 2, "title": "Asosiy", "question_count": 25, "duration_minutes": 30, "is_enabled": True},
        ]}, format="json", HTTP_X_CSRFTOKEN=self.csrf)
        self.assertEqual(res.status_code, 200, res.data)
        meta = APIClient().get("/api/public/meta/").data
        english = next(s for s in meta["subjects"] if s["slug"] == "english")
        self.assertEqual(english["stages"][0]["question_count"], 10)

    def test_branch_with_attempts_cannot_be_deleted(self):
        self.make_attempt()
        self.login()
        branch = Branch.objects.first()
        res = self.client.delete(f"/api/admin/branches/{branch.id}/", HTTP_X_CSRFTOKEN=self.csrf)
        self.assertEqual(res.status_code, 409)

    def test_dashboard_and_settings(self):
        self.make_attempt()
        self.login()
        dash = self.client.get("/api/admin/dashboard/")
        self.assertEqual(dash.data["completed_total"], 1)
        self.assertEqual(dash.data["warnings"], [])
        res = self.client.put("/api/admin/settings/", {"show_score": True}, format="json",
                              HTTP_X_CSRFTOKEN=self.csrf)
        self.assertTrue(res.data["show_score"])


def make_docx(paragraphs, key=None):
    """Build a small .docx test file; `key` is a list of (number, letter) for a key table."""
    from docx import Document

    doc = Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    if key:
        doc.add_paragraph("JAVOBLAR KALITI")
        table = doc.add_table(rows=2, cols=len(key))
        for i, (num, letter) in enumerate(key):
            table.cell(0, i).text = str(num)
            table.cell(1, i).text = letter
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    buf.name = "test.docx"
    return buf


class WordImportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)
        get_user_model().objects.create_superuser("admin", "a@example.com", "Admin12345!")

    def setUp(self):
        cache.clear()
        self.client = APIClient(enforce_csrf_checks=True)
        self.client.get("/api/admin/auth/csrf/")
        self.csrf = self.client.cookies["csrftoken"].value
        self.client.post("/api/admin/auth/login/", {"username": "admin", "password": "Admin12345!"}, format="json",
                         HTTP_X_CSRFTOKEN=self.csrf)
        self.csrf = self.client.cookies["csrftoken"].value
        self.subject = Subject.objects.create(name="Fizika", slug="physics")

    def upload(self, file, **extra):
        data = {"file": file, "subject": self.subject.id, "stage": 2, "points": 2, "difficulty": "hard", **extra}
        return self.client.post("/api/admin/questions/import-word/", data, format="multipart",
                                HTTP_X_CSRFTOKEN=self.csrf)

    def sample(self):
        return make_docx([
            "FIZIKA — TEST",
            "1. Quyidagi kodning natijasi qanday?",
            "    print(2 ** 3)",
            "A) 6", "B) 8", "C) 9", "D) 5",
            "2) Yorug‘lik tezligi taxminan qancha?",
            "А) 300 000 km/s", "В) 30 000 km/s", "*С) 3 000 km/s", "D) 3 km/s",
            "3. Rus tilidagi variantlar",
            "а) один", "б) два", "в) три", "г) четыре",
        ], key=[(1, "B"), (2, "A"), (3, "в")])

    def test_preview_parses_without_saving(self):
        res = self.upload(self.sample(), preview="1")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["count"], 3)
        self.assertEqual(Question.objects.filter(subject=self.subject).count(), 0)
        q1, q2, q3 = res.data["questions"]
        self.assertEqual(q1["text"], "Quyidagi kodning natijasi qanday?\n    print(2 ** 3)")  # indentation kept
        self.assertEqual(q1["correct"], 1)
        self.assertEqual(q3["correct"], 2)  # Russian а/б/в/г labels
        # Question 2: inline mark (C) disagrees with the key (A) -> reported, never silently picked.
        self.assertEqual(res.data["problems"], [{"question": 2, "error": "Belgilangan javob kalitdagi javobga mos emas"}])

    def test_import_saves_all_or_nothing(self):
        bad = self.upload(self.sample())
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(Question.objects.filter(subject=self.subject).count(), 0)

        good = make_docx(["1. 2 + 2 = ?", "A) 3", "*B) 4", "C) 5", "2. Poytaxt?", "A) Toshkent", "B) Buxoro"],
                         key=[(2, "A")])
        res = self.upload(good)
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["created"], 2)
        qs = Question.objects.filter(subject=self.subject, stage=2)
        self.assertEqual(qs.count(), 2)
        q = qs.get(text="2 + 2 = ?")
        self.assertEqual((q.points, q.difficulty), (2, "hard"))
        self.assertEqual(q.options.get(is_correct=True).text, "4")

        # replace=1 swaps the whole stage bank of this subject
        again = make_docx(["1. Yangi savol", "A) ha", "B) yo'q"], key=[(1, "A")])
        res = self.upload(again, replace="1")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(Question.objects.filter(subject=self.subject, stage=2).count(), 1)

    def test_missing_key_and_wrong_file_are_reported(self):
        res = self.upload(make_docx(["1. Savol", "A) bir", "B) ikki"]))
        self.assertEqual(res.status_code, 400)
        self.assertIn("To'g'ri javob ko'rsatilmagan", res.data["problems"][0]["error"])
        txt = io.BytesIO(b"hello")
        txt.name = "a.txt"
        self.assertEqual(self.upload(txt).status_code, 400)
        fake = io.BytesIO(b"not a zip")
        fake.name = "fake.docx"
        res = self.upload(fake)
        self.assertEqual(res.status_code, 400)
        self.assertIn("o'qilmadi", res.data["problems"][0]["error"])

    def test_template_is_a_valid_importable_file(self):
        res = self.client.get("/api/admin/questions/word-template/")
        self.assertEqual(res.status_code, 200)
        f = io.BytesIO(res.content)
        f.name = "t.docx"
        res = self.upload(f, preview="1")
        self.assertEqual(res.data["count"], 3)
        self.assertEqual(res.data["problems"], [])

    def test_new_subject_gets_academic_and_subject_stages(self):
        res = self.client.post("/api/admin/subjects/", {"name": "Geografiya", "slug": "geo"}, format="json",
                               HTTP_X_CSRFTOKEN=self.csrf)
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual([(s["number"], s["source"]) for s in res.data["stages"]],
                         [(1, "academic"), (2, "subject")])
        dup = self.client.post("/api/admin/subjects/", {"name": "Akademik 2", "slug": "acad2", "is_academic": True},
                               format="json", HTTP_X_CSRFTOKEN=self.csrf)
        self.assertEqual(dup.status_code, 400)

    def test_supplied_teacher_files_parse_cleanly(self):
        """The real files from the client (kept as fixtures) parse with every answer keyed."""
        import glob
        import os

        files = sorted(glob.glob(os.path.join(os.path.dirname(__file__), "fixtures", "*.docx")))
        self.assertTrue(files)
        from apps.catalog.wordimport import parse_docx

        for path in files:
            with open(path, "rb") as fh:
                result = parse_docx(fh)
            self.assertEqual(result.problems, [], path)
            self.assertEqual(len(result.questions), 20 if "Akademiya" in path else 30, path)
