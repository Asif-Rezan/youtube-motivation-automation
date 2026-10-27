"""Schedule verified daily uploads using a durable upload-completion timestamp."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


def first_publish_time(uploaded_at):
    uploaded = datetime.fromisoformat(uploaded_at.replace('Z', '+00:00'))
    if uploaded.tzinfo is None:
        raise ValueError('Upload completion timestamp must include timezone')
    earliest = uploaded.astimezone(timezone.utc) + timedelta(hours=24)
    eastern = ZoneInfo('America/New_York')
    candidate = earliest.astimezone(eastern).replace(hour=6, minute=0, second=0, microsecond=0)
    if candidate.astimezone(timezone.utc) < earliest:
        candidate += timedelta(days=1)
    return candidate.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def same_instant(left, right):
    if not left or not right:
        return False
    return datetime.fromisoformat(left.replace('Z', '+00:00')) == datetime.fromisoformat(right.replace('Z', '+00:00'))


def schedule_verified(client, state, store, key):
    if not state.get('schedule_requested'):
        return
    target = state.get('publish_at') or first_publish_time(state['uploaded_at'])
    state['publish_at'] = target
    store.save(key, state)  # Keep the same target on retries, including ambiguous responses.
    items = client.videos().list(part='status', id=state['video_id']).execute().get('items', [])
    if not items or items[0]['status']['privacyStatus'] != 'private':
        raise RuntimeError('Only a verified private video can be scheduled')
    status = items[0]['status']
    receipt = state.get('schedule_update_receipt', {})
    receipt_valid = (receipt.get('video_id') == state['video_id']
        and same_instant(receipt.get('publish_at'), target) and receipt.get('privacy') == 'private')
    if not same_instant(status.get('publishAt'), target) and not (receipt_valid and 'publishAt' not in status):
        if datetime.fromisoformat(target.replace('Z', '+00:00')) <= datetime.now(timezone.utc):
            raise RuntimeError('Saved publication time has passed; manual reconciliation required')
        writable = {k: status[k] for k in ('embeddable', 'license', 'publicStatsViewable',
                    'selfDeclaredMadeForKids', 'containsSyntheticMedia') if k in status}
        writable.update(privacyStatus='private', publishAt=target)
        writable['containsSyntheticMedia'] = True
        result = client.videos().update(part='status', body={'id': state['video_id'], 'status': writable}).execute()
        confirmed = result.get('status', {})
        if (result.get('id') == state['video_id'] and confirmed.get('privacyStatus') == 'private'
            and same_instant(confirmed.get('publishAt'), target)):
            state['schedule_update_receipt'] = {'video_id': state['video_id'],
                'publish_at': confirmed['publishAt'], 'privacy': 'private'}
            store.save(key, state)
    remote = client.videos().list(part='status', id=state['video_id']).execute()['items'][0]['status']
    receipt = state.get('schedule_update_receipt', {})
    confirmed_by_update = (receipt.get('video_id') == state['video_id']
        and same_instant(receipt.get('publish_at'), target) and receipt.get('privacy') == 'private')
    if (remote.get('privacyStatus') != 'private' or
        not (same_instant(remote.get('publishAt'), target) or
             ('publishAt' not in remote and confirmed_by_update))):
        raise RuntimeError(f'Publication schedule verification failed: expected={target}, '
            f'actual={remote.get("publishAt")}, privacy={remote.get("privacyStatus")}')
    state['schedule_verified'] = True
    store.save(key, state)
