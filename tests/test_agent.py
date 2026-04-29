"""
Unit tests for src/agent.py — all Claude API calls are mocked so no
ANTHROPIC_API_KEY is required to run pytest.
"""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.agent import (
    _validate_prefs,
    extract_user_prefs,
    plan_request,
    reflect_and_refine,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tool_response(prefs: dict) -> MagicMock:
    """Build a mock Anthropic API response that returns a tool_use block."""
    tool_block = SimpleNamespace(type="tool_use", input=prefs)
    usage = SimpleNamespace(input_tokens=100, output_tokens=50)
    return SimpleNamespace(content=[tool_block], usage=usage)


def _make_text_response(text: str) -> MagicMock:
    """Build a mock Anthropic API response that returns a text block."""
    text_block = SimpleNamespace(type="text", text=text)
    usage = SimpleNamespace(input_tokens=80, output_tokens=40)
    return SimpleNamespace(content=[text_block], usage=usage)


def _fake_results() -> list[tuple]:
    song = {
        "id": 1, "title": "Test Song", "artist": "Artist",
        "genre": "lofi", "mood": "chill",
        "energy": 0.4, "tempo_bpm": 80.0, "valence": 0.6,
        "danceability": 0.5, "acousticness": 0.8,
    }
    return [(song, 3.5, "This song matches your favorite genre (lofi).")]


# ---------------------------------------------------------------------------
# _validate_prefs
# ---------------------------------------------------------------------------

def test_validate_clamps_energy_above_1():
    prefs = {"target_energy": 1.5}
    result = _validate_prefs(prefs)
    assert result["target_energy"] == 1.0


def test_validate_clamps_energy_below_0():
    prefs = {"target_energy": -0.2}
    result = _validate_prefs(prefs)
    assert result["target_energy"] == 0.0


def test_validate_fills_missing_keys():
    result = _validate_prefs({})
    required = [
        "favorite_genre", "favorite_mood", "target_energy",
        "target_tempo_bpm", "target_valence", "target_danceability",
        "target_acousticness", "likes_acoustic",
    ]
    for key in required:
        assert key in result, f"Missing key: {key}"


def test_validate_preserves_valid_values():
    prefs = {
        "favorite_genre": "lofi",
        "favorite_mood": "chill",
        "target_energy": 0.42,
        "target_tempo_bpm": 80.0,
        "target_valence": 0.6,
        "target_danceability": 0.58,
        "target_acousticness": 0.78,
        "likes_acoustic": True,
    }
    result = _validate_prefs(prefs)
    assert result["favorite_genre"] == "lofi"
    assert result["target_energy"] == pytest.approx(0.42)
    assert result["likes_acoustic"] is True


# ---------------------------------------------------------------------------
# plan_request (Turn 0)
# ---------------------------------------------------------------------------

def test_plan_request_returns_dict():
    plan_json = json.dumps({
        "likely_energy": "low",
        "likely_genre_family": "acoustic/folk",
        "likely_mood": "relaxed",
        "ambiguities": ["genre unclear"],
        "reasoning": "User said 'calm' and 'acoustic'.",
    })
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_text_response(plan_json)

    with patch("src.agent._log_event"):
        result = plan_request("something calm and acoustic", mock_client)

    assert result["likely_energy"] == "low"
    assert result["likely_genre_family"] == "acoustic/folk"
    assert isinstance(result["ambiguities"], list)


def test_plan_request_falls_back_on_invalid_json():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_text_response("Not JSON at all.")

    with patch("src.agent._log_event"):
        result = plan_request("anything", mock_client)

    assert result == {}


# ---------------------------------------------------------------------------
# extract_user_prefs
# ---------------------------------------------------------------------------

def test_extract_returns_required_keys():
    raw_prefs = {
        "favorite_genre": "lofi",
        "favorite_mood": "focused",
        "target_energy": 0.40,
        "target_tempo_bpm": 80.0,
        "target_valence": 0.6,
        "target_danceability": 0.55,
        "target_acousticness": 0.78,
        "likes_acoustic": True,
    }
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_tool_response(raw_prefs)

    with patch("src.agent._log_event"):
        result = extract_user_prefs("something calm to study to", mock_client)

    assert result["favorite_genre"] == "lofi"
    assert result["favorite_mood"] == "focused"
    assert 0.0 <= result["target_energy"] <= 1.0


def test_extract_raises_if_no_tool_use():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_text_response("Sorry, I cannot help.")

    with patch("src.agent._log_event"):
        with pytest.raises(ValueError, match="tool_use"):
            extract_user_prefs("some request", mock_client)


# ---------------------------------------------------------------------------
# reflect_and_refine
# ---------------------------------------------------------------------------

def test_reflect_pass_returns_original_results():
    verdict_json = json.dumps({"verdict": "pass", "reflection": "Results look great!"})
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_text_response(verdict_json)

    user_prefs = _validate_prefs({"favorite_genre": "lofi", "favorite_mood": "chill", "target_energy": 0.4})
    results = _fake_results()

    with patch("src.agent._log_event"):
        outcome = reflect_and_refine("study music", user_prefs, results, mock_client)

    final_results, reflection = outcome
    assert final_results is results
    assert "great" in reflection.lower()


def test_reflect_refine_signals_retry():
    verdict_json = json.dumps({
        "verdict": "refine",
        "field": "target_energy",
        "new_value": 0.25,
        "reflection": "Energy is too high for a peaceful request.",
    })
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_text_response(verdict_json)

    user_prefs = _validate_prefs({"favorite_genre": "ambient", "favorite_mood": "peaceful", "target_energy": 0.6})
    results = _fake_results()

    with patch("src.agent._log_event"):
        outcome = reflect_and_refine("peaceful ambient music", user_prefs, results, mock_client)

    assert len(outcome) == 3
    assert outcome[0] is None  # signals re-run
    _, reflection, refined_prefs = outcome
    assert refined_prefs["target_energy"] == pytest.approx(0.25)


def test_reflect_invalid_json_falls_back():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_text_response("This is not JSON at all.")

    user_prefs = _validate_prefs({"favorite_genre": "pop", "favorite_mood": "happy", "target_energy": 0.8})
    results = _fake_results()

    with patch("src.agent._log_event"):
        outcome = reflect_and_refine("happy pop music", user_prefs, results, mock_client)

    final_results, reflection = outcome
    assert final_results is results  # fallback: original results unchanged
