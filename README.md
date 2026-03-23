## Design Decisions

### Model Choice: claude-haiku-4-5

I chose `claude-haiku-4-5-20251001` over larger models for three reasons:

1. **Speed**: Haiku consistently responds in 2–5 seconds, well under the 30-second limit
2. **Cost**: At ~$0.001 per request vs ~$0.015 for Opus, it's 15x cheaper at scale.
3. **Quality**: For structured grammar correction, a well-scoped task with a tight prompt,  Haiku performs on par with larger models. We don't need Sonnet/Opus as we're not doing heavy research or programming. 

### Prompt Strategy

The system prompt enforces four things explicitly:

- **JSON-only output**: instructs the model to return nothing outside the JSON object, and strips markdown fences as a fallback
- **Errors list as ground truth**: the prompt defines `errors` as the signal, if errors exist, the sentence is not correct
- **Native language explanations**: the prompt specifies that all explanations must be written in the learner's native language, not the target language
- **Non-Latin script handling**: explicitly instructs the model not to transliterate and to return all text in the original script (tested against Japanese, Russian, Korean)

### Reliability

- **3-attempt retry loop**: if the model returns malformed JSON, the call is retried up to 3 times before raising
- **`_sanitize_response`**: post-parse enforcement of all schema invariants — invalid `error_type` values are clamped to `other`, invalid `difficulty` values default to `B1`, and the `errors`/`is_correct` relationship is enforced with errors as the source of truth
- **Two layers of type validation**: `_sanitize_response` catches issues before Pydantic sees the data; `Literal` types in the models catch anything that slips through

### Caching

`@lru_cache(maxsize=512)` on the internal API call function means identical requests never hit the API twice within a running process. For this scope it eliminates redundant calls and keeps costs down.

### Verifying Accuracy for Unknown Languages

I don't speak most of these languages. To verify correctness for these languages I used two approaches: back-translation (feeding the corrected sentence back through the API asking for English translation) and cross-checking a sample of outputs against Google Translate. The results were consistent with expected corrections.