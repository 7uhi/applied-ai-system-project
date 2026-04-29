"""
GrooveMatch Evaluation Harness

Runs the recommender against 8 predefined test cases (3 happy-path + 5 edge cases)
and prints a structured pass/fail summary with confidence statistics.

Usage (from repo root):
    python scripts/eval.py
"""

import sys
import os
from dataclasses import dataclass
from typing import Callable

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.recommender import load_songs, recommend_songs
from src.agent import _validate_prefs


@dataclass
class TestCase:
    name: str
    prefs: dict
    assertion: Callable[[list], tuple[bool, str]]
    k: int = 5


def _top(results):
    return results[0]


def run_eval():
    songs = load_songs("data/songs.csv")

    cases = [
        TestCase(
            name="High-Energy Pop",
            prefs=_validate_prefs({"favorite_genre": "pop", "favorite_mood": "intense", "target_energy": 0.90}),
            assertion=lambda r: (
                _top(r)[0]["genre"] == "pop" and _top(r)[3] >= 0.90,
                f"top={_top(r)[0]['genre']}/{_top(r)[0]['mood']}  confidence={_top(r)[3]:.0%}  score={_top(r)[1]:.2f}",
            ),
        ),
        TestCase(
            name="Chill Lofi",
            prefs=_validate_prefs({"favorite_genre": "lofi", "favorite_mood": "focused", "target_energy": 0.42}),
            assertion=lambda r: (
                _top(r)[0]["genre"] == "lofi" and _top(r)[3] >= 0.90,
                f"top={_top(r)[0]['genre']}/{_top(r)[0]['mood']}  confidence={_top(r)[3]:.0%}  score={_top(r)[1]:.2f}",
            ),
        ),
        TestCase(
            name="Deep Intense Rock",
            prefs=_validate_prefs({"favorite_genre": "rock", "favorite_mood": "intense", "target_energy": 0.88}),
            assertion=lambda r: (
                _top(r)[0]["genre"] == "rock",
                f"top={_top(r)[0]['genre']}/{_top(r)[0]['mood']}  confidence={_top(r)[3]:.0%}  score={_top(r)[1]:.2f}",
            ),
        ),
        TestCase(
            name="[EDGE] Ghost Genre",
            prefs=_validate_prefs({"favorite_genre": "ska", "favorite_mood": "relaxed", "target_energy": 0.35}),
            assertion=lambda r: (
                _top(r)[3] <= 0.50,
                f"confidence={_top(r)[3]:.0%}  (capped at ≤50% — 'ska' not in catalog, no genre bonus)",
            ),
        ),
        TestCase(
            name="[EDGE] Out-of-Range Energy",
            prefs=_validate_prefs({"favorite_genre": "pop", "favorite_mood": "happy", "target_energy": 1.5}),
            assertion=lambda r: (
                all(s >= 0 for _, s, _, _ in r),
                f"min_score={min(s for _, s, _, _ in r):.2f}  (all scores ≥ 0 after clamping energy to 1.0)",
            ),
        ),
        TestCase(
            name="[EDGE] Genre Dominance",
            prefs=_validate_prefs({"favorite_genre": "pop", "favorite_mood": "happy", "target_energy": 0.10}),
            assertion=lambda r: (
                _top(r)[0]["genre"] == "pop"
                and abs(_top(r)[0]["energy"] - 0.10) > 0.5,
                f"top={_top(r)[0]['genre']}  energy={_top(r)[0]['energy']:.2f}  "
                f"gap={abs(_top(r)[0]['energy'] - 0.10):.2f}  (known limitation: genre bonus overrides energy)",
            ),
        ),
        TestCase(
            name="Results are sorted",
            prefs=_validate_prefs({"favorite_genre": "jazz", "favorite_mood": "chill", "target_energy": 0.50}),
            assertion=lambda r: (
                all(r[i][1] >= r[i + 1][1] for i in range(len(r) - 1)),
                f"scores={[round(s, 2) for _, s, _, _ in r]}  ✓" if all(r[i][1] >= r[i + 1][1] for i in range(len(r) - 1))
                else "NOT sorted",
            ),
        ),
        TestCase(
            name="k truncation",
            prefs=_validate_prefs({"favorite_genre": "pop", "favorite_mood": "happy", "target_energy": 0.8}),
            k=3,
            assertion=lambda r: (
                len(r) == 3,
                f"len={len(r)}  ✓",
            ),
        ),
    ]

    print(f"\nGrooveMatch Eval — {len(cases)} test cases")
    print("─" * 60)

    passed = 0
    confidence_sum = 0.0
    confidence_count = 0

    for case in cases:
        results = recommend_songs(case.prefs, songs, k=case.k)
        ok, detail = case.assertion(results)
        label = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        print(f"{label}  {case.name:<32}  {detail}")

        if results and results[0][3] is not None:
            confidence_sum += results[0][3]
            confidence_count += 1

    avg_conf = confidence_sum / confidence_count if confidence_count else 0.0
    print("─" * 60)
    print(f"{passed}/{len(cases)} passed   |   avg top-1 confidence: {avg_conf:.0%}\n")

    sys.exit(0 if passed == len(cases) else 1)


if __name__ == "__main__":
    run_eval()
