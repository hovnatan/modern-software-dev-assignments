from __future__ import annotations

import os
import re

from dotenv import load_dotenv
from ollama import chat
from pydantic import BaseModel, Field

load_dotenv()

BULLET_PREFIX_PATTERN = re.compile(r"^\s*([-*•]|\d+\.)\s+")
KEYWORD_PREFIXES = (
    "todo:",
    "action:",
    "next:",
)


def _is_action_line(line: str) -> bool:
    stripped = line.strip().lower()
    if not stripped:
        return False
    if BULLET_PREFIX_PATTERN.match(stripped):
        return True
    if any(stripped.startswith(prefix) for prefix in KEYWORD_PREFIXES):
        return True
    if "[ ]" in stripped or "[todo]" in stripped:
        return True
    return False


def extract_action_items(text: str) -> list[str]:
    lines = text.splitlines()
    extracted: list[str] = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if _is_action_line(line):
            cleaned = BULLET_PREFIX_PATTERN.sub("", line)
            cleaned = cleaned.strip()
            # Trim common checkbox markers
            cleaned = cleaned.removeprefix("[ ]").strip()
            cleaned = cleaned.removeprefix("[todo]").strip()
            extracted.append(cleaned)
    # Fallback: if nothing matched, heuristically split into sentences and pick imperative-like ones
    if not extracted:
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        for sentence in sentences:
            s = sentence.strip()
            if not s:
                continue
            if _looks_imperative(s):
                extracted.append(s)
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for item in extracted:
        lowered = item.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        unique.append(item)
    return unique


def _looks_imperative(sentence: str) -> bool:
    words = re.findall(r"[A-Za-z']+", sentence)
    if not words:
        return False
    first = words[0]
    # Crude heuristic: treat these as imperative starters
    imperative_starters = {
        "add",
        "create",
        "implement",
        "fix",
        "update",
        "write",
        "check",
        "verify",
        "refactor",
        "document",
        "design",
        "investigate",
    }
    return first.lower() in imperative_starters


class _ActionItemsLLMSchema(BaseModel):
    """Root object for Ollama structured output (JSON Schema requires an object)."""

    items: list[str] = Field(
        description="Concrete tasks someone should do; short imperative phrases without list markers.",
    )


# Small default; override with OLLAMA_MODEL (see https://ollama.com/library).
_DEFAULT_OLLAMA_MODEL = "llama3.1:8b"


def extract_action_items_llm(text: str) -> list[str]:
    """Extract action items using Ollama with JSON-schema-constrained output."""
    stripped = text.strip()
    if not stripped:
        return []

    model = os.environ.get("OLLAMA_MODEL", _DEFAULT_OLLAMA_MODEL)
    response = chat(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You extract actionable tasks from notes, emails, and meeting minutes. "
                    "Each item must be a standalone task (no leading bullets, numbers, or checkboxes). "
                    "Include follow-ups, deadlines, and assigned work; skip pure commentary. "
                    "If there are no tasks, respond with an empty items array."
                ),
            },
            {
                "role": "user",
                "content": f"Extract action items from this text:\n\n{stripped}",
            },
        ],
        format=_ActionItemsLLMSchema.model_json_schema(),
        options={"temperature": 0},
    )
    content = response.message.content
    if not content:
        return []

    parsed = _ActionItemsLLMSchema.model_validate_json(content)
    normalized = [item.strip() for item in parsed.items if item.strip()]

    seen: set[str] = set()
    unique: list[str] = []
    for item in normalized:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique
