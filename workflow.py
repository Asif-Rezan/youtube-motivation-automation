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
import time
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
    if os.getenv('STORY_FILE'):
        # Explicit original test story only; daily jobs must generate fresh stories.
        return validate_story(json.loads(Path(os.environ['STORY_FILE']).read_text()))
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
    if os.getenv('IMAGE_BACKEND', 'cpu') == 'cpu':
        from image_cpu import generate
        generate(prompt + ', cinematic lighting, no lettering or watermarks', path)
        return
    if os.getenv('IMAGE_BACKEND') != 'hf':
        raise ValueError('IMAGE_BACKEND must be cpu or hf')
    from huggingface_hub import InferenceClient
    image = InferenceClient(api_key=required('HF_TOKEN')).text_to_image(
        prompt=prompt + ', cinematic lighting, landscape composition, no text or watermarks',
        model=required('IMAGE_MODEL'), width=1344, height=768)
    image.save(path)


def speech_chunks(text, limit=200):
    chunks, current = [], ''
    for word in text.split():
        if len(word) > limit:
            raise ValueError('Narration contains a word longer than the TTS input limit')
        candidate = (current + ' ' + word).strip()
        if len(candidate) > limit:
            chunks.append(current)
            current = word
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def make_narration(text, path):
    if os.getenv('TTS_BACKEND', 'kokoro') == 'kokoro':
        from voice_cpu import generate
        generate(text, path)
        return
    parts = []
    for index, chunk in enumerate(speech_chunks(text)):
        part = path.with_name(path.stem + f'-part-{index:03}.wav')
        if not part.exists():
            part.write_bytes(request_groq('audio/speech', {
                'model': os.getenv('TTS_MODEL') or 'canopylabs/orpheus-v1-english',
                'voice': os.getenv('TTS_VOICE') or 'troy', 'input': chunk, 'response_format': 'wav'}, True))
        parts.append(part)
    playlist = path.with_suffix('.txt')
    playlist.write_text(''.join(f"file '{p.name}'\n" for p in parts))
    shell('ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(playlist), '-ar', '48000',
          '-ac', '2', '-c:a', 'pcm_s16le', str(path))


def transcribe(audio):
    if os.getenv('CAPTION_BACKEND', 'cpu') == 'cpu':
        from voice_cpu import transcribe_audio
        return transcribe_audio(audio)
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
    shell('ffmpeg', '-v', 'error', '-xerror', '-i', str(path), '-f', 'null', '-')
    return metadata


