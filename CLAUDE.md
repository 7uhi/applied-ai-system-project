# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the recommender (must be run from repo root so the relative path to data/songs.csv resolves)
python -m src.main

# Run all tests
pytest

# Run a single test function
pytest tests/test_recommender.py::test_recommend_returns_songs_sorted_by_score
```

## Architecture

There are two parallel implementations of the recommendation logic that coexist in `src/recommender.py`:

**OOP interface** — used by the test suite (`tests/test_recommender.py`):
- `Song` / `UserProfile` dataclasses hold catalog and preference data.
- `Recommender(songs).recommend(user, k)` returns a ranked `List[Song]`.
- `Recommender.explain_recommendation(user, song)` produces a human-readable reason string.

**Functional interface** — used by `src/main.py`:
- `load_songs(csv_path)` parses `data/songs.csv` into `List[Dict]`.
- `score_song(song_dict, user_prefs_dict)` returns `(score, reasons)`. **Note:** there is a duplicate definition of `score_song` in `recommender.py`; the second definition (which takes `user_prefs` as the first argument) shadows the first and currently returns an empty list — this is a known stub.
- `recommend_songs(user_prefs, songs, k)` calls `score_song` and returns sorted `(song_dict, score, explanation)` tuples.

**Data flow:** `data/songs.csv` → `load_songs` → `recommend_songs` → printed rankings in `main()`. The path `data/songs.csv` is hard-coded as a relative path, so the module must be invoked from the repo root via `python -m src.main`.

**Scoring formula** (implemented in `Recommender.recommend` and the first `score_song`):
- `+2.0` for genre match, `+1.0` for mood match, `+0–1` for energy similarity (`1.0 - |song.energy - target_energy|`). Max score = 4.0. Tempo, valence, danceability, and acousticness fields exist on both dataclasses but are not used in scoring.

**Test fixture:** `tests/test_recommender.py` constructs a two-song `Recommender` inline and tests that `recommend` sorts correctly and `explain_recommendation` returns a non-empty string. `UserProfile` is instantiated with only four keyword arguments in the tests — the dataclass must either have defaults for the remaining fields or the tests will break if new required fields are added.
