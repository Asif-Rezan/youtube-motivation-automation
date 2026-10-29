# Pipeline recovery

Temporary network timeouts, connection resets, rate limits and Google 5xx errors
receive bounded retries with backoff. Private Drive reads, transfers, thumbnail
updates, AI disclosure, scheduling and processing checks use this handling.
Permission denial, expired/revoked credentials, exhausted daily quota, disk-full,
unsafe content and invalid metadata are not treated as transient network faults.

The daily workflow supports `resume_run=daily-NUMBER` for an unuploaded run, using
its exact checkpoint identity with the latest code. Use `cleanup_run` for a known
uploaded video instead. Published/ambiguous upload states are never regenerated.

Script generation saves the outline and each completed narration batch privately
under its original run. Metadata formatting and length recovery stays within the
1000–2000-character description contract. A transient stage retry resumes valid
storyboard batches whose narration, character and model signature still match.
Audio, downloaded assets and local text/JSON checkpoints are replaced atomically.
Invalid cached caption JSON is regenerated from the existing narration audio.

Image jobs save complete QA-passed shots even when a later shot fails. Rerunning
the failed job, or the selected-shard recovery workflow, restores matching cached
shots for that shard. Stale, missing or failed-QA images are regenerated. Model
workers continue running without Google credentials; only restore/save steps
receive them. A hard runner termination can still prevent the final save step.

Resumable upload chunks keep their existing retry budget. Once the video ID is
known, retrying the upload stage finalizes that same video after checking channel,
metadata, story hash and private visibility. It does not insert another video.
The cleanup-only daily workflow can restore a saved thumbnail and finish an
already-known upload before HD verification, scheduling and scoped media cleanup.
History writes are idempotent per run.

Never automatically repeat an ambiguous videos.insert. If the response and video
ID were lost, reconciliation is required to avoid duplicates. Generic API retries
explicitly reject video and Drive insertion requests. New Drive file creation
keeps its existing preallocated-ID reconciliation logic. Cleanup cannot delete
media before the required verification checks pass.

Retries cannot make every failure disappear. Missing permissions, unavailable
models, native crashes, GitHub runner limits, sustained outages, failed quality
checks and ambiguous uploads may still require intervention. Recovery preserves
verified work where possible; it never substitutes a different AI model, silently
publishes failed content or runs unlimited retry loops.
