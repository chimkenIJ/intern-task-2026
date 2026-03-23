"""Schema validation tests -- verify models match JSON schemas."""

import json
from pathlib import Path

import jsonschema
import pytest
from app.models import FeedbackRequest, FeedbackResponse

SCHEMA_DIR = Path(__file__).parent.parent / "schema"
EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


def load_schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text())


def load_examples() -> list[dict]:
    return json.loads((EXAMPLES_DIR / "sample_inputs.json").read_text())


class TestRequestSchema:
    def test_valid_request(self):
        schema = load_schema("request.schema.json")
        valid = {
            "sentence": "Hola mundo",
            "target_language": "Spanish",
            "native_language": "English",
        }
        jsonschema.validate(valid, schema)

    def test_missing_sentence_fails(self):
        schema = load_schema("request.schema.json")
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(
                {"target_language": "Spanish", "native_language": "English"}, schema
            )

    def test_empty_sentence_fails(self):
        schema = load_schema("request.schema.json")
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(
                {
                    "sentence": "",
                    "target_language": "Spanish",
                    "native_language": "English",
                },
                schema,
            )

    def test_missing_target_language_fails(self):
        schema = load_schema("request.schema.json")
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(
                {"sentence": "Hola", "native_language": "English"}, schema
            )

    def test_missing_native_language_fails(self):
        schema = load_schema("request.schema.json")
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(
                {"sentence": "Hola", "target_language": "Spanish"}, schema
            )

    def test_non_latin_script_valid(self):
        """Japanese sentence must be accepted as a valid request."""
        schema = load_schema("request.schema.json")
        jsonschema.validate(
            {
                "sentence": "私は東京に住んでいます。",
                "target_language": "Japanese",
                "native_language": "English",
            },
            schema,
        )


class TestResponseSchema:
    def test_correct_response(self):
        schema = load_schema("response.schema.json")
        valid = {
            "corrected_sentence": "Hola mundo",
            "is_correct": True,
            "errors": [],
            "difficulty": "A1",
        }
        jsonschema.validate(valid, schema)

    def test_response_with_errors(self):
        schema = load_schema("response.schema.json")
        valid = {
            "corrected_sentence": "Le chat noir",
            "is_correct": False,
            "errors": [
                {
                    "original": "La chat",
                    "correction": "Le chat",
                    "error_type": "gender_agreement",
                    "explanation": "Chat is masculine",
                }
            ],
            "difficulty": "A1",
        }
        jsonschema.validate(valid, schema)

    def test_invalid_difficulty_fails(self):
        schema = load_schema("response.schema.json")
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(
                {
                    "corrected_sentence": "test",
                    "is_correct": True,
                    "errors": [],
                    "difficulty": "Z9",
                },
                schema,
            )

    def test_invalid_error_type_fails(self):
        schema = load_schema("response.schema.json")
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(
                {
                    "corrected_sentence": "test",
                    "is_correct": False,
                    "errors": [
                        {
                            "original": "x",
                            "correction": "y",
                            "error_type": "not_a_real_type",
                            "explanation": "test",
                        }
                    ],
                    "difficulty": "A1",
                },
                schema,
            )

    def test_missing_required_field_fails(self):
        """Response missing 'difficulty' must fail validation."""
        schema = load_schema("response.schema.json")
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(
                {
                    "corrected_sentence": "test",
                    "is_correct": True,
                    "errors": [],
                    # difficulty omitted
                },
                schema,
            )

    def test_all_valid_difficulties_accepted(self):
        """Every CEFR level must be accepted by the schema."""
        schema = load_schema("response.schema.json")
        for level in ("A1", "A2", "B1", "B2", "C1", "C2"):
            jsonschema.validate(
                {
                    "corrected_sentence": "test",
                    "is_correct": True,
                    "errors": [],
                    "difficulty": level,
                },
                schema,
            )

    def test_all_valid_error_types_accepted(self):
        """Every allowed error_type must pass schema validation."""
        schema = load_schema("response.schema.json")
        valid_types = [
            "grammar", "spelling", "word_choice", "punctuation", "word_order",
            "missing_word", "extra_word", "conjugation", "gender_agreement",
            "number_agreement", "tone_register", "other",
        ]
        for error_type in valid_types:
            jsonschema.validate(
                {
                    "corrected_sentence": "test",
                    "is_correct": False,
                    "errors": [
                        {
                            "original": "x",
                            "correction": "y",
                            "error_type": error_type,
                            "explanation": "test",
                        }
                    ],
                    "difficulty": "A1",
                },
                schema,
            )

    def test_error_missing_explanation_fails(self):
        """An error object without 'explanation' must fail schema validation."""
        schema = load_schema("response.schema.json")
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(
                {
                    "corrected_sentence": "test",
                    "is_correct": False,
                    "errors": [
                        {
                            "original": "x",
                            "correction": "y",
                            "error_type": "grammar",
                            # explanation omitted
                        }
                    ],
                    "difficulty": "A1",
                },
                schema,
            )


class TestExamplesMatchSchemas:
    """Verify that all example inputs/outputs conform to the schemas."""

    def test_all_example_requests_valid(self):
        schema = load_schema("request.schema.json")
        for example in load_examples():
            jsonschema.validate(example["request"], schema)

    def test_all_example_responses_valid(self):
        schema = load_schema("response.schema.json")
        for example in load_examples():
            jsonschema.validate(example["expected_response"], schema)