"""
Agentic workflow for the music recommender.

Turn 0 — Plan: Gemini reasons about the user request before extraction.
Turn 1 — Extract: Gemini converts free-text input into a structured
          UserProfile dict using function calling (guaranteed structured output).
Turn 2 — Reflect: Gemini reviews top-5 results and optionally refines one
          preference field, triggering a single re-run of retrieval + scoring.

All API calls are logged as JSON Lines to logs/agent.log.
"""

import json
import logging
import os
import sys
import pathlib
from datetime import datetime, timezone

from google import genai
from google.genai import types

from .recommender import load_songs, recommend_songs
from .retriever import load_embeddings, retrieve_candidates

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

LOG_DIR = pathlib.Path("logs")
LOG_FILE = LOG_DIR / "agent.log"

logging.basicConfig(
    level=logging.INFO,
    format="[agent] %(message)s",
    stream=sys.stderr,
)
_logger = logging.getLogger("music_agent")

_MODEL_NAME = "gemini-2.5-flash"


def _log_event(event: str, data: dict) -> None:
    """Append a JSON Lines record to logs/agent.log."""
    LOG_DIR.mkdir(exist_ok=True)
    record = {"timestamp": datetime.now(timezone.utc).isoformat(), "event": event, **data}
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def _strip_fences(text: str) -> str:
    """Remove markdown code fences from a JSON response."""
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


# ---------------------------------------------------------------------------
# Tool definition for structured extraction
# ---------------------------------------------------------------------------

def set_user_prefs(
    favorite_genre: str,
    favorite_mood: str,
    target_energy: float,
    target_tempo_bpm: float,
    target_valence: float,
    target_danceability: float,
    target_acousticness: float,
    likes_acoustic: bool,
) -> dict:
    """Record the user's music preferences extracted from their natural-language description.
    Choose the closest matching genre and mood from what exists in the catalog.

    Args:
        favorite_genre: Closest genre. Known genres: pop, lofi, rock, ambient, jazz, synthwave, indie pop, country, electronic, folk, metal, bossa nova, darkwave, bluegrass, meditation, hip-hop, indie folk, reggae, soul, r&b, trap, classical.
        favorite_mood: Closest mood. Known moods: happy, chill, intense, focused, relaxed, moody, nostalgic, angry, joyful, romantic, melancholic, peaceful.
        target_energy: Energy level 0.0 (very calm) to 1.0 (very intense).
        target_tempo_bpm: Beats per minute, typically 50 to 175.
        target_valence: Positivity 0.0 (dark/sad) to 1.0 (bright/happy).
        target_danceability: Danceability 0.0 (not danceable) to 1.0 (very danceable).
        target_acousticness: Acousticness 0.0 (fully electronic) to 1.0 (fully acoustic).
        likes_acoustic: True if the user prefers acoustic/organic sound.
    """
    return {}


_SYSTEM_PROMPT = (
    "You are a music preference parser. "
    "Extract structured music preferences from the user's description. "
    "Always call the set_user_prefs function — never reply with prose."
)

# ---------------------------------------------------------------------------
# Guardrails
# ---------------------------------------------------------------------------

_DEFAULTS = {
    "favorite_genre": "pop",
    "favorite_mood": "happy",
    "target_energy": 0.5,
    "target_tempo_bpm": 100.0,
    "target_valence": 0.5,
    "target_danceability": 0.5,
    "target_acousticness": 0.5,
    "likes_acoustic": False,
}
_KNOWN_GENRES = {
    "pop", "lofi", "rock", "ambient", "jazz", "synthwave", "indie pop",
    "country", "electronic", "folk", "metal", "bossa nova", "darkwave",
    "bluegrass", "meditation", "hip-hop", "indie folk", "reggae", "soul",
    "r&b", "trap", "classical",
}
_KNOWN_MOODS = {
    "happy", "chill", "intense", "focused", "relaxed", "moody",
    "nostalgic", "angry", "joyful", "romantic", "melancholic", "peaceful",
}


def _validate_prefs(prefs: dict) -> dict:
    """Clamp floats, fill missing keys, warn on unknown genre/mood."""
    result = {**_DEFAULTS, **prefs}

    for field in ("target_energy", "target_valence", "target_danceability", "target_acousticness"):
        result[field] = max(0.0, min(1.0, float(result[field])))

    result["target_tempo_bpm"] = max(30.0, min(220.0, float(result["target_tempo_bpm"])))

    if result["favorite_genre"] not in _KNOWN_GENRES:
        _logger.warning(
            "Genre '%s' is not in the catalog — results may be energy-only matches.",
            result["favorite_genre"],
        )
    if result["favorite_mood"] not in _KNOWN_MOODS:
        _logger.warning("Mood '%s' is not in the catalog.", result["favorite_mood"])

    return result


# ---------------------------------------------------------------------------
# Turn 0 — Plan
# ---------------------------------------------------------------------------

