"""Where the correct option goes in a run of questions.

Plain shuffling can easily give runs such as C C C or B B B, which test-takers
notice. ``correct_slots`` spreads the right answer evenly over the letters and
never puts it under the same letter in two consecutive questions.
"""
import random


def correct_slots(option_counts, rng=None):
    """Return one target index per question (``option_counts[i]`` options each)."""
    rng = rng or random.SystemRandom()
    used = {}
    slots, prev = [], None
    for n in option_counts:
        if n <= 0:
            slots.append(0)
            continue
        choices = [i for i in range(n) if i != prev] or list(range(n))
        # Allow a little slack (least used + 1) so the letters don't fall into a visible A B C D cycle.
        least = min(used.get(i, 0) for i in choices)
        pick = rng.choice([i for i in choices if used.get(i, 0) <= least + 1])
        used[pick] = used.get(pick, 0) + 1
        slots.append(pick)
        prev = pick
    return slots


def place_correct(options, is_correct, slot, rng=None):
    """Shuffle ``options`` and move the (first) correct one to index ``slot``."""
    rng = rng or random.SystemRandom()
    items = list(options)
    rng.shuffle(items)
    idx = next((i for i, o in enumerate(items) if is_correct(o)), None)
    if idx is not None and 0 <= slot < len(items):
        items[idx], items[slot] = items[slot], items[idx]
    return items
