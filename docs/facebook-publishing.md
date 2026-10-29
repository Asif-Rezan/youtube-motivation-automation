# Facebook Page publishing

Destination: [Rezan Relaxation](https://www.facebook.com/rezan.relaxation/), Page ID `297892583408910` (confirmed in the Page's management links). Existing YouTube and Drive credentials remain unchanged.

## One-time authorization

1. Register for Meta for Developers using the Page administrator's personal account. The user must accept Meta's terms and complete any account/email/phone verification themselves when required.
2. Create `Rezan Video Automation` with the **Manage everything on your Page** use case and the matching `rezan_relaxation` business portfolio.
3. Authorize only the required Page with `pages_show_list`, `pages_read_engagement`, and `pages_manage_posts`. The authorizing person must be able to perform CREATE_CONTENT. Confirm current standard/advanced access and review requirements in the dashboard for the actual app/account; app creation alone is not publication authorization.
4. Obtain a Page access token, not a personal profile token. Validate `/me?fields=id,name` returns `297892583408910`. Store it only as repository Actions secret `FACEBOOK_PAGE_ACCESS_TOKEN`. Never commit it, put it in a variable, paste it into chat, or print it in logs. Record any token expiry/data-access expiry and renew authorization before expiry. Do not assume a token is permanent.
5. Run a controlled publication using existing episode artifacts and inspect Page identity, processing and the scheduled release. Set repository variable `FACEBOOK_PUBLISH_ENABLED=true` only after authorization is ready.

Meta registration and authorization are interactive prerequisites. Until they finish, Facebook live publishing is not configured. The code must not report successful cross-posting merely because YouTube succeeded.

## Behavior

The original landscape MP4 is a Page video; the 40-second portrait Short is a Facebook Reel. No new models or media generation. Facebook uses the same frozen publication target saved in the YouTube checkpoint. Scheduled Page content becomes public at release; this is not personal-profile posting. The Reel is explicitly disclosed as AI-generated; Page video descriptions disclose AI-generated music and illustrations.

The Facebook jobs use the existing private Drive store for `facebook/SONG_RUN_ID/video/state.json` and `facebook/SONG_RUN_ID/short/state.json`. Keys are separate from YouTube checkpoints. A file hash, Page ID, media type, metadata, schedule and returned video/session IDs are frozen before publication. Retrying reads the same ID; an initialization with a lost response stops for reconciliation rather than creating a duplicate. API error messages show only HTTP/error codes, not response bodies, URLs or tokens.

A publishing failure can be resumed through **Publish existing episode to Facebook** without restarting models or writing to YouTube. Select `kind=video` and the original generation `source_run`, or `kind=short` and the run containing its `rhyme-short` artifact. The original song `run_id` must match. This recovery currently supports the default 0–40 second Short. Artifacts expire after seven days. Preserve or restore artifacts before retrying older episodes.

Facebook scheduling is constrained to over ten minutes and under 29 days in this integration (the stricter Reel window). Expired schedules require deliberate reconciliation; retries never silently publish early or postpone an existing scheduled item. Automatic long-video cleanup waits for long/Short jobs, including enabled Facebook steps. Scheduled media is retained by the existing cleanup rules. Facebook is disabled independently of YouTube until `FACEBOOK_PUBLISH_ENABLED=true`.

## Verification and limits

Run `python -m unittest -v` and `actionlint -shellcheck= -pyflakes=`. Mocked tests cover Page identity, schedule windows, AI disclosure, per-chunk transfer, retry ID reuse, response-loss duplicate prevention, invalid upload hosts and credential-safe diagnostics. These do not prove actual Meta account eligibility, token permissions, upload acceptance or schedule readback; those require the authorized live test.

Official API references used:

- [Page video upload and schedule parameters](https://developers.facebook.com/docs/graph-api/reference/page/videos/)
- [Video API publishing requirements](https://developers.facebook.com/documentation/video-api/guides/publishing)
- [Reel publishing and schedule parameters](https://developers.facebook.com/documentation/video-api/guides/reels-publishing)

The implementation uses Graph API `v26.0`, as shown in Meta's current reference when this integration was prepared. Review Meta's API-version lifecycle before upgrading.
