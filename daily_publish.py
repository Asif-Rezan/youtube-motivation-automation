"""Verify an existing private upload; permanently clean only tagged run media."""
from reliability import api_execute
import hashlib
import json
import re
import time


def disposable(name):
    return name in {'plan.json', 'narration.wav', 'captions.srt', 'video.mp4',
        'thumbnail.jpg', 'music.audio', 'thumbnail-source.png'} or bool(
        re.fullmatch(r'shot-\d+\.(png|mp4|qa\.json)', name))


def validate_remote(video, state, channel):
    if video.get('id') != state.get('video_id'):
        raise RuntimeError('Video identity mismatch')
    snippet, status = video['snippet'], video['status']
    story = state['story']
    if (snippet['channelId'] != channel or snippet['title'] != story['title']
        or set(snippet.get('tags', [])) != set(story['tags'])
        or snippet['description'] != state.get('upload_description', story['description'])):
        raise RuntimeError('Channel or metadata mismatch')
    if state.get('video_details_version') == 1:
        expected = {'defaultAudioLanguage': 'en-US', 'defaultLanguage': 'en-US',
                    'containsSyntheticMedia': True, 'hasPaidProductPlacement': False}
        actual = {k: snippet.get(k) for k in ('defaultAudioLanguage', 'defaultLanguage')}
        actual['containsSyntheticMedia'] = status.get('containsSyntheticMedia')
        receipt = state.get('ai_disclosure_verification', {})
        if ('containsSyntheticMedia' not in status and receipt.get('video_id') == video['id']
            and receipt.get('value') is True and receipt.get('method') == 'videos.update-response'):
            actual['containsSyntheticMedia'] = True
        # YouTube may omit a false paid-placement value. Its documented default is false.
        actual['hasPaidProductPlacement'] = video.get('paidProductPlacementDetails', {}).get(
            'hasPaidProductPlacement', False)
        mismatches = {k: {'expected': value, 'actual': actual[k]}
                      for k, value in expected.items() if actual[k] != value}
        if mismatches:
            raise RuntimeError('Video details mismatch: ' + json.dumps(mismatches, sort_keys=True))
    if (status.get('uploadStatus') in ('failed', 'rejected', 'deleted')
        or video.get('processingDetails', {}).get('processingStatus') in ('failed', 'terminated')):
        raise RuntimeError('YouTube upload failed')
    return (status.get('uploadStatus') == 'processed'
        and video.get('processingDetails', {}).get('processingStatus') == 'succeeded'
        and video.get('contentDetails', {}).get('definition') == 'hd')


def ensure_ai_disclosure(client, video, state, channel):
    """Insert can omit the AI flag; explicitly update and read it back before publishing."""
    if state.get('video_details_version') != 1:
        return video
    # Verify identity and exact story metadata before any mutation.
    validate_remote(video, dict(state, video_details_version=None), channel)
    status = video['status']
    if status.get('containsSyntheticMedia') is True:
        return video
    if status.get('privacyStatus') != 'private':
        raise RuntimeError('AI disclosure repair requires a private video')
    writable = {k: status[k] for k in ('privacyStatus', 'publishAt', 'embeddable',
        'license', 'publicStatsViewable', 'selfDeclaredMadeForKids') if k in status}
    writable['containsSyntheticMedia'] = True
    result = api_execute(client.videos().update(part='status', body={'id': video['id'], 'status': writable}))
    print(json.dumps({'check': 'AI disclosure update', 'video_id': video['id'],
        'returned_ai_disclosure': result.get('status', {}).get('containsSyntheticMedia')}), flush=True)
    if result.get('id') == video['id'] and result.get('status', {}).get('containsSyntheticMedia') is True:
        state['ai_disclosure_verification'] = {'video_id': video['id'], 'value': True,
            'method': 'videos.update-response'}
    for attempt in range(6):
        items = api_execute(client.videos().list(part='snippet,status,processingDetails,contentDetails,paidProductPlacementDetails',
            id=video['id'])).get('items', [])
        if not items:
            raise RuntimeError('Video unavailable after AI disclosure update')
        if items[0]['status'].get('containsSyntheticMedia') is True:
            return items[0]
        if ('containsSyntheticMedia' not in items[0]['status']
            and state.get('ai_disclosure_verification', {}).get('video_id') == video['id']):
            validate_remote(items[0], state, channel)
            return items[0]
        if attempt < 5:
            time.sleep(10)
    raise RuntimeError('YouTube accepted AI disclosure update but did not confirm it after 50 seconds')


