from datetime import timedelta
from unittest import mock

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog import demo_data
from apps.catalog.models import Branch, Subject
from apps.core.models import SiteSettings

from .models import Attempt, AttemptAnswer, AttemptStage
from .services import finalize_expired


class DemoDataTests(TestCase):
    def test_demo_bank_is_valid(self):
        self.assertEqual(demo_data.validate(), [])

    def test_every_subject_has_enough_questions(self):
        # The academic bank is the academy regulations test: at least one full stage.
        self.assertGreaterEqual(len(demo_data.items(demo_data.ACADEMIC[4])), demo_data.ACADEMIC_STAGE["question_count"])
        for slug, *_rest, module in demo_data.SUBJECTS:
            if module:
                self.assertEqual(len(demo_data.items(module)), demo_data.BANK_SIZE, slug)


class ExamFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.branch = Branch.objects.first()
        self.subject = Subject.objects.get(slug="math")

    def start(self, first="Ali", last="Valiyev", subject=None):
        return self.client.post("/api/attempts/", {
            "first_name": first, "last_name": last, "branch_id": self.branch.id,
            "subject_id": (subject or self.subject).id,
        }, format="json")

    def auth(self, token):
        return {"HTTP_X_ATTEMPT_TOKEN": token}

    def test_meta_lists_branches_and_subjects(self):
        res = self.client.get("/api/public/meta/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual([b["name"] for b in res.data["branches"]], [name for name, _ in demo_data.BRANCHES])
        subjects = res.data["subjects"]
        self.assertEqual([s["slug"] for s in subjects], [row[0] for row in demo_data.SUBJECTS])
        self.assertNotIn("academic", [s["slug"] for s in subjects])  # the shared bank is not selectable
        math = next(s for s in subjects if s["slug"] == "math")
        self.assertEqual([(st["title"], st["question_count"]) for st in math["stages"]],
                         [("Akademik test", 20), ("Fan testi", 30)])
        other = next(s for s in subjects if s["slug"] == "other")
        self.assertEqual([st["number"] for st in other["stages"]], [1])

    def test_stage1_uses_academic_bank_and_stage2_the_subject_bank(self):
        res = self.start()
        token, state = res.data["token"], res.data["state"]
        academic = Subject.objects.get(is_academic=True)
        attempt = Attempt.objects.get(pk=state["id"])
        stage1 = AttemptAnswer.objects.filter(attempt=attempt, stage=1).select_related("question")
        self.assertEqual({a.question.subject_id for a in stage1}, {academic.id})
        self.client.post(f"/api/attempts/{attempt.id}/stages/1/finish/", {}, format="json", **self.auth(token))
        self.client.post(f"/api/attempts/{attempt.id}/stages/2/start/", {}, format="json", **self.auth(token))
        stage2 = AttemptAnswer.objects.filter(attempt=attempt, stage=2).select_related("question")
        self.assertEqual(stage2.count(), 30)
        self.assertEqual({a.question.subject_id for a in stage2}, {self.subject.id})

    def test_other_subject_has_only_the_academic_stage(self):
        res = self.start(subject=Subject.objects.get(slug="other"))
        self.assertEqual(res.status_code, 201, res.data)
        token, state = res.data["token"], res.data["state"]
        self.assertEqual(len(state["stages"]), 1)
        fin = self.client.post(f"/api/attempts/{state['id']}/stages/1/finish/", {}, format="json",
                               **self.auth(token))
        self.assertEqual(fin.data["status"], "completed")
        self.assertEqual(Attempt.objects.get(pk=state["id"]).max_score, 20)

    def test_start_returns_stage1_questions_without_answer_key(self):
        res = self.start()
        self.assertEqual(res.status_code, 201, res.data)
        state = res.data["state"]
        self.assertEqual(len(state["questions"]), 20)
        body = res.content.decode()
        self.assertNotIn("correct", body)
        self.assertNotIn("is_correct", body)
        q = state["questions"][0]
        self.assertEqual(set(q.keys()), {"id", "position", "text", "options", "selected"})
        self.assertEqual(set(q["options"][0].keys()), {"id", "text"})

    def test_questions_are_shuffled_between_attempts(self):
        a = self.start("Ali", "Valiyev").data["state"]
        b = self.start("Vali", "Aliyev").data["state"]
        # Stage 1 (academic) keeps the document order for everyone ...
        self.assertEqual([q["text"] for q in a["questions"]], [q["text"] for q in b["questions"]])
        ids = list(AttemptAnswer.objects.filter(attempt_id=a["id"], stage=1).order_by("position")
                   .values_list("question_id", flat=True))
        self.assertEqual(ids, sorted(ids))
        # ... while the subject stage is shuffled per person.
        def stage2(attempt_id):
            return list(AttemptAnswer.objects.filter(attempt_id=attempt_id, stage=2).order_by("position")
                        .values_list("question_text", flat=True))
        self.assertNotEqual(stage2(a["id"]), stage2(b["id"]))

    @override_settings(PROXY_SECRET="proxy-secret")
    def test_visitor_ip_from_cloudflare_proxy(self):
        data = {"first_name": "Ip", "last_name": "Tekshiruv", "branch_id": self.branch.id, "subject_id": self.subject.id}
        res = self.client.post("/api/attempts/", data, format="json",
                               HTTP_X_PROXY_SECRET="proxy-secret", HTTP_X_CLIENT_IP="203.0.113.7")
        self.assertEqual(Attempt.objects.get(pk=res.data["state"]["id"]).ip_address, "203.0.113.7")
        # Without the right secret the header is ignored.
        data["last_name"] = "Soxta"
        res = self.client.post("/api/attempts/", data, format="json",
                               HTTP_X_PROXY_SECRET="wrong", HTTP_X_CLIENT_IP="203.0.113.8")
        self.assertNotEqual(Attempt.objects.get(pk=res.data["state"]["id"]).ip_address, "203.0.113.8")

    def test_invalid_names_are_rejected(self):
        res = self.start(first="<script>", last="X")
        self.assertEqual(res.status_code, 400)
        self.assertIn("first_name", res.data)
        self.assertIn("last_name", res.data)

    def test_group_and_academic_bank_cannot_be_started(self):
        group = Subject.objects.create(name="Guruh", slug="group")
        Subject.objects.create(name="Yo'nalish", slug="group-a", parent=group)
        self.assertEqual(self.start(subject=group).status_code, 400)
        self.assertEqual(self.start(subject=Subject.objects.get(is_academic=True)).status_code, 400)

    def test_wrong_token_is_rejected(self):
        res = self.start()
        attempt_id = res.data["state"]["id"]
        self.assertEqual(self.client.get(f"/api/attempts/{attempt_id}/", **self.auth("nope")).status_code, 404)
        self.assertEqual(self.client.get(f"/api/attempts/{attempt_id}/").status_code, 404)

    def _answer_all(self, attempt_id, token, stage, questions, correct=True):
        attempt = Attempt.objects.get(pk=attempt_id)
        key = {a.id: str(a.correct_option) for a in AttemptAnswer.objects.filter(attempt=attempt, stage=stage)}
        items = []
        for q in questions:
            if correct:
                option = key[q["id"]]
            else:
                option = next(o["id"] for o in q["options"] if o["id"] != key[q["id"]])
            items.append({"id": q["id"], "option": option})
        return items

    def test_full_flow_grading_and_hidden_results(self):
        res = self.start()
        token, state = res.data["token"], res.data["state"]
        attempt_id = state["id"]
        items = self._answer_all(attempt_id, token, 1, state["questions"])
        # 15 correct, 5 left blank
        save = self.client.put(f"/api/attempts/{attempt_id}/answers/", {"stage": 1, "answers": items[:15]},
                               format="json", **self.auth(token))
        self.assertEqual(save.status_code, 200, save.data)

        # Reload keeps answers
        reloaded = self.client.get(f"/api/attempts/{attempt_id}/", **self.auth(token)).data
        self.assertEqual(sum(1 for q in reloaded["questions"] if q["selected"]), 15)

        fin1 = self.client.post(f"/api/attempts/{attempt_id}/stages/1/finish/", {}, format="json",
                                **self.auth(token))
        self.assertEqual(fin1.status_code, 200)
        self.assertEqual(fin1.data["current_stage"], 2)
        self.assertEqual(fin1.data["questions"], [])  # stage 2 not started yet

        st2 = self.client.post(f"/api/attempts/{attempt_id}/stages/2/start/", {}, format="json",
                               **self.auth(token))
        self.assertEqual(len(st2.data["questions"]), 30)
        items2 = self._answer_all(attempt_id, token, 2, st2.data["questions"][:10])
        wrong2 = self._answer_all(attempt_id, token, 2, st2.data["questions"][10:20], correct=False)
        fin2 = self.client.post(f"/api/attempts/{attempt_id}/stages/2/finish/", {"answers": items2 + wrong2},
                                format="json", **self.auth(token))
        self.assertEqual(fin2.data["status"], "completed")
        self.assertIsNone(fin2.data["result"])  # hidden by default
        self.assertIsNone(fin2.data["review"])

        attempt = Attempt.objects.get(pk=attempt_id)
        self.assertEqual(attempt.stage1_correct, 15)
        self.assertEqual(attempt.stage1_score, 15)
        self.assertEqual(attempt.stage2_correct, 10)
        self.assertEqual(attempt.stage2_score, 10)
        self.assertEqual(attempt.total_score, 25)
        self.assertEqual(attempt.max_score, 20 + 30)
        self.assertEqual(attempt.wrong_count, 10)
        self.assertEqual(attempt.blank_count, 5 + 10)

        # Finishing again is harmless; saving after completion is refused.
        again = self.client.post(f"/api/attempts/{attempt_id}/stages/2/finish/", {}, format="json",
                                 **self.auth(token))
        self.assertEqual(again.status_code, 200)
        late = self.client.put(f"/api/attempts/{attempt_id}/answers/", {"stage": 2, "answers": items2[:1]},
                               format="json", **self.auth(token))
        self.assertEqual(late.status_code, 409)
        self.assertEqual(Attempt.objects.get(pk=attempt_id).total_score, 25)

    def test_results_visible_when_admin_allows(self):
        s = SiteSettings.load()
        s.show_score = True
        s.show_answer_review = True
        s.save()
        res = self.start()
        token, attempt_id = res.data["token"], res.data["state"]["id"]
        self.client.post(f"/api/attempts/{attempt_id}/stages/1/finish/", {}, format="json", **self.auth(token))
        self.client.post(f"/api/attempts/{attempt_id}/stages/2/start/", {}, format="json", **self.auth(token))
        fin = self.client.post(f"/api/attempts/{attempt_id}/stages/2/finish/", {}, format="json",
                               **self.auth(token))
        self.assertEqual(fin.data["result"]["total_score"], 0)
        self.assertEqual(len(fin.data["review"]), 50)

    def test_option_from_another_question_is_rejected(self):
        res = self.start()
        token, state = res.data["token"], res.data["state"]
        q1, q2 = state["questions"][0], state["questions"][1]
        bad = self.client.put(f"/api/attempts/{state['id']}/answers/",
                              {"stage": 1, "answers": [{"id": q1["id"], "option": q2["options"][0]["id"]}]},
                              format="json", **self.auth(token))
        self.assertEqual(bad.status_code, 400)

    def test_cannot_touch_other_attempts_questions(self):
        a = self.start("Ali", "Valiyev").data
        b = self.start("Vali", "Aliyev").data
        q = b["state"]["questions"][0]
        res = self.client.put(f"/api/attempts/{a['state']['id']}/answers/",
                              {"stage": 1, "answers": [{"id": q["id"], "option": q["options"][0]["id"]}]},
                              format="json", **self.auth(a["token"]))
        self.assertEqual(res.status_code, 400)

    def test_retake_is_controlled_by_admin(self):
        res = self.start()
        token, attempt_id = res.data["token"], res.data["state"]["id"]
        # Second start while the first is running.
        self.assertEqual(self.start().status_code, 409)
        for n in (1, 2):
            if n == 2:
                self.client.post(f"/api/attempts/{attempt_id}/stages/2/start/", {}, format="json", **self.auth(token))
            self.client.post(f"/api/attempts/{attempt_id}/stages/{n}/finish/", {}, format="json", **self.auth(token))
        # Name matching ignores case and extra spaces.
        blocked = self.start(first=" ali ", last="VALIYEV")
        self.assertEqual(blocked.status_code, 403)
        self.assertEqual(blocked.data["code"], "already_completed")
        Attempt.objects.filter(pk=attempt_id).update(retake_allowed=True)
        self.assertEqual(self.start().status_code, 201)

    def test_timeout_auto_finishes_stage(self):
        res = self.start()
        token, state = res.data["token"], res.data["state"]
        attempt_id = state["id"]
        items = self._answer_all(attempt_id, token, 1, state["questions"][:3])
        self.client.put(f"/api/attempts/{attempt_id}/answers/", {"stage": 1, "answers": items}, format="json",
                        **self.auth(token))
        AttemptStage.objects.filter(attempt_id=attempt_id, number=1).update(
            deadline=timezone.now() - timedelta(minutes=5))
        late = self.client.put(f"/api/attempts/{attempt_id}/answers/", {"stage": 1, "answers": items},
                               format="json", **self.auth(token))
        self.assertEqual(late.status_code, 409)
        stage = AttemptStage.objects.get(attempt_id=attempt_id, number=1)
        self.assertEqual(stage.finish_reason, "timeout")
        self.assertEqual(stage.correct_count, 3)

    def test_sweeper_closes_abandoned_attempts(self):
        res = self.start()
        attempt_id = res.data["state"]["id"]
        AttemptStage.objects.filter(attempt_id=attempt_id, number=1).update(
            deadline=timezone.now() - timedelta(hours=2))
        self.assertGreaterEqual(finalize_expired(), 1)
        attempt = Attempt.objects.get(pk=attempt_id)
        self.assertEqual(attempt.current_stage, 2)
        # Long pause before stage 2 closes the whole attempt.
        AttemptStage.objects.filter(attempt_id=attempt_id, number=1).update(
            finished_at=timezone.now() - timedelta(hours=1))
        finalize_expired()
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, "completed")

    def test_registration_can_be_closed(self):
        s = SiteSettings.load()
        s.registration_open = False
        s.save()
        self.assertEqual(self.start().status_code, 403)

    @override_settings(EXAM={"GRACE_SECONDS": 20, "STAGE_BREAK_MAX_MINUTES": 15, "QUESTION_POOL_CACHE_SECONDS": 60})
    def test_finish_slightly_after_deadline_keeps_answers(self):
        res = self.start()
        token, state = res.data["token"], res.data["state"]
        attempt_id = state["id"]
        items = self._answer_all(attempt_id, token, 1, state["questions"][:4])
        AttemptStage.objects.filter(attempt_id=attempt_id, number=1).update(
            deadline=timezone.now() - timedelta(seconds=5))
        fin = self.client.post(f"/api/attempts/{attempt_id}/stages/1/finish/", {"answers": items}, format="json",
                               **self.auth(token))
        self.assertEqual(fin.status_code, 200)
        self.assertEqual(AttemptStage.objects.get(attempt_id=attempt_id, number=1).correct_count, 4)

    def test_answer_key_edit_does_not_change_existing_attempt(self):
        res = self.start()
        token, state = res.data["token"], res.data["state"]
        attempt_id = state["id"]
        items = self._answer_all(attempt_id, token, 1, state["questions"][:1])
        row = AttemptAnswer.objects.get(pk=items[0]["id"])
        # Admin flips the key of the source question afterwards.
        q = row.question
        for o in q.options.all():
            o.is_correct = not o.is_correct and str(o.uid) != items[0]["option"]
            o.save()
        with mock.patch("apps.exams.services.timezone.now", return_value=timezone.now()):
            self.client.post(f"/api/attempts/{attempt_id}/stages/1/finish/", {"answers": items}, format="json",
                             **self.auth(token))
        row.refresh_from_db()
        self.assertTrue(row.is_correct)
