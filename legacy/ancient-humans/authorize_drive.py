"""Run on your own computer: Drive consent, GitHub secret update, optional test."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

REPO = 'Asif-Rezan/youtube-motivation-automation'
SCOPES = ['https://www.googleapis.com/auth/drive.file']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--client', type=Path, default=Path('client_secrets.json'))
    parser.add_argument('--folder', required=True, help='Existing private workflow folder ID')
    parser.add_argument('--run-test', action='store_true', help='Dispatch one daily-pipeline test after saving the secret')
    args = parser.parse_args()
    if not args.client.is_file():
        parser.error('Download your Desktop app OAuth client JSON from Google Cloud and save it as client_secrets.json')
    config = json.loads(args.client.read_text())
    if 'installed' not in config:
        parser.error('Use a Desktop app OAuth client, not a Web application client')
    if not shutil.which('gh'):
        parser.error('Install GitHub CLI (macOS: brew install gh), then run gh auth login')
    subprocess.run(['gh', 'auth', 'status'], check=True, capture_output=True)
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    flow = InstalledAppFlow.from_client_config(config, SCOPES, autogenerate_code_verifier=True)
    credentials = flow.run_local_server(host='127.0.0.1', port=0, prompt='consent',
        access_type='offline', authorization_prompt_message='Approve Drive access in the browser that opens.',
        success_message='Authorization received. You can close this tab.', timeout_seconds=300)
    if not credentials.refresh_token:
        raise RuntimeError('No refresh token returned; GitHub secret was not changed')
    if not set(SCOPES).issubset(set(credentials.granted_scopes or credentials.scopes or [])):
        raise RuntimeError('Required scopes were not approved; GitHub secret was not changed')
    # Read-only validation before replacing the secret. Use the original client so
    # existing drive.file checkpoints remain accessible to this application.
    from google.auth.transport.requests import Request
    credentials.refresh(Request())
    drive = build('drive', 'v3', credentials=credentials, cache_discovery=False)
    drive.about().get(fields='storageQuota').execute()
    folder = args.folder
    if not folder:
        parser.error('Pass --folder with the existing private workflow folder ID; secret was not changed')
    info = drive.files().get(fileId=folder, fields='mimeType,trashed,capabilities(canAddChildren)').execute()
    permissions = drive.permissions().list(fileId=folder, fields='permissions(role,type)').execute().get('permissions', [])
    if (info.get('mimeType') != 'application/vnd.google-apps.folder' or info.get('trashed')
        or not info.get('capabilities', {}).get('canAddChildren')
        or not permissions or any(p.get('role') != 'owner' for p in permissions)):
        raise RuntimeError('Existing folder must be writable and owner-only; secret was not changed')
    # Tokens go directly to GitHub CLI stdin, never stdout, command arguments, or disk.
    subprocess.run(['gh', 'secret', 'set', 'DRIVE_TOKEN_JSON', '--repo', REPO],
        input=credentials.to_json(), text=True, check=True, capture_output=True)
    print('Drive authorization and existing folder verified and DRIVE_TOKEN_JSON updated securely.')
    if args.run_test:
        subprocess.run(['gh', 'workflow', 'run', 'daily-upload.yml', '--ref', 'main', '--repo', REPO],
            check=True, capture_output=True)
        print('One test run requested. Daily 01:00 Asia/Dhaka schedule is unchanged.')
    print('View progress: https://github.com/' + REPO + '/actions/workflows/daily-upload.yml')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # OAuth exceptions may contain callback URLs; never print raw responses.
        print('Authorization/setup failed: ' + type(error).__name__ +
              '. Check the original Drive OAuth client and existing folder, client file, Google consent and gh auth login. No tokens were printed.')
        raise SystemExit(1)
