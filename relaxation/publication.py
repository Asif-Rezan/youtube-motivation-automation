"""Explicit full-episode publication with durable platform IDs and guarded cleanup."""
import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from storage import Store
from pipeline import publish, youtube_client, pipeline_failure_message
from facebook_publish import Facebook, publish as facebook_publish, verify_remote


def validate(plan, metadata):
    if plan.get('seconds') != 10800 or len(plan.get('scenes', [])) != 100:
        raise ValueError('Only the full three-hour episode may be published')
    if metadata != plan['youtube'] or plan.get('nature_backend') != 'field_recording':
        raise ValueError('Metadata or licensed rain source mismatch')
    if 'alex36917' not in metadata['snippet']['description'] or plan['chapters'] not in metadata['snippet']['description']:
        raise ValueError('Rain attribution and chapters are required')


def run(stage, episode, root):
    if not re.fullmatch(r'[0-9]+', episode):
        raise ValueError('Expected original GitHub run ID')
    for name in ('DRIVE_TOKEN_JSON', 'DRIVE_FOLDER_ID', 'YOUTUBE_TOKEN_JSON', 'EXPECTED_CHANNEL_ID', 'FACEBOOK_PAGE_ACCESS_TOKEN'):
        if not os.getenv(name):
            raise ValueError('Missing publication configuration: '+name)
    store=Store(); client=youtube_client(); fb=Facebook(os.environ['FACEBOOK_PAGE_ACCESS_TOKEN'])
    fb.verify_page()
    run_id='relaxation-'+episode; key=f'runs/{run_id}/state.json'
    state=store.load(key,{})
    def save(): store.save(key,state)
    if stage=='preflight':
        channels=client.channels().list(part='status',mine=True).execute(num_retries=3).get('items',[])
        if len(channels)!=1 or channels[0].get('status',{}).get('longUploadsStatus') in ('disallowed','eligible'):
            raise RuntimeError('YouTube account must enable long video uploads before a three-hour run')
        if state.get('upload_started') and not state.get('video_id'):
            raise RuntimeError('Ambiguous upload must be reconciled before retry')
        print('YouTube channel, Facebook Page and Drive credentials verified',flush=True)
        return
    if stage=='youtube':
        plan=json.loads((root/'plan.json').read_text()); metadata=json.loads((root/'metadata.json').read_text())
        validate(plan,metadata)
        if plan != store.load(f'relaxation/production-drafts/{episode}/plan.json',None):
            raise ValueError('AI checkpoint differs from local plan')
        if state.get('phase')=='published': return state['video_id']
        if state.get('upload_started') and not state.get('video_id'):
            raise RuntimeError('Ambiguous upload must be reconciled before retry')
        source=root/'relaxation-3-hours.mp4'
        probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(source)]))
        video=next(s for s in probe['streams'] if s['codec_type']=='video')
        if abs(float(probe['format']['duration'])-10800)>.1 or (video['width'],video['height'])!=(1280,720):
            raise ValueError('Full video validation failed')
        from PIL import Image
        with Image.open(root/'thumbnail.jpg') as image:
            if image.size!=(1920,1080) or (root/'thumbnail.jpg').stat().st_size>=2000000:
                raise ValueError('Thumbnail validation failed')
        target=root/'video.mp4'
        if not target.exists(): os.link(source,target)
        if not state.get('video_id'):
            state.update(relaxation=True,song=metadata['snippet']);save()
            for name in ('video.mp4','thumbnail.jpg'): store.upload(root/name,f'runs/{run_id}/{name}')
        publish(client,root,metadata['snippet'],state,save,metadata_override=metadata['snippet'])
        return state['video_id']
    if state.get('phase')!='published': raise RuntimeError('Verified public YouTube publication required')
    fb_key=f'facebook/{run_id}/video/state.json'; receipt=store.load(fb_key,{})
    if stage=='facebook':
        root.mkdir(parents=True,exist_ok=True)
        file_id=store.find(f'runs/{run_id}/video.mp4')
        if not file_id: raise RuntimeError('Drive backup missing; refusing publication')
        store.download(file_id,root/'video.mp4')
        snippet=state['upload_body']['snippet']
        facebook_publish(fb,root/'video.mp4','video',dict(title=snippet['title'],description=snippet['description']),None,receipt,lambda:store.save(fb_key,receipt),attempts=240)
        state.update(facebook_verified=True,facebook_video_id=receipt['video_id']);save()
        return receipt['video_id']
    if not receipt.get('video_id') or not verify_remote(fb.status(receipt['video_id']),receipt):
        raise RuntimeError('Fresh Facebook publication verification failed; Drive media retained')
    from cleanup_drive import cleanup
    cleanup(store,client,run_id,state)
    return 'Verified publication; Drive temporary media cleaned'

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['preflight','youtube','facebook','cleanup']);parser.add_argument('--episode',required=True);parser.add_argument('--root',type=Path,default=Path('output/relaxation-production'));args=parser.parse_args()
    try: print(run(args.stage,args.episode,args.root))
    except Exception as error:
        print(pipeline_failure_message(error));raise SystemExit(1)