def cleanup(store, run, state):
    if not re.fullmatch(r'daily-\d+', run):
        raise ValueError('Invalid daily run ID')
    proof = state.get('verification', {})
    if (state.get('phase') != 'verified_private' or proof.get('video_id') != state.get('video_id')
        or not all(proof.get(k) is True for k in ('hd', 'metadata', 'processed', 'private'))):
        raise RuntimeError('Verified private upload required before deletion')
    key = f'runs/{run}/cleanup.json'
    journal = store.load(key, None)
    if journal is None:
        files, token = [], None
        while True:
            result = api_execute(store.client.files().list(q=f"'{store.folder}' in parents and trashed = false and "
                f"appProperties has {{ key='automation_run' and value='{run}' }} and "
                "appProperties has { key='disposable' and value='v1' }",
                fields='nextPageToken,files(id,name,appProperties,parents,mimeType)',
                pageSize=1000, pageToken=token))
            files.extend(result.get('files', []))
            token = result.get('nextPageToken')
            if not token:
                break
        journal = {'run': run, 'video_id': state['video_id'], 'files': files, 'deleted': []}
        store.save(key, journal)  # Durable ID manifest before any destructive operation.
    if journal['run'] != run or journal['video_id'] != state['video_id']:
        raise RuntimeError('Cleanup journal identity mismatch')
    for entry in journal['files']:
        fid = entry['id']
        if fid in journal['deleted']:
            continue
        for attempt in range(4):
            try:
                remote = api_execute(store.client.files().get(fileId=fid,
                    fields='id,name,parents,appProperties,mimeType'))
                name = remote['name'].removeprefix(f'runs__{run}__')
                props = remote.get('appProperties', {})
                if (remote['name'] != f'runs__{run}__{name}' or not disposable(name)
                    or store.folder not in remote.get('parents', [])
                    or props.get('automation_run') != run or props.get('disposable') != 'v1'
                    or props.get('workflow_key') != hashlib.sha256(f'runs/{run}/{name}'.encode()).hexdigest()
                    or remote.get('mimeType') == 'application/vnd.google-apps.folder'):
                    raise ValueError('Unsafe cleanup target rejected')
                store.check_private(fid)
                store.client.files().delete(fileId=fid).execute()
                break
            except ValueError:
                raise
            except Exception as error:
                if getattr(getattr(error, 'resp', None), 'status', None) == 404:
                    break  # Previous deletion succeeded before checkpoint was saved.
                if attempt == 3:
                    raise
                time.sleep(2 ** attempt)
        journal['deleted'].append(fid)
        if len(journal['deleted']) % 10 == 0:
            store.save(key, journal)
            print(json.dumps({'check': 'Drive cleanup', 'deleted': len(journal['deleted']),
                'total': len(journal['files'])}), flush=True)
    journal['complete'] = True
    store.save(key, journal)


def main():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from workflow import Store, required
    run = required('SAVED_RUN_ID')
    if not re.fullmatch(r'daily-\d+', run):
        raise ValueError('Only daily run IDs are accepted')
    store = Store()
    key = f'runs/{run}/state.json'
    state = store.load(key, {})
    if state.get('phase') not in ('uploaded', 'complete', 'verified_private') or not state.get('video_id'):
        raise RuntimeError('No successful upload to verify; no cleanup allowed')
    client = build('youtube', 'v3', credentials=Credentials.from_authorized_user_info(
        json.loads(required('YOUTUBE_TOKEN_JSON'))), cache_discovery=False)
    if state.get('thumbnail_uploaded') is not True:
        # The insert already succeeded: recover its thumbnail without inserting again.
        import tempfile
        from pathlib import Path
        from workflow import finalize_uploaded
        thumbnail_id = store.find(f'runs/{run}/thumbnail.jpg')
        if not thumbnail_id:
            raise RuntimeError('Saved thumbnail unavailable; preserve uploaded video and media')
        with tempfile.TemporaryDirectory(prefix='known-upload-') as directory:
            thumbnail = Path(directory)/'thumbnail.jpg'
            store.download(thumbnail_id, thumbnail)
            finalize_uploaded(client, thumbnail, state['story'], state, store, key)
    deadline = time.monotonic() + 1800
    while True:
        items = api_execute(client.videos().list(part='snippet,status,processingDetails,contentDetails,paidProductPlacementDetails',
            id=state['video_id'])).get('items', [])
        if not items:
            raise RuntimeError('Uploaded video unavailable')
        video = ensure_ai_disclosure(client, items[0], state, required('EXPECTED_CHANNEL_ID'))
        if validate_remote(video, state, required('EXPECTED_CHANNEL_ID')):
            break
        if time.monotonic() >= deadline:
            raise RuntimeError('HD processing pending; preserve all media')
        time.sleep(20)
    if video['status']['privacyStatus'] != 'private':
        raise RuntimeError('Video must remain private; preserve all media')
    state.update(phase='verified_private', verification={'video_id': state['video_id'],
        'hd': True, 'processed': True, 'metadata': True, 'private': True})
    store.save(key, state)
    history = store.load('history.json', [])
    if not any(h.get('run') == run for h in history):
        history.append({'run': run, 'video_id': state['video_id'], 'title': state['story']['title'], 'format': state['story'].get('format'), 'hash': state['hash']})
    store.save('history.json', history)
    from publish_schedule import schedule_verified
    schedule_verified(client, state, store, key)
    cleanup(store, run, state)
    print(json.dumps({'run': run, 'video_id': state['video_id'], 'privacy': 'private', 'verified': True, 'cleanup_complete': True, 'publish_at': state.get('publish_at')}))


if __name__ == '__main__':
    main()