class Store:
    """Private Google Drive storage; never purchases additional quota."""
    def __init__(self):
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        self.client = build('drive', 'v3', credentials=Credentials.from_authorized_user_info(
            json.loads(required('DRIVE_TOKEN_JSON'))), cache_discovery=False)
        self.folder = os.getenv('DRIVE_FOLDER_ID')
        if not self.folder:
            query = ("trashed = false and mimeType = 'application/vnd.google-apps.folder' and "
                     "appProperties has { key='youtube_automation_root' and value='v1' }")
            roots = self.client.files().list(q=query, fields='files(id)', pageSize=100).execute()['files']
            if len(roots) > 1:
                raise RuntimeError('Multiple workflow folders require reconciliation')
            if roots:
                self.folder = roots[0]['id']
            else:
                self.folder = self.client.files().create(body={
                    'name': 'YouTubeAutomation',
                    'mimeType': 'application/vnd.google-apps.folder',
                    'appProperties': {'youtube_automation_root': 'v1'}
                }, fields='id').execute()['id']
        info = self.client.files().get(fileId=self.folder, fields='mimeType,trashed').execute()
        if info.get('trashed') or info['mimeType'] != 'application/vnd.google-apps.folder':
            raise RuntimeError('DRIVE_FOLDER_ID must identify an accessible active folder')
        self.check_private(self.folder)

    def check_private(self, file_id):
        permissions = self.client.permissions().list(fileId=file_id,
            fields='permissions(type,role)', pageSize=100).execute().get('permissions', [])
        if any(p.get('role') != 'owner' for p in permissions):
            raise RuntimeError('Workflow storage must be private to its owner')

    def find(self, key):
        # Query using only an internal SHA-256 key, never interpolated user input.
        digest = hashlib.sha256(key.encode()).hexdigest()
        q = (f"'{self.folder}' in parents and trashed = false and "
             f"appProperties has {{ key='workflow_key' and value='{digest}' }}")
        items = self.client.files().list(q=q, fields='files(id)', pageSize=100).execute()['files']
        if len(items) > 1:
            raise RuntimeError('Duplicate checkpoint files require reconciliation')
        if items:
            self.check_private(items[0]['id'])
            return items[0]['id']
        return None

    def load(self, key, default):
        file_id = self.find(key)
        if not file_id:
            return default
        return json.loads(self.client.files().get_media(fileId=file_id).execute())

    def check_quota(self, size):
        quota = self.client.about().get(fields='storageQuota').execute()['storageQuota']
        if 'limit' not in quota:
            raise RuntimeError('Cannot verify free storage allowance; stop before upload')
        limit = min(int(quota['limit']), 15 * 1024**3)
        if int(quota.get('usage', 0)) + size + 100 * 1024**2 > limit:
            raise RuntimeError('Free storage allowance nearly full; no paid upgrade will be requested')

    def put(self, key, media, size):
        self.check_private(self.folder)
        self.check_quota(size)
        file_id = self.find(key)
        if file_id:
            return self.client.files().update(fileId=file_id, media_body=media, fields='id').execute()
        metadata = {'name': key.replace('/', '__'), 'parents': [self.folder],
                    'appProperties': {'workflow_key': hashlib.sha256(key.encode()).hexdigest()}}
        return self.client.files().create(body=metadata, media_body=media, fields='id').execute()

    def save(self, key, value):
        import io
        from googleapiclient.http import MediaIoBaseUpload
        payload = json.dumps(value).encode()
        self.put(key, MediaIoBaseUpload(io.BytesIO(payload), mimetype='application/json', resumable=True), len(payload))

    def upload(self, path, key):
        from googleapiclient.http import MediaFileUpload
        self.put(key, MediaFileUpload(str(path), resumable=True), path.stat().st_size)

    def download(self, file_id, path):
        import io
        from googleapiclient.http import MediaIoBaseDownload
        self.check_private(file_id)
        with path.open('wb') as output:
            request = MediaIoBaseDownload(output, self.client.files().get_media(fileId=file_id))
            done = False
            while not done:
                _, done = request.next_chunk(num_retries=3)


def load_music(store, root):
    # CPU music generation uses no API credits or paid provider.
    if os.getenv('MUSIC_BACKEND', 'magenta') == 'magenta':
        from music_cpu import generate
        generate(root/'music.audio')
        return 'Background music: original Magenta MusicRNN melody with synthesized ambient piano.'
    # Only free sources. vidIQ-generated assets are not accepted.
    manifest = store.load('music-manifest.json', None)
    if not manifest or manifest.get('source') not in ('YouTube Audio Library', 'AI-generated (free local model)'):
        raise RuntimeError('Missing verified background music manifest in Drive')
    if manifest.get('attribution_required') and not manifest.get('attribution', '').strip():
        raise RuntimeError('Audio Library track requires attribution')
    target = root/'music.audio'
    store.download(manifest['file_id'], target)
    if hashlib.sha256(target.read_bytes()).hexdigest() != manifest['sha256']:
        raise RuntimeError('Music file differs from the licensed track in the manifest')
    duration(target)  # Reject unreadable files.
    return manifest.get('attribution', '')


def upload_private(video, thumbnail, story, state, store, key, music_credit=''):
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
             '\n\n' + music_credit, 'tags': story['tags'], 'categoryId': '22',
             'defaultLanguage': 'en'}, 'status': {'privacyStatus': 'private', 'selfDeclaredMadeForKids': False}},
        media_body=MediaFileUpload(str(video), chunksize=8*1024*1024, resumable=True))
    result = None
    while result is None:
        _, result = request.next_chunk(num_retries=5)
    state.update(phase='uploaded', video_id=result['id'])
    store.save(key, state)
    client.thumbnails().set(videoId=result['id'], media_body=MediaFileUpload(str(thumbnail))).execute()
    deadline = time.monotonic() + 1200
    while True:
        items = client.videos().list(part='status,processingDetails', id=result['id']).execute().get('items', [])
        if not items:
            raise RuntimeError('Uploaded video is not accessible for verification')
        remote = items[0]
        assert remote['status']['privacyStatus'] == 'private', 'Upload privacy validation failed'
        processing = remote.get('processingDetails', {}).get('processingStatus')
        upload_status = remote['status'].get('uploadStatus')
        if processing in ('failed', 'terminated') or upload_status in ('failed', 'rejected', 'deleted'):
            raise RuntimeError('YouTube rejected or failed to process the private video')
        if processing == 'succeeded' and upload_status == 'processed':
            break
        if time.monotonic() >= deadline:
            raise RuntimeError('YouTube processing is still pending; private test is not passed')
        print(json.dumps({'check': 'YouTube processing', 'status': processing}), flush=True)
        time.sleep(20)
    state['processing_status'] = 'succeeded'
    state['phase'] = 'complete'
    store.save(key, state)


