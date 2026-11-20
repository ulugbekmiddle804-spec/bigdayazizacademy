import random
from collections import Counter

from django.test import SimpleTestCase

from apps.catalog import demo_data
from apps.catalog.answer_order import correct_slots, place_correct


class AnswerOrderTests(SimpleTestCase):
    def test_no_same_letter_twice_in_a_row_and_balanced(self):
        for seed in range(50):
            slots = correct_slots([4] * 30, random.Random(seed))
            self.assertTrue(all(a != b for a, b in zip(slots, slots[1:])))
            counts = Counter(slots)
            self.assertEqual(set(counts), {0, 1, 2, 3})
            self.assertLessEqual(max(counts.values()) - min(counts.values()), 2)

    def test_place_correct_moves_right_answer(self):
        rng = random.Random(1)
        for slot in range(4):
            items = place_correct(["a", "b", "c", "d"], lambda o: o == "c", slot, rng)
            self.assertEqual(items.index("c"), slot)
            self.assertEqual(sorted(items), ["a", "b", "c", "d"])

    def test_mixed_option_counts(self):
        slots = correct_slots([2, 2, 3, 5, 1, 4], random.Random(3))
        for n, s in zip([2, 2, 3, 5, 1, 4], slots):
            self.assertLess(s, n)


class SubjectBankTests(SimpleTestCase):
    def test_correct_option_is_not_noticeably_longest(self):
        """The right answer must not give itself away by being much longer than every other option."""
        for slug, _name, _desc, _icon, module in demo_data.SUBJECTS:
            if not module:
                continue
            for _diff, text, opts, correct in demo_data.items(module):
                right = len(opts[correct])
                others = max(len(o) for i, o in enumerate(opts) if i != correct)
                with self.subTest(subject=slug, question=text[:60]):
                    self.assertFalse(right > others and right >= 1.15 * others)
