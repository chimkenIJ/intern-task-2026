"""Unit tests -- run without an API key using mocked LLM responses."""

import json
from unittest.mock import MagicMock, patch

import pytest
from app.feedback import get_feedback, _cached_call
from app.models import FeedbackRequest


def _mock_message(response_data: dict) -> MagicMock:
    content_block = MagicMock()
    content_block.text = json.dumps(response_data)
    message = MagicMock()
    message.content = [content_block]
    return message


def _make_request(**kwargs) -> FeedbackRequest:
    defaults = {
        "sentence": "test",
        "target_language": "Spanish",
        "native_language": "English",
    }
    defaults.update(kwargs)
    return FeedbackRequest(**defaults)


@pytest.fixture(autouse=True)
def clear_lru_cache():
    _cached_call.cache_clear()
    yield
    _cached_call.cache_clear()


def test_feedback_with_errors():
    mock_response = {
        "corrected_sentence": "Yo fui al mercado ayer.",
        "is_correct": False,
        "errors": [
            {
                "original": "soy fue",
                "correction": "fui",
                "error_type": "conjugation",
                "explanation": "You mixed two verb forms.",
            }
        ],
        "difficulty": "A2",
    }

    with patch("app.feedback._client.messages.create", return_value=_mock_message(mock_response)):
        result = get_feedback(_make_request(sentence="Yo soy fue al mercado ayer."))

    assert result.is_correct is False
    assert result.corrected_sentence == "Yo fui al mercado ayer."
    assert len(result.errors) == 1
    assert result.errors[0].error_type == "conjugation"
    assert result.difficulty == "A2"


def test_feedback_correct_sentence():
    sentence = "Ich habe gestern einen interessanten Film gesehen."
    mock_response = {
        "corrected_sentence": sentence,
        "is_correct": True,
        "errors": [],
        "difficulty": "B1",
    }

    with patch("app.feedback._client.messages.create", return_value=_mock_message(mock_response)):
        result = get_feedback(_make_request(sentence=sentence, target_language="German"))

    assert result.is_correct is True
    assert result.errors == []
    assert result.corrected_sentence == sentence


def test_feedback_multiple_errors():
    mock_response = {
        "corrected_sentence": "Le chat noir est sur la table.",
        "is_correct": False,
        "errors": [
            {
                "original": "La chat",
                "correction": "Le chat",
                "error_type": "gender_agreement",
                "explanation": "'Chat' is masculine.",
            },
            {
                "original": "le table",
                "correction": "la table",
                "error_type": "gender_agreement",
                "explanation": "'Table' is feminine.",
            },
        ],
        "difficulty": "A1",
    }

    with patch("app.feedback._client.messages.create", return_value=_mock_message(mock_response)):
        result = get_feedback(_make_request(
            sentence="La chat noir est sur le table.",
            target_language="French",
        ))

    assert result.is_correct is False
    assert len(result.errors) == 2
    assert all(e.error_type == "gender_agreement" for e in result.errors)


def test_sanitize_forces_is_correct_false_when_errors_present():
    mock_response = {
        "corrected_sentence": "Yo fui al mercado.",
        "is_correct": True,
        "errors": [
            {
                "original": "soy fue",
                "correction": "fui",
                "error_type": "conjugation",
                "explanation": "Mixed verb forms.",
            }
        ],
        "difficulty": "A2",
    }

    with patch("app.feedback._client.messages.create", return_value=_mock_message(mock_response)):
        result = get_feedback(_make_request())

    assert result.is_correct is False
    assert len(result.errors) == 1


def test_sanitize_correct_sentence_no_errors():
    mock_response = {
        "corrected_sentence": "The sky is blue.",
        "is_correct": True,
        "errors": [],
        "difficulty": "A1",
    }

    with patch("app.feedback._client.messages.create", return_value=_mock_message(mock_response)):
        result = get_feedback(_make_request(sentence="The sky is blue.", target_language="English"))

    assert result.is_correct is True
    assert result.errors == []
    assert result.corrected_sentence == "The sky is blue."


def test_sanitize_invalid_error_type_becomes_other():
    mock_response = {
        "corrected_sentence": "Yo fui.",
        "is_correct": False,
        "errors": [
            {
                "original": "soy fue",
                "correction": "fui",
                "error_type": "tense_confusion",
                "explanation": "Wrong tense.",
            }
        ],
        "difficulty": "A1",
    }

    with patch("app.feedback._client.messages.create", return_value=_mock_message(mock_response)):
        result = get_feedback(_make_request())

    assert result.errors[0].error_type == "other"


def test_sanitize_invalid_difficulty_becomes_b1():
    mock_response = {
        "corrected_sentence": "Test.",
        "is_correct": True,
        "errors": [],
        "difficulty": "D4",
    }

    with patch("app.feedback._client.messages.create", return_value=_mock_message(mock_response)):
        result = get_feedback(_make_request(sentence="Test sentence.", target_language="English"))

    assert result.difficulty == "B1"


def test_lru_cache_prevents_duplicate_api_calls():
    mock_response = {
        "corrected_sentence": "Yo fui.",
        "is_correct": False,
        "errors": [
            {
                "original": "soy fue",
                "correction": "fui",
                "error_type": "conjugation",
                "explanation": "Mixed forms.",
            }
        ],
        "difficulty": "A2",
    }

    with patch("app.feedback._client.messages.create", return_value=_mock_message(mock_response)) as mock_api:
        get_feedback(_make_request())
        get_feedback(_make_request())

    mock_api.assert_called_once()