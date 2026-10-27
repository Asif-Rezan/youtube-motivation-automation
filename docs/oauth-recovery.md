# Recover rejected Google refresh tokens

`invalid_grant` means Google rejected the refresh token. Retrying the same
secret cannot repair an expired or revoked grant. Do not skip the Drive check:
all image workers depend on private Drive checkpoints.

1. In the Google Cloud project owning the **original Drive OAuth client**, check
   Google Auth Platform > Audience. External apps in Testing issue refresh tokens
   that expire after seven days for Drive scopes. Switch to Production before
   creating the replacement token, following any Google verification requirements.
   Production removes this Testing limit, but tokens can still be revoked.
2. Download that same Desktop OAuth client as `client_secrets.json` locally.
   Keep the same Google account and OAuth client: `drive.file` access belongs to
   the application and changing the client can hide existing checkpoints.
3. On your computer, install `google-auth-oauthlib` and `google-api-python-client`,
   install GitHub CLI, and run `gh auth login`.
4. Run `python authorize_drive.py --client client_secrets.json --folder EXISTING_FOLDER_ID`.
   Use the existing workflow folder ID from your Drive/Actions configuration.
   The helper verifies access and owner-only permissions before replacing
   `DRIVE_TOKEN_JSON` through GitHub CLI stdin. It never prints or saves tokens.
5. Run **Google OAuth check** in Actions. Both Google authorization checks must pass. Then start **Daily financial storytelling publishing** with
   `cleanup_run` blank. Alternatively add `--run-test` to the helper to request
   one fresh private generation after saving the validated token.

Text is generated locally by Qwen; external text credentials are not required.
Scheduled publication and explicit AI-disclosure updates now require a publish scope.
For `publish_scope_missing` or HTTP 403 insufficient authentication scopes, run
`python authorize_youtube.py --client client_secrets.json` locally and approve
YouTube access for the configured channel. This helper requests `youtube.upload`
and `youtube.force-ssl`, verifies the channel, and securely replaces
`YOUTUBE_TOKEN_JSON` in GitHub. Then retry the failed daily run using `cleanup_run`
before requesting a fresh generation. Upload-only authorization cannot schedule videos. The configured destination remains Rezan Relaxation.

Google reference: https://developers.google.com/identity/protocols/oauth2#expiration
