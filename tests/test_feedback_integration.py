"""Integration tests -- require ANTHROPIC_API_KEY to be set.

Run with: pytest tests/test_feedback_integration.py -v

These tests make real API calls. Skip them in CI or when no key is available.
"""

import os

import pytest
from dotenv import load_dotenv

load_dotenv()

from app.feedback import get_feedback
from app.models import FeedbackRequest

pytestmark = pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set -- skipping integration tests",
)

VALID_ERROR_TYPES = {
    "grammar",
    "spelling",
    "word_choice",
    "punctuation",
    "word_order",
    "missing_word",
    "extra_word",
    "conjugation",
    "gender_agreement",
    "number_agreement",
    "tone_register",
    "other",
}
VALID_DIFFICULTIES = {"A1", "A2", "B1", "B2", "C1", "C2"}


def test_spanish_conjugation_error():
    result = get_feedback(
        FeedbackRequest(
            sentence="Yo soy fue al mercado ayer.",
            target_language="Spanish",
            native_language="English",
        )
    )
    assert result.is_correct is False
    assert len(result.errors) >= 1
    assert result.difficulty in VALID_DIFFICULTIES
    for error in result.errors:
        assert error.error_type in VALID_ERROR_TYPES
        assert len(error.explanation) > 0


def test_correct_german():
    result = get_feedback(
        FeedbackRequest(
            sentence="Ich habe gestern einen interessanten Film gesehen.",
            target_language="German",
            native_language="English",
        )
    )
    assert result.is_correct is True
    assert result.errors == []
    assert result.corrected_sentence == "Ich habe gestern einen interessanten Film gesehen."
    assert result.difficulty in VALID_DIFFICULTIES


def test_french_gender_agreement():
    result = get_feedback(
        FeedbackRequest(
            sentence="La chat noir est sur le table.",
            target_language="French",
            native_language="English",
        )
    )
    assert result.is_correct is False
    assert len(result.errors) >= 1
    assert any(e.error_type in {"gender_agreement", "grammar"} for e in result.errors)


def test_japanese_particle():
    result = get_feedback(
        FeedbackRequest(
            sentence="私は東京を住んでいます。",
            target_language="Japanese",
            native_language="English",
        )
    )
    assert result.is_correct is False
    assert any("に" in e.correction for e in result.errors)


def test_correct_sentence_empty_errors():
    sentence = "Je mange une pomme."
    result = get_feedback(
        FeedbackRequest(
            sentence=sentence,
            target_language="French",
            native_language="English",
        )
    )
    assert result.is_correct is True
    assert result.errors == []
    assert result.corrected_sentence == sentence


def test_multiple_errors_english():
    result = get_feedback(
        FeedbackRequest(
            sentence="He go to school yesterday and don't did his homework.",
            target_language="English",
            native_language="Spanish",
        )
    )
    assert result.is_correct is False
    assert len(result.errors) >= 2
    for error in result.errors:
        assert error.error_type in VALID_ERROR_TYPES
        assert len(error.explanation) > 0


def test_russian_cyrillic():
    result = get_feedback(
        FeedbackRequest(
            sentence="Я идти в магазин вчера.",
            target_language="Russian",
            native_language="English",
        )
    )
    assert result.is_correct is False
    assert result.difficulty in VALID_DIFFICULTIES
    assert any(
        any("\u0400" <= ch <= "\u04ff" for ch in e.correction)
        for e in result.errors
    )


def test_explanation_in_native_language_not_target():
    result = get_feedback(
        FeedbackRequest(
            sentence="Ich habe gegessen ein Apfel.",
            target_language="German",
            native_language="English",
        )
    )
    assert result.is_correct is False
    for error in result.errors:
        lowered = error.explanation.lower()
        assert any(word in lowered for word in {"the", "a", "an", "you", "your", "this", "is", "are", "was"})


def test_high_cefr_difficulty():
    result = get_feedback(
        FeedbackRequest(
            sentence="Notwithstanding the aforementioned stipulations, the contract shall remain in full force.",
            target_language="English",
            native_language="Spanish",
        )
    )
    assert result.difficulty in {"B2", "C1", "C2"}


def test_low_cefr_difficulty():
    result = get_feedback(
        FeedbackRequest(
            sentence="I am happy.",
            target_language="English",
            native_language="Spanish",
        )
    )
    assert result.difficulty in {"A1", "A2"}


def test_schema_fields_always_present():
    result = get_feedback(
        FeedbackRequest(
            sentence="El perro es muy rapido.",
            target_language="Spanish",
            native_language="English",
        )
    )
    assert hasattr(result, "corrected_sentence")
    assert hasattr(result, "is_correct")
    assert hasattr(result, "errors")
    assert hasattr(result, "difficulty")
    assert isinstance(result.errors, list)
    assert result.difficulty in VALID_DIFFICULTIES