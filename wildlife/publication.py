"""Checkpoint and verify public wildlife publishing before deleting Drive media."""
import argparse
import json
import os
from pathlib import Path

from pipeline import pipeline_failure_message, publish, youtube_client
from storage import Store


def key_for(episode):
    return f'runs/wildlife-{episode}/state.json'


def next_action(store, episode):
    state = store.load(key_for(episode), {})
    if state.get('facebook_verified') and state.get('phase') == 'published':
        journal = store.load(f'runs/wildlife-{episode}/cleanup.json', {})
        return 'complete' if journal.get('complete') else 'cleanup'
    if state.get('phase') == 'published':
        return 'facebook'
    if state.get('upload_started') and not state.get('video_id'):
        raise RuntimeError('Ambiguous YouTube upload requires reconciliation')
    return 'render'


def selection(episode, manifest_path):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from .episodes import EPISODES
    from .generate import HISTORY_KEY, build

    store = Store()
    if episode == 'auto':
        history = store.load(HISTORY_KEY, [])
        for row in history:
            candidate = row['episode']
            action = next_action(store, candidate)
            if action != 'complete':
                episode = candidate
                break
        else:
            episode = 'auto-' + datetime.now(ZoneInfo('Asia/Dhaka')).date().isoformat()
    if episode not in EPISODES and not is_generated(episode):
        raise ValueError('Unknown wildlife episode')
    action = next_action(store, episode)
    if action == 'render':
        manifest = build(episode,store) if is_generated(episode) else None
        manifest_path.parent.mkdir(parents=True,exist_ok=True)
        manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
    return {'episode':episode,'next':action,'ai':is_generated(episode)}


def is_generated(episode):
    import re
    return bool(re.fullmatch(r'auto-\d{4}-\d{2}-\d{2}',episode))


def run(stage, episode, root):
    from .episodes import EPISODES
    if episode not in EPISODES and not is_generated(episode):
        raise ValueError('Unknown wildlife episode')
    store = Store()
    run_id = f'wildlife-{episode}'
    key = key_for(episode)
    state = store.load(key, {})

    def save():
        store.save(key, state)

    if stage == 'youtube':
        from .render import plan_episode, duration
        manifest = None
        if is_generated(episode):
            manifest = json.loads((root/'episode-plan.json').read_text())
            if manifest != store.load(f'wildlife/{episode}/plan.json',None):
                raise ValueError('Publication plan differs from the original AI checkpoint')
        package, _, timeline = plan_episode(episode, False, manifest)
        metadata = json.loads((root/'metadata.json').read_text())
        if metadata != package.build(timeline) or not 600 <= duration(root/'video.mp4') <= 900:
            raise ValueError('Only the validated full wildlife episode may be published')
        client = youtube_client()
        if state.get('phase') == 'published':
            return state['video_id']
        if state.get('upload_started') and not state.get('video_id'):
            raise RuntimeError('Ambiguous YouTube upload requires reconciliation')
        if not state.get('video_id'):
            state.update(wildlife=True, song=metadata)
            save()
            for name in ('video.mp4', 'thumbnail.jpg'):
                store.upload(root/name, f'runs/{run_id}/{name}')
        publish(client, root, metadata, state, save, metadata_override=metadata)
        return state['video_id']

    if stage == 'facebook':
        from facebook_publish import Facebook, publish as publish_facebook
        if state.get('phase') != 'published':
            raise RuntimeError('Public YouTube video must be verified before Facebook publication')
        if state.get('facebook_verified'):
            return state['facebook_video_id']
        fb_key = f'facebook/{run_id}/video/state.json'
        fb_state = store.load(fb_key, {})
        snippet = state['upload_body']['snippet']
        metadata = {'title': snippet['title'], 'description': snippet['description']}
        root.mkdir(parents=True, exist_ok=True)
        file_id = store.find(f'runs/{run_id}/video.mp4')
        if not file_id:
            raise RuntimeError('Verified wildlife video backup is missing')
        store.download(file_id, root/'video.mp4')
        publish_facebook(Facebook(os.getenv('FACEBOOK_PAGE_ACCESS_TOKEN')), root/'video.mp4',
                         'video', metadata, None, fb_state, lambda:store.save(fb_key, fb_state))
        state.update(facebook_verified=True, facebook_video_id=fb_state['video_id'])
        save()
        return state['facebook_video_id']

    from cleanup_drive import cleanup
    cleanup(store, youtube_client(), run_id, state)
    return state['video_id']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('select', 'youtube', 'facebook', 'cleanup'))
    parser.add_argument('--episode', default='auto')
    parser.add_argument('--manifest',type=Path,default=Path('output/wildlife-plan/plan.json'))
    parser.add_argument('--root', type=Path, default=Path('output/wildlife'))
    args = parser.parse_args()
    try:
        if args.stage == 'select':
            print(json.dumps(selection(args.episode,args.manifest)))
        else:
            print(run(args.stage, args.episode, args.root))
    except Exception as error:
        print(pipeline_failure_message(error))
        raise SystemExit(1)
