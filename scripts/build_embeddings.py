"""
One-time script to build and save song embeddings.

Run from the repo root:
    python scripts/build_embeddings.py

Outputs:
    data/embeddings.npy   — numpy array of shape (N, 384)
    data/song_ids.npy     — ordered song IDs matching embedding rows
"""

import csv
import pathlib
import numpy as np
from sentence_transformers import SentenceTransformer

SONGS_CSV = pathlib.Path("data/songs.csv")
EMBEDDINGS_NPY = pathlib.Path("data/embeddings.npy")
SONG_IDS_NPY = pathlib.Path("data/song_ids.npy")
MODEL_NAME = "all-MiniLM-L6-v2"


def _energy_label(energy: float) -> str:
    if energy < 0.33:
        return "low"
    if energy < 0.66:
        return "moderate"
    return "high"


def _acousticness_label(acousticness: float) -> str:
    if acousticness > 0.7:
        return "acoustic"
    if acousticness > 0.4:
        return "semi-acoustic"
    return "electronic"


def song_to_text(row: dict) -> str:
    """Convert a song CSV row into a descriptive sentence for embedding."""
    energy_lbl = _energy_label(float(row["energy"]))
    acoustic_lbl = _acousticness_label(float(row["acousticness"]))
    return (
        f"Genre: {row['genre']}. Mood: {row['mood']}. "
        f"Energy: {row['energy']} ({energy_lbl}). "
        f"Tempo: {row['tempo_bpm']} BPM. "
        f"Valence: {row['valence']}. "
        f"Danceability: {row['danceability']}. "
        f"Sound: {acoustic_lbl}."
    )


def main() -> None:
    print(f"Loading songs from {SONGS_CSV}...")
    songs = []
    with open(SONGS_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            songs.append(row)

    print(f"  {len(songs)} songs loaded.")

    texts = [song_to_text(s) for s in songs]
    song_ids = np.array([int(s["id"]) for s in songs])

    print(f"Loading embedding model '{MODEL_NAME}'...")
    model = SentenceTransformer(MODEL_NAME)

    print("Computing embeddings (this takes ~30 seconds on first run)...")
    embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)

    np.save(EMBEDDINGS_NPY, embeddings)
    np.save(SONG_IDS_NPY, song_ids)

    print(f"\nSaved embeddings: {EMBEDDINGS_NPY}  shape={embeddings.shape}")
    print(f"Saved song IDs:   {SONG_IDS_NPY}")


if __name__ == "__main__":
    main()
