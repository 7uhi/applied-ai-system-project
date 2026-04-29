"""
RAG retrieval layer: embeds a user profile description and finds the
most semantically similar songs from the precomputed embedding matrix.
"""

import pathlib
import numpy as np

_MODEL_NAME = "all-MiniLM-L6-v2"
_EMBEDDINGS_PATH = pathlib.Path("data/embeddings.npy")
_SONG_IDS_PATH = pathlib.Path("data/song_ids.npy")

# Module-level cache so the model is only loaded once per process
_model = None


def _get_model():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers is required. Install with: pip install sentence-transformers"
            ) from exc
        _model = SentenceTransformer(_MODEL_NAME)
    return _model


def load_embeddings(songs: list[dict]) -> tuple[np.ndarray, list[dict]]:
    """
    Load precomputed embeddings and align them with the in-memory song list.

    Returns (embeddings_matrix, ordered_songs) where row i of the matrix
    corresponds to ordered_songs[i].
    """
    if not _EMBEDDINGS_PATH.exists() or not _SONG_IDS_PATH.exists():
        raise FileNotFoundError(
            "Embedding files not found. Run: python scripts/build_embeddings.py"
        )

    embeddings = np.load(_EMBEDDINGS_PATH)
    saved_ids = np.load(_SONG_IDS_PATH).tolist()

    id_to_song = {s["id"]: s for s in songs}
    ordered_songs = [id_to_song[sid] for sid in saved_ids if sid in id_to_song]

    if len(ordered_songs) != len(saved_ids):
        missing = len(saved_ids) - len(ordered_songs)
        print(f"[retriever] Warning: {missing} embedding rows have no matching song in CSV.")

    return embeddings[: len(ordered_songs)], ordered_songs


def _profile_to_text(user_prefs: dict) -> str:
    """Convert an extracted user profile dict into an embeddable description."""
    energy = user_prefs.get("target_energy", 0.5)
    energy_lbl = "low" if energy < 0.33 else ("moderate" if energy < 0.66 else "high")
    acousticness = user_prefs.get("target_acousticness", 0.5)
    acoustic_lbl = (
        "acoustic" if acousticness > 0.7 else
        ("semi-acoustic" if acousticness > 0.4 else "electronic")
    )
    return (
        f"Genre: {user_prefs.get('favorite_genre', 'any')}. "
        f"Mood: {user_prefs.get('favorite_mood', 'any')}. "
        f"Energy: {energy:.2f} ({energy_lbl}). "
        f"Tempo: {user_prefs.get('target_tempo_bpm', 100):.0f} BPM. "
        f"Valence: {user_prefs.get('target_valence', 0.5):.2f}. "
        f"Danceability: {user_prefs.get('target_danceability', 0.5):.2f}. "
        f"Sound: {acoustic_lbl}."
    )


def retrieve_candidates(
    user_prefs: dict,
    embeddings: np.ndarray,
    songs: list[dict],
    top_n: int = 30,
) -> list[dict]:
    """
    Embed the user profile and return the top-N songs by cosine similarity.

    The returned list is a semantic pre-filter; the rule-based scorer in
    recommender.py then re-ranks this smaller pool to produce the final top-k.
    """
    model = _get_model()
    query_text = _profile_to_text(user_prefs)
    query_vec = model.encode(query_text, convert_to_numpy=True)

    norms = np.linalg.norm(embeddings, axis=1) * np.linalg.norm(query_vec)
    norms = np.where(norms == 0, 1e-9, norms)  # avoid division by zero
    sims = (embeddings @ query_vec) / norms

    top_n = min(top_n, len(songs))
    top_indices = np.argsort(sims)[::-1][:top_n]
    return [songs[i] for i in top_indices]
