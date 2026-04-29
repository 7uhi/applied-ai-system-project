import pytest
from src.recommender import Song, UserProfile, Recommender, score_song, recommend_songs


# ---------------------------------------------------------------------------
# Shared song fixtures for functional-interface tests
# ---------------------------------------------------------------------------

def _song(genre="pop", mood="happy", energy=0.8) -> dict:
    return {
        "id": 1, "title": "Fixture Song", "artist": "Test Artist",
        "genre": genre, "mood": mood, "energy": energy,
        "tempo_bpm": 120.0, "valence": 0.8, "danceability": 0.7, "acousticness": 0.2,
    }


def _prefs(genre="pop", mood="happy", energy=0.8) -> dict:
    return {
        "favorite_genre": genre, "favorite_mood": mood, "target_energy": energy,
        "target_tempo_bpm": 120.0, "target_valence": 0.8,
        "target_danceability": 0.7, "target_acousticness": 0.2, "likes_acoustic": False,
    }

def make_small_recommender() -> Recommender:
    songs = [
        Song(
            id=1,
            title="Test Pop Track",
            artist="Test Artist",
            genre="pop",
            mood="happy",
            energy=0.8,
            tempo_bpm=120,
            valence=0.9,
            danceability=0.8,
            acousticness=0.2,
        ),
        Song(
            id=2,
            title="Chill Lofi Loop",
            artist="Test Artist",
            genre="lofi",
            mood="chill",
            energy=0.4,
            tempo_bpm=80,
            valence=0.6,
            danceability=0.5,
            acousticness=0.9,
        ),
    ]
    return Recommender(songs)


def test_recommend_returns_songs_sorted_by_score():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    results = rec.recommend(user, k=2)

    assert len(results) == 2
    # Starter expectation: the pop, happy, high energy song should score higher
    assert results[0].genre == "pop"
    assert results[0].mood == "happy"


def test_explain_recommendation_returns_non_empty_string():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    song = rec.songs[0]

    explanation = rec.explain_recommendation(user, song)
    assert isinstance(explanation, str)
    assert explanation.strip() != ""


# ---------------------------------------------------------------------------
# Confidence scoring — functional interface
# ---------------------------------------------------------------------------

def test_score_song_perfect_match_confidence_is_1():
    # Genre + mood + zero energy gap = 4.0/4.0 = 1.0 confidence
    score, reasons, confidence = score_song(_song("pop", "happy", 0.8), _prefs("pop", "happy", 0.8))
    assert score == pytest.approx(4.0)
    assert confidence == pytest.approx(1.0)


def test_score_song_energy_only_gives_low_confidence():
    # No genre or mood match; energy diff = 0 → score = 1.0, confidence = 0.25
    score, reasons, confidence = score_song(_song("rock", "angry", 0.5), _prefs("pop", "happy", 0.5))
    assert score == pytest.approx(1.0)
    assert confidence == pytest.approx(0.25)


def test_score_song_ghost_genre_caps_confidence():
    # User wants "classical", but the only available song is "lofi" — genre never matches.
    # With mood match (+1.0) and perfect energy match (+1.0), score = 2.0 → confidence = 0.5.
    song = _song("lofi", "relaxed", 0.3)
    prefs = _prefs("classical", "relaxed", 0.3)
    score, _, confidence = score_song(song, prefs)
    assert score == pytest.approx(2.0)
    assert confidence == pytest.approx(0.5)


def test_recommend_songs_returns_top_k_sorted_by_score():
    songs = [
        _song("lofi", "chill", 0.4),
        _song("pop",  "happy", 0.8),
        _song("rock", "angry", 0.9),
    ]
    results = recommend_songs(_prefs("pop", "happy", 0.8), songs, k=2)
    assert len(results) == 2
    # pop/happy/0.8 song must be ranked first (perfect match)
    assert results[0][0]["genre"] == "pop"
    assert results[0][1] == pytest.approx(4.0)
    # second result should score lower
    assert results[1][1] < results[0][1]


def test_recommend_songs_k_larger_than_catalog_returns_all():
    songs = [_song("pop", "happy", 0.8)]
    results = recommend_songs(_prefs("pop", "happy", 0.8), songs, k=10)
    assert len(results) == 1
