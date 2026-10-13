"""10–15 minute videos with a distinct illustrated image every ten seconds."""
import bisect
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import sys
from zoneinfo import ZoneInfo
import workflow as w

ROOT = Path(os.getenv('OUTPUT_DIR', 'output/ghibli-long-test'))
INTERVAL = 10
SHARDS = 6
ASSETS = ('story.json', 'plan.json', 'narration.wav', 'captions.srt')


def run_id():
    return os.getenv('SAVED_RUN_ID') or (dt.datetime.now(ZoneInfo('Asia/Dhaka')).date().isoformat()+'-ghibli-long-test')


def shot_plan(story, lengths):
    total = sum(lengths)
    ends, acc = [], 0
    for length in lengths:
        acc += length
        ends.append(acc)
    shots = []
    for index in range(math.ceil(total/INTERVAL)):
        start = index*INTERVAL
        chapter = min(bisect.bisect_right(ends, start), len(lengths)-1)
        offset = 0 if chapter == 0 else ends[chapter-1]
        scene = story['scenes'][chapter]
        beats = scene.get('image_prompts') or [scene['image_prompt']]
        local = int((start-offset)//INTERVAL)
        beat = beats[min(local, len(beats)-1)]
        # Vary framing even when a chapter runs longer than its provided beats.
        camera = ('wide establishing composition', 'medium character view',
                  'intimate detail composition', 'over-the-shoulder composition')[index%4]
        prompt = beat+', '+camera
        shots.append({'index': index, 'start': start, 'duration': min(INTERVAL, total-start),
            'chapter': chapter, 'prompt': prompt, 'seed': 1700+index})
    return {'duration_seconds': total, 'image_interval_seconds': INTERVAL,
        'style': 'ghibli-inspired', 'shots': shots}


def prepare(story=None, root=ROOT):
    root.mkdir(parents=True, exist_ok=True)
    story = story or json.loads(Path(os.getenv('STORY_FILE', str(root/'story.json'))).read_text())
    w.validate_story(story)
    (root/'story.json').write_text(json.dumps(story, indent=2))
    lengths, word_lists, audios = [], [], []
    for index, scene in enumerate(story['scenes']):
        audio = root/f'narration-{index:02}.wav'
        if not audio.exists():
            w.make_narration(scene['narration'], audio)
        length = w.duration(audio)
        words_path = root/f'words-{index:02}.json'
        if not words_path.exists():
            words_path.write_text(json.dumps(w.transcribe(audio)))
        words = json.loads(words_path.read_text())
        w.aligned_subtitles([words], [length], root/'chapter-check.srt')
        lengths.append(length)
        word_lists.append(words)
        audios.append(audio)
        print(json.dumps({'chapter': index+1, 'seconds': length, 'audio_passed': True}), flush=True)
    total = sum(lengths)
    if not 600 <= total <= 900:
        raise RuntimeError(f'Narration is {total:.1f}s, outside 600–900s; do not generate images')
    w.aligned_subtitles(word_lists, lengths, root/'captions.srt')
    (root/'audio-list.txt').write_text(''.join(f"file '{p.name}'\n" for p in audios))
    w.shell('ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(root/'audio-list.txt'),
        '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s16le', str(root/'narration.wav'))
    plan = shot_plan(story, lengths)
    (root/'plan.json').write_text(json.dumps(plan, indent=2))
    print(json.dumps({'audio_ready': True, 'seconds': total, 'images': len(plan['shots'])}), flush=True)
    return plan


def picture_clip(image, seconds, target):
    frames = max(1, round(seconds*30))
    vf = ("scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
        f"zoompan=z='min(zoom+0.0002,1.04)':d={frames}:s=1920x1080:fps=30,"
        f"fade=t=in:st=0:d=0.2,fade=t=out:st={max(0,seconds-.2)}:d=0.2,format=yuv420p")
    w.shell('ffmpeg', '-y', '-i', str(image), '-vf', vf, '-frames:v', str(frames), '-an',
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '21', '-movflags', '+faststart', str(target))


def generate_shard(shard, root=ROOT, count=SHARDS):
    plan = json.loads((root/'plan.json').read_text())
    shots = [s for s in plan['shots'] if s['index']%count == shard]
    for shot in shots:
        index = shot['index']
        image, clip = root/f'shot-{index:03}.png', root/f'shot-{index:03}.mp4'
        os.environ['IMAGE_SEED'] = str(shot['seed'])
        if not image.exists():
            w.make_image(shot['prompt'], image)
        if not clip.exists():
            picture_clip(image, shot['duration'], clip)
        print(json.dumps({'shard': shard, 'shot': index+1, 'total': len(plan['shots']), 'rendered': True}), flush=True)


def finish(root=ROOT):
    from PIL import Image, ImageDraw, ImageFont, ImageOps
    from music_cpu import generate
    plan = json.loads((root/'plan.json').read_text())
    clips = [root/f"shot-{s['index']:03}.mp4" for s in plan['shots']]
    if not all(p.exists() for p in clips):
        raise RuntimeError('Not every ten-second image clip exists')
    for shot, clip in zip(plan['shots'], clips):
        if abs(w.duration(clip)-shot['duration']) > .04:
            raise RuntimeError('Shot timing differs from the global ten-second plan')
    (root/'clips.txt').write_text(''.join(f"file '{p.name}'\n" for p in clips))
    w.shell('ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(root/'clips.txt'), '-c', 'copy', str(root/'joined.mp4'))
    if not (root/'music.audio').exists():
        generate(root/'music.audio')
    w.shell('ffmpeg', '-y', '-i', str(root/'joined.mp4'), '-i', str(root/'narration.wav'),
        '-stream_loop', '-1', '-i', str(root/'music.audio'), '-filter_complex',
        '[1:a]loudnorm=I=-16:TP=-1.5:LRA=11,asplit=2[voice][side];[2:a]volume=0.09[music];'
        '[music][side]sidechaincompress=threshold=0.02:ratio=8[duck];'
        '[voice][duck]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11[a]',
        '-vf', f"subtitles={root/'captions.srt'}:force_style='FontName=DejaVu Sans,FontSize=22,Outline=2,MarginV=35'",
        '-map', '0:v', '-map', '[a]', '-t', str(plan['duration_seconds']), '-ar', '48000',
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '21', '-c:a', 'aac', '-movflags', '+faststart', str(root/'video.mp4'))
    metadata = w.check_video(root/'video.mp4')
    story = json.loads((root/'story.json').read_text())
    os.environ['IMAGE_SEED'] = '9931'
    w.make_image(story['thumbnail_prompt'], root/'thumbnail-source.png')
    image = ImageOps.fit(Image.open(root/'thumbnail-source.png').convert('RGB'), (1280, 720))
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 75)
    draw.rectangle((0, 510, 1280, 720), fill=(17, 37, 37))
    draw.text((55, 555), story['thumbnail_text'].upper(), font=font, fill=(255, 244, 212))
    image.save(root/'thumbnail.jpg', quality=92)
    if (root/'thumbnail.jpg').stat().st_size >= 2*1024*1024:
        raise RuntimeError('Thumbnail exceeds size limit')
    report = {'render_passed': True, 'duration_seconds': float(metadata['format']['duration']),
        'width': 1920, 'height': 1080, 'images': len(clips), 'image_interval_seconds': 10,
        'style': 'ghibli-inspired', 'privacy': 'private', 'voice': 'Kokoro am_michael',
        'music': 'Magenta MusicRNN', 'timeline_verified': True}
    (root/'validation.json').write_text(json.dumps(report))
    print(json.dumps(report), flush=True)
    return report


def render_complete(story, root):
    prepare(story, root)
    generate_shard(0, root, count=1)
    return finish(root)



def init_input():
    store = w.Store()
    if not store.find('inputs/ghibli-long-story.json'):
        store.save('inputs/ghibli-long-story.json', {'awaiting_private_input': True})
    print(json.dumps({'private_input_ready': True}), flush=True)


def stage_story():
    ROOT.mkdir(parents=True, exist_ok=True)
    store = w.Store()
    file_id = store.find('inputs/ghibli-long-story.json')
    if not file_id:
        raise RuntimeError('Private story input is not configured')
    store.download(file_id, ROOT/'story.json')
    story = w.validate_story(json.loads((ROOT/'story.json').read_text()))
    print(json.dumps({'private_story_accessible': True,
        'words': sum(len(s['narration'].split()) for s in story['scenes'])}), flush=True)


def save_preparation():
    store = w.Store()
    key = f'runs/{run_id()}/state.json'
    if store.load(key, {}).get('phase') in ('upload_started', 'uploaded', 'complete'):
        raise RuntimeError('Existing upload requires reconciliation; refusing duplicate')
    for name in ASSETS:
        store.upload(ROOT/name, f'runs/{run_id()}/{name}')
    store.save(key, {'phase': 'prepared', 'story': json.loads((ROOT/'story.json').read_text())})


def restore_preparation(images_only=False):
    ROOT.mkdir(parents=True, exist_ok=True)
    store = w.Store()
    for name in (('story.json', 'plan.json') if images_only else ASSETS):
        file_id = store.find(f'runs/{run_id()}/{name}')
        if not file_id:
            raise RuntimeError('Saved preparation asset missing')
        store.download(file_id, ROOT/name)


def save_shard(shard):
    store = w.Store()
    plan = json.loads((ROOT/'plan.json').read_text())
    for shot in plan['shots']:
        if shot['index']%SHARDS == shard:
            for ext in ('png', 'mp4'):
                name = f"shot-{shot['index']:03}.{ext}"
                store.upload(ROOT/name, f'runs/{run_id()}/{name}')
    print(json.dumps({'shard': shard, 'saved_privately': True}), flush=True)


def restore_clips():
    restore_preparation()
    store = w.Store()
    for shot in json.loads((ROOT/'plan.json').read_text())['shots']:
        name = f"shot-{shot['index']:03}.mp4"
        file_id = store.find(f'runs/{run_id()}/{name}')
        if not file_id:
            raise RuntimeError('Saved ten-second clip missing')
        store.download(file_id, ROOT/name)


def upload():
    report = json.loads((ROOT/'validation.json').read_text())
    if not report.get('render_passed') or report.get('image_interval_seconds') != 10:
        raise RuntimeError('New-format render has not passed validation')
    w.check_video(ROOT/'video.mp4')
    store, key = w.Store(), f'runs/{run_id()}/state.json'
    if store.load(key, {}).get('phase') in ('upload_started', 'uploaded', 'complete'):
        raise RuntimeError('Existing upload requires reconciliation; refusing duplicate insertion')
    story = json.loads((ROOT/'story.json').read_text())
    digest = hashlib.sha256(' '.join(s['narration'] for s in story['scenes']).encode()).hexdigest()
    history = store.load('history.json', [])
    if any(h.get('hash') == digest for h in history):
        raise RuntimeError('Story was already uploaded')
    state = {'phase': 'rendered', 'story': story, 'hash': digest, 'validation': report}
    for name in ('video.mp4', 'thumbnail.jpg', 'captions.srt', 'story.json', 'plan.json', 'music.audio', 'validation.json'):
        store.upload(ROOT/name, f'runs/{run_id()}/{name}')
    store.save(key, state)
    w.upload_private(ROOT/'video.mp4', ROOT/'thumbnail.jpg', story, state, store, key,
        'Background music: original Magenta MusicRNN melody with synthesized ambient piano.')
    history.append({'title': story['title'], 'hash': digest, 'run': run_id()})
    store.save('history.json', history)
    store.save('last-private-test.json', {'passed': True, 'run': run_id(),
        'video_id': state['video_id'], 'validation': report, 'processing_status': state['processing_status']})
    print(json.dumps({'private_test_passed': True, 'video_id': state['video_id'], **report}), flush=True)


if __name__ == '__main__':
    command = sys.argv[1]
    shard = int(sys.argv[2]) if len(sys.argv)>2 else 0
    actions = {'init-input': init_input, 'stage-story': stage_story, 'prepare': prepare, 'save-preparation': save_preparation,
        'restore-images': lambda: restore_preparation(True), 'generate-shard': lambda: generate_shard(shard),
        'save-shard': lambda: save_shard(shard), 'restore-clips': restore_clips,
        'finish': finish, 'upload': upload}
    try:
        actions[command]()
    except Exception as error:
        print(json.dumps({'command': command, 'passed': False, 'error_type': type(error).__name__,
            'http_status': getattr(getattr(error, 'resp', None), 'status', None)}), flush=True)
        if command in ('prepare', 'generate-shard', 'finish'):
            raise
        raise SystemExit(1)
