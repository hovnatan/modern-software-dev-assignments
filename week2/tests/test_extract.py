import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from ollama import ResponseError

from ..app.exceptions import LLMUnavailableError
from ..app.services.extract import extract_action_items, extract_action_items_llm


def test_extract_bullets_and_checkboxes():
    text = """
    Notes from meeting:
    - [ ] Set up database
    * implement API extract endpoint
    1. Write tests
    Some narrative sentence.
    """.strip()

    items = extract_action_items(text)
    assert "Set up database" in items
    assert "implement API extract endpoint" in items
    assert "Write tests" in items


def _ollama_response_json(items: list[str]) -> SimpleNamespace:
    """Minimal shape used by extract_action_items_llm (response.message.content)."""
    return SimpleNamespace(
        message=SimpleNamespace(content=json.dumps({"items": items})),
    )


@patch("week2.app.services.extract.chat")
def test_extract_action_items_llm_empty_string_no_ollama_call(mock_chat):
    assert extract_action_items_llm("") == []
    mock_chat.assert_not_called()


@patch("week2.app.services.extract.chat")
def test_extract_action_items_llm_whitespace_only_no_ollama_call(mock_chat):
    assert extract_action_items_llm("   \n\t  ") == []
    mock_chat.assert_not_called()


@patch("week2.app.services.extract.chat")
def test_extract_action_items_llm_bullet_list_note(mock_chat):
    mock_chat.return_value = _ollama_response_json(
        [
            "Set up database",
            "Implement API extract endpoint",
            "Write tests",
        ]
    )
    text = """
    Notes from meeting:
    - Set up database
    * Implement API extract endpoint
    1. Write tests
    Some narrative sentence.
    """.strip()

    items = extract_action_items_llm(text)

    assert items == [
        "Set up database",
        "Implement API extract endpoint",
        "Write tests",
    ]
    mock_chat.assert_called_once()
    call_kwargs = mock_chat.call_args.kwargs
    user_message = call_kwargs["messages"][-1]["content"]
    assert "Set up database" in user_message
    assert call_kwargs.get("format") is not None
    assert call_kwargs.get("options") == {"temperature": 0}


@patch("week2.app.services.extract.chat")
def test_extract_action_items_llm_keyword_prefixed_lines(mock_chat):
    mock_chat.return_value = _ollama_response_json(
        [
            "Email the client",
            "Schedule standup",
        ]
    )
    text = """
    todo: Email the client
    action: Schedule standup
    FYI: lunch was fine.
    """.strip()

    items = extract_action_items_llm(text)

    assert items == ["Email the client", "Schedule standup"]


@patch("week2.app.services.extract.chat")
def test_extract_action_items_llm_strips_whitespace_and_dedupes(mock_chat):
    mock_chat.return_value = _ollama_response_json(
        [
            "  Fix bug  ",
            "Fix bug",
            "Another task",
        ]
    )

    items = extract_action_items_llm("any note body")

    assert items == ["Fix bug", "Another task"]


@patch("week2.app.services.extract.chat")
def test_extract_action_items_llm_empty_items_array(mock_chat):
    mock_chat.return_value = _ollama_response_json([])

    items = extract_action_items_llm("Nothing to do here, just thoughts.")

    assert items == []


@patch("week2.app.services.extract.chat")
def test_extract_action_items_llm_empty_message_content(mock_chat):
    mock_chat.return_value = SimpleNamespace(message=SimpleNamespace(content=None))

    assert extract_action_items_llm("some text") == []


@patch("week2.app.services.extract.chat")
def test_extract_action_items_llm_maps_ollama_errors(mock_chat):
    mock_chat.side_effect = ResponseError("model not found", status_code=404)

    with pytest.raises(LLMUnavailableError) as exc_info:
        extract_action_items_llm("do something")

    assert "Ollama" in exc_info.value.message or "unreachable" in exc_info.value.message.lower()