_PLAN_SYSTEM_PROMPT = (
    "You are a music intent analyst. "
    "Read the user's request and output ONLY valid JSON with these keys: "
    "likely_energy (one of: low / moderate / high), "
    "likely_genre_family (short label), "
    "likely_mood (short label), "
    "ambiguities (list of strings — what is unclear), "
    "reasoning (one sentence explaining your interpretation). "
    "Do not call any tools. Do not include any text outside the JSON object."
)


def plan_request(user_text: str, client: genai.Client) -> dict:
    """
    Turn 0: Gemini briefly reasons about the user's request before extraction.
    Returns a dict with keys: likely_energy, likely_genre_family, likely_mood,
    ambiguities, reasoning. Falls back to an empty dict on parse failure.
    """
    _logger.info("Turn 0: planning intent for: '%s'", user_text)

    response = client.models.generate_content(
        model=_MODEL_NAME,
        contents=user_text,
        config=types.GenerateContentConfig(
            system_instruction=_PLAN_SYSTEM_PROMPT,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        ),
    )

    raw_text = _strip_fences(response.text)
    try:
        plan = json.loads(raw_text)
    except json.JSONDecodeError:
        _logger.warning("Turn 0 response was not valid JSON — skipping plan context.")
        plan = {}

    _log_event("plan", {
        "user_input": user_text,
        "tokens_in": response.usage_metadata.prompt_token_count,
        "tokens_out": response.usage_metadata.candidates_token_count,
        "plan": plan,
    })
    return plan


# ---------------------------------------------------------------------------
# Turn 1 — Extract
# ---------------------------------------------------------------------------

def extract_user_prefs(user_text: str, client: genai.Client, plan: dict | None = None) -> dict:
    """Call Gemini to extract a structured UserProfile dict from free text.

    If a Turn 0 plan dict is provided, it is prepended to the extraction
    prompt so Gemini's reasoning is grounded in its own prior analysis.
    """
    _logger.info("Turn 1: extracting preferences from: '%s'", user_text)

    if plan:
        user_message = (
            f"Your prior analysis of this request: {json.dumps(plan)}\n\n"
            f"User request: {user_text}"
        )
    else:
        user_message = user_text

    response = client.models.generate_content(
        model=_MODEL_NAME,
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_PROMPT,
            tools=[set_user_prefs],
            tool_config=types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(mode="ANY"),
            ),
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        ),
    )

    fn_calls = response.function_calls
    if not fn_calls or fn_calls[0].name != "set_user_prefs":
        raise ValueError("Gemini did not return a function_call during extraction.")

    raw_prefs = dict(fn_calls[0].args)
    prefs = _validate_prefs(raw_prefs)

    _log_event("extract", {
        "user_input": user_text,
        "tokens_in": response.usage_metadata.prompt_token_count,
        "tokens_out": response.usage_metadata.candidates_token_count,
        "profile": prefs,
    })
    _logger.info(
        "  Extracted: genre=%s, mood=%s, energy=%.2f",
        prefs["favorite_genre"], prefs["favorite_mood"], prefs["target_energy"],
    )
    return prefs


# ---------------------------------------------------------------------------
# Turn 2 — Reflect & optionally refine
# ---------------------------------------------------------------------------

