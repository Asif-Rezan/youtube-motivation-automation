# Metadata JSON recovery — run 40640621158

The run completed one outline request and all four narration batches, then failed
in the final metadata request with three generic JSON validation retries. The
logs did not retain the rejected output or distinguish truncation from schema
validation, so the exact violated constraint cannot be recovered.

The code exposed a concrete failure path: the metadata schema required a
3500–4500-character description, but the native decoder intentionally strips
large length constraints. A complete short or long draft was rejected by the
transport validator before `generate_metadata` could perform its editorial
repair. The transport then repeated the request without corrective feedback.

Complete metadata drafts now reach the editorial repair loop. The final
3500–4500-character requirement remains strict. Repair prompts include the
measured character count and the completed narration, without filler or a canned
story fallback. Generic JSON retries now supply corrective feedback; truncated
responses receive a larger bounded output budget with context rechecked.
Diagnostics distinguish invalid JSON, truncation and schema constraints without
logging rejected text.

Tests cover short/long metadata through the actual transport validator, bounded
failure for persistently invalid drafts, increased truncation budgets, retry
context limits and privacy-safe diagnostics. The local-text regression workflow
now runs automatically when relevant code changes and uses the pinned real Qwen
model to generate and validate complete metadata from public synthetic context.
It needs no Google credentials and does not upload or publish videos.