def preflight():
    needed = ['DRIVE_TOKEN_JSON']
    if not os.getenv('STORY_FILE') or os.getenv('TTS_BACKEND', 'kokoro') == 'groq' or os.getenv('CAPTION_BACKEND', 'cpu') == 'groq':
        needed.append('GROQ_API_KEY')
    if os.getenv('IMAGE_BACKEND', 'cpu') == 'hf':
        needed += ['HF_TOKEN', 'IMAGE_MODEL']
    else:
        import importlib.util
        for module in ('torch', 'diffusers', 'transformers'):
            if importlib.util.find_spec(module) is None:
                needed.append(module + ' (CPU dependency)')
    import importlib.util
    if os.getenv('TTS_BACKEND', 'kokoro') == 'kokoro' and importlib.util.find_spec('kokoro') is None:
        needed.append('kokoro (CPU dependency)')
    if os.getenv('CAPTION_BACKEND', 'cpu') == 'cpu' and importlib.util.find_spec('faster_whisper') is None:
        needed.append('faster_whisper (CPU dependency)')
    if os.getenv('MUSIC_BACKEND', 'magenta') == 'magenta' and not shutil.which('node'):
        needed.append('node (CPU music dependency)')
    if os.getenv('UPLOAD_ENABLED') == 'true':
        needed += ['YOUTUBE_TOKEN_JSON', 'EXPECTED_CHANNEL_ID']
    missing = [name for name in needed if not os.getenv(name)]
    missing += [name for name in ('ffmpeg', 'ffprobe') if not shutil.which(name)]
    if missing:
        raise RuntimeError('Missing: ' + ', '.join(missing))


def run(daily=False):
    if daily and os.getenv('STORY_FILE'):
        raise RuntimeError('Daily automation cannot reuse a fixed test story')
    if daily and os.getenv('DAILY_ENABLED') != 'true':
        raise RuntimeError('Daily automation is disabled until the complete private test passes')
    preflight()
    from PIL import Image, ImageDraw, ImageFont, ImageOps
    day = dt.datetime.now(ZoneInfo('Asia/Dhaka')).date().isoformat()
    run_id = day if daily else day + '-test'
    root = Path('output') / run_id
    root.mkdir(parents=True, exist_ok=True)
    store, key = Store(), f'runs/{run_id}/state.json'
    test_record = store.load('last-private-test.json', {}) if daily else {}
    if daily and (not test_record.get('passed') or not test_record.get('remote_verification', {}).get('private_test_passed')):
        raise RuntimeError('No fully verified private HD upload test is recorded')
    state = store.load(key, {})
    if state.get('phase') in ('upload_started', 'uploaded', 'complete'):
        raise RuntimeError('Run already uploaded or needs upload reconciliation; inspect state before continuing')
    music_credit = load_music(store, root)
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
            make_narration(scene['narration'], audio)
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
    video = root/'video.mp4'
    shell('ffmpeg', '-y', '-i', str(root/'joined.mp4'), '-stream_loop', '-1', '-i', str(root/'music.audio'),
        '-filter_complex', '[0:a]loudnorm=I=-16:TP=-1.5:LRA=11,asplit=2[voice][side];[1:a]volume=0.09[music];'
        '[music][side]sidechaincompress=threshold=0.02:ratio=8[duck];[voice][duck]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11[a]',
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
        upload_private(video, thumb, story, state, store, key, music_credit)
    if state['phase'] == 'complete':
        history.append({'title': story['title'], 'hash': digest, 'run': run_id})
        store.save('history.json', history)
        if not daily:
            store.save('last-private-test.json', {'passed': True, 'run': run_id, 'video_id': state['video_id']})
    print(json.dumps({'run': run_id, 'phase': state['phase'], 'video_id': state.get('video_id')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['preflight', 'test', 'daily'])
    command = parser.parse_args().command
    if command == 'preflight':
        preflight()
    else:
        run(daily=command == 'daily')
