"""
Live Ollama integration tests for extract_action_items_llm().

These call a real local Ollama server. They are skipped automatically when the
server is down or the configured model is not pulled.

Run only these tests:
  pytest week2/tests/test_extract_ollama_live.py -v

Exclude from CI / default runs (mocked tests in test_extract.py still run):
  pytest week2/tests/ -m "not ollama"

Requires: Ollama running (default http://localhost:11434) and a model that
supports structured outputs. Default model matches extract._DEFAULT_OLLAMA_MODEL;
override with OLLAMA_MODEL.
"""

from __future__ import annotations

import functools
import os

import ollama
import pytest

from week2.app.services import extract as extract_mod
from week2.app.services.extract import extract_action_items_llm


@functools.lru_cache(maxsize=1)
def _live_ollama_skip_reason() -> str | None:
    try:
        ollama.list()
    except Exception as exc:
        return f"Ollama server not reachable: {exc!r}"

    model = os.environ.get("OLLAMA_MODEL", extract_mod._DEFAULT_OLLAMA_MODEL)
    try:
        ollama.show(model)
    except Exception as exc:
        return (
            f"Ollama model {model!r} not available: {exc!r} "
            f"(try: ollama pull {model})"
        )
    return None


_skip = _live_ollama_skip_reason()
pytestmark = [
    pytest.mark.ollama,
    pytest.mark.skipif(_skip is not None, reason=_skip or "ollama unavailable"),
]


def test_live_llm_bullet_list_extracts_tasks():
    text = """
    Sprint planning:
    - Set up PostgreSQL and run migrations
    * Implement the /extract API endpoint
    1. Add pytest coverage for extract.py
    The team liked the donuts.
    """.strip()

    items = extract_action_items_llm(text)

    assert isinstance(items, list)
    assert len(items) >= 2
    joined = " ".join(s.lower() for s in items)
    assert "database" in joined or "postgres" in joined or "migration" in joined
    assert "extract" in joined or "api" in joined or "endpoint" in joined
    assert all(isinstance(s, str) and s.strip() for s in items)


def test_live_llm_keyword_prefixed_lines():
    text = """
    todo: Email the client about the delay
    action: Schedule a standup for Tuesday
    next: Deploy the hotfix to staging

    Random thought: the logo colors are nice.
    """.strip()

    items = extract_action_items_llm(text)

    assert isinstance(items, list)
    assert len(items) >= 2
    joined = " ".join(s.lower() for s in items)
    assert "email" in joined or "client" in joined
    assert "standup" in joined or "schedule" in joined or "tuesday" in joined


def test_live_llm_mostly_informational_note():
    text = """
    Yesterday was sunny. We discussed the architecture at a high level
    but made no decisions. Everyone enjoyed the coffee.
    """.strip()

    items = extract_action_items_llm(text)

    assert isinstance(items, list)
    # Small models sometimes invent tasks; allow at most one soft hallucination.
    assert len(items) <= 1
