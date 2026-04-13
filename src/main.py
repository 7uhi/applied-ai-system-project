"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

from .recommender import load_songs, recommend_songs


def main() -> None:
    songs = load_songs("data/songs.csv")

    # --- User preference profiles ---

    # Profile 1: High-Energy Pop
    # A workout listener who wants loud, fast, euphoric pop bangers.
    high_energy_pop = {
        "favorite_genre":       "pop",     # primary genre preference
        "favorite_mood":        "intense", # wants high-octane, pumped-up tracks
        "target_energy":        0.90,      # near-maximum energy
        "target_tempo_bpm":     130.0,     # fast; gym-ready tempo
        "target_valence":       0.80,      # bright and positive
        "target_danceability":  0.88,      # highly danceable
        "target_acousticness":  0.08,      # strongly prefers produced/electronic sound
        "likes_acoustic":       False,
    }

    # Profile 2: Chill Lofi
    # A late-night focused listener who prefers mellow, acoustic-leaning lofi
    # with just enough energy to stay productive.
    chill_lofi = {
        "favorite_genre":       "lofi",    # primary genre preference
        "favorite_mood":        "focused", # preferred emotional atmosphere
        "target_energy":        0.42,      # calm but not completely passive
        "target_tempo_bpm":     80.0,      # slow-to-mid tempo; nothing frantic
        "target_valence":       0.62,      # slightly positive, not euphoric
        "target_danceability":  0.58,      # gentle groove is fine
        "target_acousticness":  0.78,      # strongly prefers acoustic/organic textures
        "likes_acoustic":       True,
    }

    # Profile 3: Deep Intense Rock
    # A listener who craves heavy, driving rock with raw emotion and aggression.
    deep_intense_rock = {
        "favorite_genre":       "rock",    # primary genre preference
        "favorite_mood":        "intense", # wants dark, powerful tracks
        "target_energy":        0.88,      # very high energy
        "target_tempo_bpm":     148.0,     # fast, driving tempo
        "target_valence":       0.35,      # darker, more serious tone
        "target_danceability":  0.55,      # rhythmic but not club-oriented
        "target_acousticness":  0.12,      # prefers amplified/electric sound
        "likes_acoustic":       False,
    }

    # --- Adversarial / edge-case profiles ---
    # Each one is designed to expose a specific blind spot in score_song.

    # Edge case 1: Conflicting energy + mood
    # High energy (0.92) but wants a "peaceful" mood.  score_song treats these
    # as independent axes, so it can recommend a perfectly energy-matched song
    # whose mood is the opposite of what the user actually wants.
    contradictory_energy_mood = {
        "favorite_genre":       "meditation",
        "favorite_mood":        "peaceful",  # wants calm, serene atmosphere
        "target_energy":        0.92,        # but also wants near-max energy — contradiction
        "target_tempo_bpm":     130.0,
        "target_valence":       0.50,
        "target_danceability":  0.50,
        "target_acousticness":  0.50,
        "likes_acoustic":       False,
    }

    # Edge case 2: Ghost genre (genre absent from the catalog)
    # "classical" doesn't exist in songs.csv, so the +2.0 genre bonus never
    # fires.  Every song starts from 0, and the winner is decided purely by
    # energy proximity — the user effectively gets random-feeling results with
    # no genre relevance at all.
    ghost_genre = {
        "favorite_genre":       "classical",  # not in the catalog
        "favorite_mood":        "relaxed",
        "target_energy":        0.35,
        "target_tempo_bpm":     70.0,
        "target_valence":       0.65,
        "target_danceability":  0.40,
        "target_acousticness":  0.85,
        "likes_acoustic":       True,
    }

    # Edge case 3: Silent preferences
    # This user has extreme but completely ignored preferences: they hate
    # danceability (0.02) and love acousticness (0.99), yet score_song never
    # reads those keys.  The top results may be highly danceable electronic
    # tracks — exactly the opposite of what was requested.
    silent_preferences = {
        "favorite_genre":       "folk",
        "favorite_mood":        "relaxed",
        "target_energy":        0.40,
        "target_tempo_bpm":     75.0,
        "target_valence":       0.70,
        "target_danceability":  0.02,   # ignored by scorer — user hates dancing
        "target_acousticness":  0.99,   # ignored by scorer — wants pure acoustic
        "likes_acoustic":       True,
    }

    # Edge case 4: Out-of-range energy target
    # target_energy=1.5 is above the [0,1] range of song energies.  The
    # formula  1.0 - |song_energy - 1.5|  always produces a value ≤ 0.5,
    # and for songs with energy < 0.5 it goes negative.  A song with
    # energy=0.0 scores -0.5 on energy similarity, which can drag its total
    # below zero — unexpected and undocumented behaviour.
    out_of_range_energy = {
        "favorite_genre":       "pop",
        "favorite_mood":        "happy",
        "target_energy":        1.5,    # outside the valid 0.0–1.0 range
        "target_tempo_bpm":     120.0,
        "target_valence":       0.85,
        "target_danceability":  0.80,
        "target_acousticness":  0.10,
        "likes_acoustic":       False,
    }

    # Edge case 5: Genre dominance swamps a bad energy fit
    # The user wants pop (gets +2.0) but targets energy=0.10 — very low.
    # Most pop songs are high-energy (0.8+), so energy similarity is ~0.2.
    # Total for a pop song ≈ 2.0 + 0.2 = 2.2.  A non-pop song with
    # energy=0.10 scores ~1.0 (perfect energy, no genre bonus).  The pop
    # songs "win" even though they're a terrible energy match, showing that
    # a single categorical bonus can overwhelm the continuous signal.
    genre_dominance = {
        "favorite_genre":       "pop",
        "favorite_mood":        "happy",
        "target_energy":        0.10,   # extremely low — almost no pop song fits
        "target_tempo_bpm":     55.0,
        "target_valence":       0.30,
        "target_danceability":  0.20,
        "target_acousticness":  0.90,
        "likes_acoustic":       True,
    }

    profiles = [
        ("High-Energy Pop",              high_energy_pop),
        ("Chill Lofi",                   chill_lofi),
        ("Deep Intense Rock",            deep_intense_rock),
        # adversarial profiles
        ("[EDGE] Contradictory Energy+Mood", contradictory_energy_mood),
        ("[EDGE] Ghost Genre",               ghost_genre),
        ("[EDGE] Silent Preferences",        silent_preferences),
        ("[EDGE] Out-of-Range Energy",       out_of_range_energy),
        ("[EDGE] Genre Dominance",           genre_dominance),
    ]

    for profile_name, user_prefs in profiles:
        recommendations = recommend_songs(user_prefs, songs, k=5)

        print("\n" + "=" * 50)
        print(f"   Top 5 Recommendations for: {profile_name}")
        print("=" * 50)
        for rank, (song, score, explanation) in enumerate(recommendations, start=1):
            print(f"\n#{rank}  {song['title']}  —  {song['artist']}")
            print(f"    Genre: {song['genre']}  |  Mood: {song['mood']}  |  Score: {score:.2f}")
            print(f"    Why: {explanation}")


if __name__ == "__main__":
    main()
