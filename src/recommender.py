from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import csv

@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float

@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float        # 0.0 (very calm) – 1.0 (very intense)
    target_tempo_bpm: float = 100.0   # beats per minute
    target_valence: float = 0.5       # 0.0 (dark/sad) – 1.0 (bright/happy)
    target_danceability: float = 0.5  # 0.0 (not danceable) – 1.0 (very danceable)
    target_acousticness: float = 0.5  # 0.0 (fully electronic) – 1.0 (fully acoustic)
    likes_acoustic: bool = False      # convenience flag derived from target_acousticness

class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        """Store the song catalog for later recommendation queries."""
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """Return the top-k songs ranked by genre, mood, and energy match."""
        scored = []
        for song in self.songs:
            score = 0.0
            if song.genre == user.favorite_genre:
                score += 2.0
            if song.mood == user.favorite_mood:
                score += 1.0
            score += 1.0 - abs(song.energy - user.target_energy)
            scored.append((song, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [song for song, _ in scored[:k]]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Build a human-readable sentence explaining why a song was recommended."""
        reasons = []
        if song.genre == user.favorite_genre:
            reasons.append(f"matches your favorite genre ({song.genre})")
        if song.mood == user.favorite_mood:
            reasons.append(f"matches your preferred mood ({song.mood})")
        energy_diff = abs(song.energy - user.target_energy)
        if energy_diff <= 0.10:
            reasons.append(f"energy level is very close to your target ({song.energy:.2f} vs {user.target_energy:.2f})")
        elif energy_diff <= 0.25:
            reasons.append(f"energy level is a reasonable match ({song.energy:.2f} vs {user.target_energy:.2f})")
        if not reasons:
            reasons.append("overall profile is the closest available match")
        return "This song " + ", and ".join(reasons) + "."

def load_songs(csv_path: str) -> List[Dict]:
    """
    Loads songs from a CSV file.
    Required by src/main.py
    """
    print(f"Loading songs from {csv_path}...")
    songs = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            songs.append({
                "id":            int(row["id"]),
                "title":         row["title"],
                "artist":        row["artist"],
                "genre":         row["genre"],
                "mood":          row["mood"],
                "energy":        float(row["energy"]),
                "tempo_bpm":     float(row["tempo_bpm"]),
                "valence":       float(row["valence"]),
                "danceability":  float(row["danceability"]),
                "acousticness":  float(row["acousticness"]),
            })
    return songs

_MAX_SCORE = 4.0  # 2.0 genre + 1.0 mood + 1.0 energy


def score_song(song: Dict, user_prefs: Dict) -> Tuple[float, List[str], float]:
    """
    Scores a single song against user preferences.

    Scoring recipe:
      +2.0  genre match
      +1.0  mood match
      +0–1  energy similarity  (1.0 - |song.energy - target_energy|)

    Returns (score, reasons, confidence) where confidence is score / 4.0.
    """
    score = 0.0
    reasons = []

    if song["genre"] == user_prefs["favorite_genre"]:
        score += 2.0
        reasons.append(f"genre match (+2.0)")

    if song["mood"] == user_prefs["favorite_mood"]:
        score += 1.0
        reasons.append(f"mood match (+1.0)")

    energy_similarity = 1.0 - abs(song["energy"] - user_prefs["target_energy"])
    score += energy_similarity
    reasons.append(f"energy similarity (+{energy_similarity:.2f})")

    confidence = round(max(0.0, score) / _MAX_SCORE, 3)
    return score, reasons, confidence

def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str, float]]:
    """
    Functional implementation of the recommendation logic.
    Required by src/main.py

    Returns a list of (song_dict, score, explanation, confidence) tuples, best first.
    """
    scored = []
    for song in songs:
        score, reasons, confidence = score_song(song, user_prefs)
        explanation = "This song " + ", and ".join(reasons) + "."
        scored.append((song, score, explanation, confidence))

    return sorted(scored, key=lambda x: x[1], reverse=True)[:k]
