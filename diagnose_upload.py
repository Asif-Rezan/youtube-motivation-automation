"""Read-only diagnostics for a known private upload; no credentials or prose logged."""
import json
import os
import workflow as w
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from reliability import api_execute


def main():
    run = os.environ['SAVED_RUN_ID']
    state = w.Store().load(f'runs/{run}/state.json', {})
    if not state.get('video_id'):
        raise RuntimeError('No saved upload identity')
    client = build('youtube', 'v3', credentials=Credentials.from_authorized_user_info(
        json.loads(w.required('YOUTUBE_TOKEN_JSON'))), cache_discovery=False)
    items = api_execute(client.videos().list(part='snippet,status', id=state['video_id'])).get('items', [])
    if not items:
        raise RuntimeError('Saved video unavailable')
    video = items[0]
    expected = {'channelId': w.required('EXPECTED_CHANNEL_ID'), 'title': state['story']['title'],
                'description': state.get('upload_description', state['story']['description']),
                'tags': state['story']['tags']}
    report = {}
    for field, value in expected.items():
        actual = video['snippet'].get(field, [] if field == 'tags' else '')
        report[field] = {'equal': set(actual) == set(value) if field == 'tags' else actual == value,
                         'expected_length': len(value), 'actual_length': len(actual)}
        if isinstance(value, str):
            report[field]['equal_stripped'] = value.strip() == actual.strip()
            report[field]['equal_newlines'] = value.replace('\r\n', '\n') == actual.replace('\r\n', '\n')
        elif field == 'tags':
            report[field]['missing'] = sorted(set(value)-set(actual))
            report[field]['added'] = sorted(set(actual)-set(value))
    print(json.dumps({'phase': state.get('phase'), 'video_id': state['video_id'],
                      'privacy': video['status'].get('privacyStatus'), 'fields': report}), flush=True)


if __name__ == '__main__':
    main()
