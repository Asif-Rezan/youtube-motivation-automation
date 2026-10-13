"""Cloud-run daily storytelling pipeline. No public publishing path exists."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import textwrap
from zoneinfo import ZoneInfo


def required(name):
    value = os.getenv(name, '')
    if not value:
        raise RuntimeError(f'Missing configuration: {name}')
    return value


def shell(*args):
    return subprocess.check_output(args, stderr=subprocess.PIPE, text=True)


def probe(path):
    return json.loads(shell('ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(path)))


def duration(path):
    return float(probe(path)['format']['duration'])


def timestamp(seconds):
    millis = round(seconds * 1000)
    h, rest = divmod(millis, 3600000)
    m, rest = divmod(rest, 60000)
    s, ms = divmod(rest, 1000)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'


def validate_story(data):
    if not isinstance(data, dict) or not 4 <= len(data.get('scenes', [])) <= 20:
        raise ValueError('Story must contain 4–20 scenes')
    if not isinstance(data.get('title'), str) or not 1 <= len(data['title']) <= 100:
        raise ValueError('Invalid title')
    if not isinstance(data.get('description'), str) or len(data['description']) > 4500:
        raise ValueError('Invalid description')
    tags = data.get('tags', [])
    if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags) or len(','.join(tags)) > 400:
        raise ValueError('Invalid tags')
    words = 0
    for scene in data['scenes']:
        for field in ('narration', 'image_prompt'):
            if not isinstance(scene.get(field), str) or not scene[field].strip():
                raise ValueError(f'Missing scene {field}')
        words += len(scene['narration'].split())
    if not 500 <= words <= 1200:
        raise ValueError(f'Expected 500–1200 narrated words; received {words}')
    if not isinstance(data.get('thumbnail_text'), str) or len(data['thumbnail_text']) > 45:
        raise ValueError('Invalid thumbnail text')
    if not isinstance(data.get('thumbnail_prompt'), str):
        raise ValueError('Missing thumbnail prompt')
    return data


def request_groq(endpoint, payload, binary=False):
    import requests
    # Generation calls are not automatically repeated: repeats can consume credits.
    response = requests.post('https://api.groq.com/openai/v1/' + endpoint,
        headers={'Authorization': 'Bearer ' + required('GROQ_API_KEY')}, json=payload, timeout=180)
    if not response.ok:
        raise RuntimeError(f'Groq request failed with HTTP {response.status_code}')
    return response.content if binary else response.json()


def make_story(day, previous):
    prompt = f'''Write an original fictional English motivational story for {day}.
    Use a concrete protagonist, difficult choice, believable setbacks and earned resolution.
    Avoid imitating existing videos, fabricated true-story claims, or guaranteed success claims.
    650–850 spoken words, 8–12 scenes. Strong opening hook; natural narration; understated ending.
    Keep the same character appearance across all cinematic 16:9 image prompts.
    Avoid these recent titles and concepts: {previous}.
    Return JSON with title, description, tags (list), thumbnail_text (2–5 words),
    thumbnail_prompt, scenes (list of objects with narration and image_prompt).
    Description must clearly label the story fictional. No timestamps until audio is generated.'''
    result = request_groq('chat/completions', {'model': os.getenv('STORY_MODEL', 'llama-3.3-70b-versatile'),
        'messages': [{'role': 'user', 'content': prompt}], 'response_format': {'type': 'json_object'},
        'temperature': 0.9, 'max_completion_tokens': 6000})
    return validate_story(json.loads(result['choices'][0]['message']['content']))


def make_image(prompt, path):
    from huggingface_hub import InferenceClient
    image = InferenceClient(api_key=required('HF_TOKEN')).text_to_image(
        prompt=prompt + ', cinematic lighting, landscape composition, no text or watermarks',
        model=required('IMAGE_MODEL'), width=1344, height=768)
    image.save(path)


def transcribe(audio):
    import requests
    with audio.open('rb') as stream:
        response = requests.post('https://api.groq.com/openai/v1/audio/transcriptions',
            headers={'Authorization': 'Bearer ' + required('GROQ_API_KEY')},
            files={'file': (audio.name, stream, 'audio/wav')},
            data={'model': 'whisper-large-v3', 'response_format': 'verbose_json',
                  'timestamp_granularities[]': 'word', 'language': 'en'}, timeout=180)
    if not response.ok:
        raise RuntimeError(f'Transcription failed with HTTP {response.status_code}')
    words = response.json().get('words')
    if not words:
        raise RuntimeError('Transcription did not return word timings')
    return words


def aligned_subtitles(word_lists, lengths, path):
    cues, elapsed, index = [], 0.0, 1
    for words, length in zip(word_lists, lengths):
        for start in range(0, len(words), 8):
            group = words[start:start+8]
            begin, end = float(group[0]['start']), float(group[-1]['end'])
            if not 0 <= begin < end <= length + 0.1:
                raise ValueError('Caption timestamps exceed scene audio')
            text = '\n'.join(textwrap.wrap(' '.join(w['word'].strip() for w in group), 48))
            cues.append(f'{index}\n{timestamp(elapsed+begin)} --> {timestamp(elapsed+min(end,length))}\n{text}\n')
            index += 1
        elapsed += length
    path.write_text('\n'.join(cues), encoding='utf-8')


def render_scene(image, audio, output):
    length = duration(audio)
    frames = round(length * 30)
    vf = ("scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
          f"zoompan=z='min(zoom+0.00015,1.06)':d={frames}:s=1920x1080:fps=30,"
          f"fade=t=in:st=0:d=0.35,fade=t=out:st={max(0,length-0.35)}:d=0.35,format=yuv420p")
    shell('ffmpeg', '-y', '-i', str(image), '-i', str(audio), '-vf', vf, '-t', str(length),
          '-c:v', 'libx264', '-preset', 'fast', '-crf', '21', '-c:a', 'aac', '-ar', '48000',
          '-ac', '2', '-movflags', '+faststart', str(output))
    return length


def subtitles(scenes, lengths, path):
    # Phrase timings are estimates within precisely measured scene audio, not forced alignment.
    cues, elapsed, index = [], 0.0, 1
    for scene, length in zip(scenes, lengths):
        words = scene['narration'].split()
        for start in range(0, len(words), 9):
            end = min(start + 9, len(words))
            text = '\n'.join(textwrap.wrap(' '.join(words[start:end]), 48))
            cues.append(f'{index}\n{timestamp(elapsed+length*start/len(words))} --> '
                        f'{timestamp(elapsed+length*end/len(words))}\n{text}\n')
            index += 1
        elapsed += length
    path.write_text('\n'.join(cues), encoding='utf-8')


def check_video(path, min_duration=180):
    metadata = probe(path)
    video = next(s for s in metadata['streams'] if s['codec_type'] == 'video')
    assert (video['width'], video['height']) == (1920, 1080), 'Wrong output dimensions'
    assert min_duration <= float(metadata['format']['duration']) <= 600, 'Duration outside required range'
    assert any(s['codec_type'] == 'audio' for s in metadata['streams']), 'Missing audio'
    shell('ffmpeg', '-v', 'error', '-i', str(path), '-f', 'null', '-')
    return metadata


class Store:
    def __init__(self):
        import boto3
        self.client = boto3.client('s3', endpoint_url=os.getenv('S3_ENDPOINT_URL') or None)
        self.bucket = required('S3_BUCKET')

    def load(self, key, default):
        from botocore.exceptions import ClientError
        try:
            return json.loads(self.client.get_object(Bucket=self.bucket, Key=key)['Body'].read())
        except ClientError as error:
            if error.response['Error']['Code'] == 'NoSuchKey':
                return default
            raise

    def save(self, key, value):
        self.client.put_object(Bucket=self.bucket, Key=key, Body=json.dumps(value).encode(), ContentType='application/json')

    def upload(self, path, key):
        self.client.upload_file(str(path), self.bucket, key)


def upload_private(video, thumbnail, story, state, store, key):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    client = build('youtube', 'v3', credentials=Credentials.from_authorized_user_info(
        json.loads(required('YOUTUBE_TOKEN_JSON'))), cache_discovery=False)
    channels = client.channels().list(part='id', mine=True).execute()['items']
    if required('EXPECTED_CHANNEL_ID') not in [c['id'] for c in channels]:
        raise RuntimeError('OAuth account is not the expected YouTube channel')
    # Persist before insert. An interrupted/ambiguous upload requires manual reconciliation.
    # Never silently retry videos.insert and risk duplicate videos.
    state['phase'] = 'upload_started'
    store.save(key, state)
    request = client.videos().insert(part='snippet,status', notifySubscribers=False,
        body={'snippet': {'title': story['title'], 'description': story['description'] +
             '\n\n' + os.getenv('MUSIC_CREDIT', ''), 'tags': story['tags'], 'categoryId': '22',
             'defaultLanguage': 'en'}, 'status': {'privacyStatus': 'private', 'selfDeclaredMadeForKids': False}},
        media_body=MediaFileUpload(str(video), chunksize=8*1024*1024, resumable=True))
    result = None
    while result is None:
        _, result = request.next_chunk(num_retries=5)
    state.update(phase='uploaded', video_id=result['id'])
    store.save(key, state)
    client.thumbnails().set(videoId=result['id'], media_body=MediaFileUpload(str(thumbnail))).execute()
    remote = client.videos().list(part='status', id=result['id']).execute()['items'][0]
    assert remote['status']['privacyStatus'] == 'private', 'Upload privacy validation failed'
    state['phase'] = 'complete'
    store.save(key, state)


def preflight():
    needed = ['GROQ_API_KEY', 'HF_TOKEN', 'IMAGE_MODEL', 'MUSIC_URL', 'S3_BUCKET',
              'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY']
    if os.getenv('UPLOAD_ENABLED') == 'true':
        needed += ['YOUTUBE_TOKEN_JSON', 'EXPECTED_CHANNEL_ID']
    missing = [name for name in needed if not os.getenv(name)]
    missing += [name for name in ('ffmpeg', 'ffprobe') if not shutil.which(name)]
    if missing:
        raise RuntimeError('Missing: ' + ', '.join(missing))


def run(daily=False):
    if daily and os.getenv('DAILY_ENABLED') != 'true':
        raise RuntimeError('Daily automation is disabled until the complete private test passes')
    preflight()
    import requests
    from PIL import Image, ImageDraw, ImageFont, ImageOps
    day = dt.datetime.now(ZoneInfo('Asia/Dhaka')).date().isoformat()
    run_id = day if daily else day + '-test'
    root = Path('output') / run_id
    root.mkdir(parents=True, exist_ok=True)
    store, key = Store(), f'runs/{run_id}/state.json'
    state = store.load(key, {})
    if state.get('phase') in ('upload_started', 'uploaded', 'complete'):
        raise RuntimeError('Run already uploaded or needs upload reconciliation; inspect state before continuing')
    history = store.load('history.json', [])
    story = state.get('story') or make_story(day, history[-30:])
    digest = hashlib.sha256(' '.join(s['narration'] for s in story['scenes']).encode()).hexdigest()
    if digest in [h.get('hash') for h in history]:
        raise RuntimeError('Exact duplicate story rejected')
    state.update(story=story, phase='generating', hash=digest)
    store.save(key, state)
    (root/'story.json').write_text(json.dumps(story, indent=2))
    lengths, clips, word_lists = [], [], []
    for i, scene in enumerate(story['scenes']):
        image, audio, clip = [root/f'{i:02}.{ext}' for ext in ('png', 'wav', 'mp4')]
        if not image.exists():
            make_image(scene['image_prompt'], image)
        if not audio.exists():
            audio.write_bytes(request_groq('audio/speech', {'model': os.getenv('TTS_MODEL', 'playai-tts'),
                'voice': os.getenv('TTS_VOICE', 'Fritz-PlayAI'), 'input': scene['narration'], 'response_format': 'wav'}, True))
        lengths.append(render_scene(image, audio, clip))
        clips.append(clip)
        words_file = root/f'{i:02}-words.json'
        if not words_file.exists():
            words_file.write_text(json.dumps(transcribe(audio)))
        word_lists.append(json.loads(words_file.read_text()))
    if not 180 <= sum(lengths) <= 600:
        raise RuntimeError('Narration length outside 3–10 minutes; revise story before upload')
    aligned_subtitles(word_lists, lengths, root/'captions.srt')
    playlist = root/'clips.txt'
    playlist.write_text(''.join(f"file '{p.name}'\n" for p in clips))
    shell('ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(playlist), '-c', 'copy', str(root/'joined.mp4'))
    music_url = required('MUSIC_URL')
    if not music_url.startswith('https://'):
        raise RuntimeError('MUSIC_URL must be HTTPS')
    response = requests.get(music_url, timeout=120)
    response.raise_for_status()
    (root/'music.audio').write_bytes(response.content)
    video = root/'video.mp4'
    shell('ffmpeg', '-y', '-i', str(root/'joined.mp4'), '-stream_loop', '-1', '-i', str(root/'music.audio'),
        '-filter_complex', '[0:a]loudnorm=I=-16:TP=-1.5:LRA=11[v];[1:a]volume=0.08[m];'
        '[m][v]sidechaincompress=threshold=0.02:ratio=8[duck];[0:a][duck]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11[a]',
        '-vf', f"subtitles={root/'captions.srt'}:force_style='FontName=DejaVu Sans,FontSize=22,Outline=2,MarginV=35'",
        '-map', '0:v', '-map', '[a]', '-t', str(sum(lengths)), '-c:v', 'libx264', '-preset', 'fast',
        '-crf', '21', '-c:a', 'aac', '-movflags', '+faststart', str(video))
    check_video(video)
    thumb_source, thumb = root/'thumbnail-source.png', root/'thumbnail.jpg'
    make_image(story['thumbnail_prompt'], thumb_source)
    image = ImageOps.fit(Image.open(thumb_source).convert('RGB'), (1280, 720))
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 72)
    draw.rectangle((0, 470, 1280, 720), fill=(15, 18, 24))
    draw.multiline_text((55, 500), '\n'.join(textwrap.wrap(story['thumbnail_text'].upper(), 22)),
                        font=font, fill='white', stroke_width=2, stroke_fill='black')
    image.save(thumb, quality=90)
    assert thumb.stat().st_size < 2*1024*1024
    for path in (video, thumb, root/'captions.srt', root/'story.json'):
        store.upload(path, f'runs/{run_id}/{path.name}')
    state['phase'] = 'rendered'
    store.save(key, state)
    if os.getenv('UPLOAD_ENABLED') == 'true':
        upload_private(video, thumb, story, state, store, key)
    history.append({'title': story['title'], 'hash': digest, 'run': run_id})
    store.save('history.json', history)
    print(json.dumps({'run': run_id, 'phase': state['phase'], 'video_id': state.get('video_id')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['preflight', 'test', 'daily'])
    command = parser.parse_args().command
    if command == 'preflight':
        preflight()
    else:
        run(daily=command == 'daily')
