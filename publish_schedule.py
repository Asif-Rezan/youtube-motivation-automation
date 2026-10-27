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
    if status.get('publishAt') != target:
        if datetime.fromisoformat(target.replace('Z', '+00:00')) <= datetime.now(timezone.utc):
            raise RuntimeError('Saved publication time has passed; manual reconciliation required')
        writable = {k: status[k] for k in ('embeddable', 'license', 'publicStatsViewable',
                    'selfDeclaredMadeForKids', 'containsSyntheticMedia') if k in status}
        writable.update(privacyStatus='private', publishAt=target)
        client.videos().update(part='status', body={'id': state['video_id'], 'status': writable}).execute()
    remote = client.videos().list(part='status', id=state['video_id']).execute()['items'][0]['status']
    if remote.get('publishAt') != target or remote.get('privacyStatus') != 'private':
        raise RuntimeError('Publication schedule verification failed')
    state['schedule_verified'] = True
    store.save(key, state)
