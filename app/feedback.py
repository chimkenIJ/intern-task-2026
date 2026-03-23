"""System prompt and LLM interaction for language feedback."""

import json
import re
from functools import lru_cache

from anthropic import Anthropic

from app.models import FeedbackRequest, FeedbackResponse

SYSTEM_PROMPT = """\
You are an expert multilingual language tutor with deep knowledge of grammar \
across all world languages, including those with non-Latin scripts (Japanese, \
Korean, Chinese, Russian, Arabic, Hindi, etc.).

A language learner has written a sentence in their target language. Analyze it \
carefully and return structured feedback.

STRICT RULES:
1. CORRECT SENTENCE: If the sentence has no errors, return:
   - is_correct: true
   - errors: [] (empty array, never omit this field)
   - corrected_sentence: the original sentence EXACTLY as written (character for character)

2. ERRORS: For each error found:
   - original: the exact erroneous span from the input sentence
   - correction: the corrected form of that span only
   - error_type: MUST be one of these exact strings:
     grammar | spelling | word_choice | punctuation | word_order | missing_word |
     extra_word | conjugation | gender_agreement | number_agreement | tone_register | other
   - explanation: 1-2 friendly sentences written in the learner's NATIVE language
     (not the target language). Be specific about what went wrong and why.

3. CORRECTIONS: Make the MINIMUM edits needed. Preserve the learner's vocabulary,
   voice, and sentence structure wherever possible. Do not rephrase or improve
   style — only fix genuine errors.

4. DIFFICULTY: Assign CEFR level based on the grammatical structures and
   vocabulary in the ORIGINAL sentence — not whether it has errors.
   A1=beginner, A2=elementary, B1=intermediate, B2=upper-intermediate,
   C1=advanced, C2=mastery.

5. NON-LATIN SCRIPTS: Handle all writing systems correctly. Do not transliterate.
   Return all text in the original script.

6. OUTPUT: Return ONLY a valid JSON object. No markdown fences, no preamble,
   no explanation outside the JSON. The response must start with {{ and end with }}.

JSON schema (follow exactly):
{{
  "corrected_sentence": "string",
  "is_correct": boolean,
  "errors": [
    {{
      "original": "string",
      "correction": "string",
      "error_type": "string",
      "explanation": "string"
    }}
  ],
  "difficulty": "A1|A2|B1|B2|C1|C2"
}}
"""

VALID_ERROR_TYPES = {
    "grammar", "spelling", "word_choice", "punctuation", "word_order",
    "missing_word", "extra_word", "conjugation", "gender_agreement",
    "number_agreement", "tone_register", "other",
}
VALID_DIFFICULTIES = {"A1", "A2", "B1", "B2", "C1", "C2"}

_client = Anthropic()


def _sanitize_response(data: dict) -> dict:
    if data.get("difficulty") not in VALID_DIFFICULTIES:
        data["difficulty"] = "B1"

    for error in data.get("errors", []):
        if error.get("error_type") not in VALID_ERROR_TYPES:
            error["error_type"] = "other"

    errors = data.get("errors") or []

    if errors:
        data["is_correct"] = False
        data["errors"] = errors
    else:
        data["is_correct"] = bool(data.get("is_correct", False))
        data["errors"] = []

    return data


@lru_cache(maxsize=512)
def _cached_call(sentence: str, target_language: str, native_language: str) -> str:
    user_message = (
        f"Target language: {target_language}\n"
        f"Native language: {native_language}\n"
        f"Sentence: {sentence}"
    )

    last_exc: Exception | None = None

    for attempt in range(3):
        try:
            response = _client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            )

            raw = response.content[0].text.strip()
            raw = re.sub(
                r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE
            ).strip()
            json.loads(raw)
            return raw

        except json.JSONDecodeError as exc:
            last_exc = exc
            continue

    raise ValueError("LLM returned invalid JSON after 3 attempts") from last_exc


def get_feedback(request: FeedbackRequest) -> FeedbackResponse:
    raw = _cached_call(
        request.sentence,
        request.target_language,
        request.native_language,
    )
    data = json.loads(raw)
    data = _sanitize_response(data)
    return FeedbackResponse(**data)