def reflect_and_refine(
    user_text: str,
    user_prefs: dict,
    results: list[tuple],
    client: genai.Client,
) -> tuple:
    """
    Ask Gemini whether the top-5 results match the user's intent.

    Returns (final_results, reflection_text). If Gemini proposes a refinement,
    one field is adjusted and recommend_songs is re-run once (hard cap).
    """
    _logger.info("Turn 2: reflecting on top-%d results...", len(results))

    results_summary = "\n".join(
        f"  {i+1}. {r[0]['title']} by {r[0]['artist']} "
        f"(genre={r[0]['genre']}, mood={r[0]['mood']}, score={r[1]:.2f})"
        for i, r in enumerate(results)
    )

    reflect_prompt = (
        f"A user asked for: \"{user_text}\"\n\n"
        f"You extracted these preferences:\n{json.dumps(user_prefs, indent=2)}\n\n"
        f"The top recommendations are:\n{results_summary}\n\n"
        "Do these results match what the user was looking for?\n"
        "Reply with ONLY valid JSON in one of these two formats:\n"
        '  {"verdict": "pass", "reflection": "<one sentence>"}\n'
        '  {"verdict": "refine", "field": "<field_name>", '
        '"new_value": <value>, "reflection": "<one sentence>"}\n'
        "Do not include any text outside the JSON object."
    )

    response = client.models.generate_content(
        model=_MODEL_NAME,
        contents=reflect_prompt,
        config=types.GenerateContentConfig(
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        ),
    )

    raw_text = _strip_fences(response.text)

    try:
        verdict_data = json.loads(raw_text)
    except json.JSONDecodeError:
        _logger.warning("Reflection response was not valid JSON — keeping original results.")
        _log_event("reflect", {
            "verdict": "parse_error",
            "raw_response": raw_text,
            "tokens_in": response.usage_metadata.prompt_token_count,
            "tokens_out": response.usage_metadata.candidates_token_count,
        })
        return results, raw_text

    verdict = verdict_data.get("verdict", "pass")
    reflection = verdict_data.get("reflection", "")
    _logger.info("  Reflection verdict: %s — %s", verdict, reflection)

    if verdict == "refine":
        field = verdict_data.get("field")
        new_value = verdict_data.get("new_value")

        if field and field in _DEFAULTS and new_value is not None:
            refined_prefs = {**user_prefs, field: new_value}
            refined_prefs = _validate_prefs(refined_prefs)
            _logger.info("  Refining: %s → %s", field, new_value)

            _log_event("reflect", {
                "verdict": "refine",
                "field_changed": field,
                "new_value": new_value,
                "reflection": reflection,
                "tokens_in": response.usage_metadata.prompt_token_count,
                "tokens_out": response.usage_metadata.candidates_token_count,
            })
            return None, reflection, refined_prefs  # signal to caller to re-run

    _log_event("reflect", {
        "verdict": verdict,
        "reflection": reflection,
        "tokens_in": response.usage_metadata.prompt_token_count,
        "tokens_out": response.usage_metadata.candidates_token_count,
    })
    return results, reflection


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run_agent(
    user_text: str,
    songs_path: str = "data/songs.csv",
    k: int = 5,
) -> None:
    """Full agentic pipeline: plan → extract → RAG retrieve → score → reflect → print."""

    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        print("Error: GOOGLE_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    # Load catalog
    songs = load_songs(songs_path)

    # Load precomputed embeddings
    try:
        embeddings, ordered_songs = load_embeddings(songs)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Turn 0 — plan: Gemini reasons about the request before extracting
    try:
        plan = plan_request(user_text, client)
    except Exception as e:
        _logger.warning("Turn 0 planning failed (%s) — proceeding without plan context.", e)
        plan = {}

    if plan:
        print(f"\nTurn 0 — Planning:")
        print(f"  Energy:  {plan.get('likely_energy', '?')}")
        print(f"  Genre:   {plan.get('likely_genre_family', '?')}")
        print(f"  Mood:    {plan.get('likely_mood', '?')}")
        if plan.get("ambiguities"):
            print(f"  Unclear: {'; '.join(plan['ambiguities'])}")
        print(f"  Notes:   {plan.get('reasoning', '')}")

    # Turn 1 — extract structured preferences (informed by Turn 0 plan)
    try:
        user_prefs = extract_user_prefs(user_text, client, plan=plan)
    except Exception as e:
        print(f"Error during preference extraction: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"\nTurn 1 — Extracted preferences:")
    print(f"  Genre: {user_prefs['favorite_genre']}  |  Mood: {user_prefs['favorite_mood']}")
    print(f"  Energy: {user_prefs['target_energy']:.2f}  |  Acousticness: {user_prefs['target_acousticness']:.2f}")

    # RAG retrieval — narrow catalog to 30 semantic candidates
    _logger.info("RAG: retrieving top-30 candidates from %d songs...", len(ordered_songs))
    candidates = retrieve_candidates(user_prefs, embeddings, ordered_songs, top_n=30)
    _log_event("retrieve", {"candidates_found": len(candidates)})

    # Rule-based scoring on candidates
    results = recommend_songs(user_prefs, candidates, k=k)

    # Turn 2 — reflect and optionally refine once
    try:
        outcome = reflect_and_refine(user_text, user_prefs, results, client)
    except Exception as e:
        _logger.warning("Reflection failed (%s) — using original results.", e)
        outcome = (results, "Reflection skipped due to error.")

    # outcome is either (results, reflection) or (None, reflection, refined_prefs)
    if len(outcome) == 3 and outcome[0] is None:
        _, reflection, refined_prefs = outcome
        _logger.info("Re-running with refined preferences...")
        candidates = retrieve_candidates(refined_prefs, embeddings, ordered_songs, top_n=30)
        results = recommend_songs(refined_prefs, candidates, k=k)
        _log_event("refine_result", {"refined_prefs": refined_prefs})
    else:
        results, reflection = outcome

    # Print final recommendations
    print(f"\n{'='*52}")
    print(f"  Top {k} Recommendations for: \"{user_text[:45]}\"")
    print(f"{'='*52}")
    for rank, (song, score, explanation, confidence) in enumerate(results, start=1):
        print(f"\n#{rank}  {song['title']}  —  {song['artist']}")
        print(f"    Genre: {song['genre']}  |  Mood: {song['mood']}  |  Score: {score:.2f}  |  Confidence: {confidence:.0%}")
        print(f"    Why: {explanation}")

    if reflection:
        print(f"\nGemini says: \"{reflection}\"")

    _log_event("final", {
        "user_input": user_text,
        "top_results": [
            {"title": s["title"], "genre": s["genre"], "score": round(sc, 3)}
            for s, sc, _, _conf in results
        ],
    })
