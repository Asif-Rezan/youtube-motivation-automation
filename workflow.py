"""Cloud rendering and private upload helpers; daily_publish verifies and publishes daily runs."""
import argparse
import datetime as dt
import hashlib
from difflib import SequenceMatcher
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import textwrap
import time
from zoneinfo import ZoneInfo

FINAL_CTA = (" Which choice would you have made in that situation? "
    'Leave a comment with your answer, like this video if it inspired you, '
    'and subscribe for more stories about money, choices, and everyday life.')

VISUAL_STYLE = ('historical documentary reconstruction, realistic stone, wood and earth textures, '
    'natural scene-appropriate lighting, period-appropriate objects, clear landscape composition')
VISUAL_STYLE_ID = 'historical-documentary-ssd-v1'
IMAGE_INTERVAL_SECONDS = 7


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


def validate_story(data, word_range=(1200, 2500)):
    if not isinstance(data, dict) or not 4 <= len(data.get('scenes', [])) <= 32:
        raise ValueError('Story must contain 4–32 narration chapters')
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
    if not word_range[0] <= words <= word_range[1]:
        raise ValueError(f'Expected {word_range[0]}–{word_range[1]} narrated words; received {words}')
    if not isinstance(data.get('thumbnail_text'), str) or len(data['thumbnail_text']) > 45:
        raise ValueError('Invalid thumbnail text')
    if not isinstance(data.get('thumbnail_prompt'), str):
        raise ValueError('Missing thumbnail prompt')
    from content_strategy import validate_pov
    validate_pov(data)
    from human_history import validate
    validate(data)
    return data


def check_recent_originality(story, history):
    """Reject obviously interchangeable recent concepts before rendering or upload."""
    title = ' '.join(story['title'].lower().split())
    for item in history[-30:]:
        old_title = ' '.join(item.get('title', '').lower().split())
        if old_title and SequenceMatcher(None, title, old_title).ratio() >= 0.82:
            raise ValueError('Story title is too similar to a recent upload')
    if story.get('format') and story['format'] in [h.get('format') for h in history[-2:]]:
        raise ValueError('Story format repeats one of the last two uploads')


def request_text(endpoint, payload):
    if os.getenv('TEXT_BACKEND', 'qwen-local') != 'qwen-local':
        raise ValueError('Only the local Qwen text backend is supported')
    from story_cpu import request_story
    return request_story(endpoint, payload)


def text_batch_pause(seconds=60):
    """Local inference needs no provider cooldown between batches."""
    return None


def make_story(day, previous, *, draft=None, checkpoint=None):
    if os.getenv('STORY_FILE'):
        # Explicit original test story only; daily jobs must generate fresh stories.
        return validate_story(json.loads(Path(os.environ['STORY_FILE']).read_text()))
    model = os.getenv('STORY_MODEL', 'Qwen/Qwen3-4B-Instruct-2507')
    def object_schema(properties):
        return {'type': 'object', 'properties': properties,
            'required': list(properties), 'additionalProperties': False}
    text_schema = {'type': 'string'}
    financial = os.getenv('CONTENT_TYPE') == 'financial-storytelling'
    from content_strategy import PROFILE, PILLARS, select_pillar, narration_direction
    pillar = select_pillar(day, previous) if financial else None
    scene_schema = object_schema({'summary': text_schema, 'image_prompt': text_schema,
        **({'continuity_note': text_schema} if financial else {}),
        'image_prompts': {'type': 'array', 'items': text_schema}})
    chapter_keys = [f'chapter_{i:02}' for i in range(1, 21)]
    outline_schema = object_schema({**({'story_bible': text_schema} if financial else {}), **{k: text_schema for k in
        ('title', 'description', 'thumbnail_text', 'thumbnail_prompt', 'character_description', 'protagonist_name')},
        'tags': {'type': 'array', 'items': text_schema},
        'scenes': object_schema({k: scene_schema for k in chapter_keys})})
    def ask(prompt, limit, schema):
        result = request_text('chat/completions', {'model': model,
            'messages': [{'role': 'user', 'content': prompt}],
            'response_format': {'type': 'json_schema', 'json_schema': {'name': 'story_payload',
                'strict': True, 'schema': schema}}, 'reasoning_effort': 'low',
            'temperature': 0.8, 'max_completion_tokens': limit})
        choice = result['choices'][0]
        if choice.get('finish_reason') == 'length':
            raise RuntimeError('Story response was truncated; refusing incomplete script')
        return json.loads(choice['message']['content'])
    if os.getenv('CONTENT_TYPE', 'human-history') == 'human-history':
        from human_history import generate
        outline = generate(day, previous, ask, text_batch_pause, check_recent_originality, object_schema,
                           draft=draft, checkpoint=checkpoint)
        from long_video import validate_engagement
        validate_engagement(outline)
        return validate_story(outline)
    formats = (
        ('decision_drama', 'A character must choose between two costly financial options; show the consequences of the choice.'),
        ('business_postmortem', 'Reconstruct a fictional small business failure, then show the specific decisions that enabled recovery.'),
        ('money_psychology', 'Follow one harmful money belief through concrete incidents until the character tests and changes it.'),
        ('family_tradeoff', 'Tell a multigenerational family story around a financial disagreement and its human consequences.'),
        ('everyday_mistake', 'Trace one ordinary money mistake through escalating real-world consequences and a practical correction.'),
        ('two_paths', 'Contrast two fictional people facing the same money problem whose choices produce different outcomes.'),
    ) if financial else (
        ('decision_drama', 'Build the story around one difficult choice and its consequences.'),
        ('relationship_conflict', 'Build the story around a relationship conflict and an earned reconciliation.'),
        ('setback_recovery', 'Reconstruct a specific failure and the concrete steps of recovery.'),
        ('two_paths', 'Contrast two characters facing the same challenge with different choices.'),
    )
    recent_formats = [h.get('format') for h in previous[-3:]]
    selected_format, format_direction = next(
        ((name, direction) for name, direction in formats if name not in recent_formats),
        formats[0])
    theme = ('Original immersive financial storytelling about money psychology, financial resilience, '
        'work, family, business, lifestyle pressure and personal freedom. Real financial history is allowed ONLY when verified source '
        'material is supplied; otherwise choose fiction. Never invent historical facts or investment '
        'returns. Show realistic tradeoffs and uncertainty, no guaranteed wealth or personalized advice.'
        if financial else 'Motivational storytelling.')
    pov_brief = (f'''Original second-person financial scenario for an adult US audience.
    Today's topic pillar is {pillar}: {PILLARS[pillar]}
    The viewer is the protagonist: narrate as you/your, never as a biography of a named hero.
    Give that same person an internal first name for consistent image generation; it is not the narrator's viewpoint.
    Open inside a concrete, ordinary money decision with an immediate consequence or revealing contradiction.
    Establish the title's promised conflict within chapter 1. Curiosity can be implicit; do not force a rhetorical question.
    Chapters 1-3: immediate scene, stakes and goal. Chapters 4-8: choices, budget constraints and first consequences.
    Chapters 9-14: a believable setback, relationship tension and an imperfect adjustment.
    Chapters 15-18: demonstrate the result with elapsed time, costs and remaining uncertainty.
    Chapters 19-20: pay off the opening scene and show what changed in autonomy, time or trust.
    Use one or two recurring people with their own motives, sensory everyday details and short natural dialogue.
    Keep suspense through a pending decision or consequence, not repetitive teaser sentences or artificial cliffhangers.
    No automatic millionaire ending, villainous poor friends, perfect savers or magical investment recovery.
    Show the financial mechanism through a concrete choice, not a list of tips. Maintain consistent arithmetic:
    distinguish gross pay from take-home pay, revenue from profit, savings from investment gains and cash from net worth.
    Avoid specific investment returns, current tax limits, benefits rules or legal claims without supplied verified sources.
    Story money amounts and circumstances are illustrative fiction. Do not present this as a true account.
    Title must start "POV: You" and promise a specific decision or consequence, max 85 characters.
    Invent the title, events and dialogue; do not reproduce another channel's titles, characters or plot sequence.
    story_bible: max 180 words recording starting age/job, family, take-home income, recurring expenses,
    opening cash/debt, goal, time horizon and the causal ending. Use only the numbers the plot actually needs.
    Each chapter's continuity_note: max 18 words recording elapsed time, any money changes and unresolved setup/payoff.
    Keep chapter summaries to 18 words and image_prompt to 16 words to fit the outline response budget.
    Description must clearly disclose an original fictional, educational scenario, not personal financial advice.
    ''' if financial else '')
    outline = ask(f'''Plan an original fictional English motivational story for {day}.
    Content direction: {theme}
    {pov_brief}
    This video's format is {selected_format}: {format_direction}
    Make its central problem, setting, character relationships, turning points, and resolution materially distinct.
    Avoid these previous titles and plots: {json.dumps(previous[-30:])}.
    A concrete consequential choice or revealing contradiction must open the FIRST sentence.
    No greeting or generic motivational preamble. Give the protagonist one concrete goal, believable setbacks, and earned resolution.
    No random magical trials, repeated mentor lessons, or repeated endings. Escalate choices, setbacks, surprising reversals,
    specific dialogue, and emotional payoffs. Resolve the opening question in the final act.
    Last chapter ends with an earned resolution and a specific reflection. No viewer calls to action in the story plan.
    Create an original plot and title; avoid generic stock stories.
    Return JSON: title (max 100 characters), description (clearly label fictional), tags (list),
    thumbnail_text (2-5 words, metadata only), thumbnail_prompt (one specific scene from the story,
    showing the protagonist and the financial or emotional contrast; no written words),
    protagonist_name (first name), character_description (max 24 words: age appearance,
    skin tone, face shape, hair color and style, consistent outfit),
    scenes (object with chapter_01 through chapter_20). Each chapter: summary (max 25 words), image_prompt,
    image_prompts ({'two' if financial else 'four'} distinct visual beats, each max 8 words). Use clear scenes that work as
    cinematic 2D editorial illustrations grounded in each chapter's actual events, setting, and time of day.
    Show the specific narrated action or objects; include unusual or fantastical elements only when the story describes them.
    Main character keeps the same appearance and clothing. Provide ONLY the plan, no full narration yet.''', 5200, outline_schema)
    outline['scenes'] = [outline['scenes'][k] for k in chapter_keys]
    outline['format'] = selected_format
    if financial:
        outline['content_profile'] = PROFILE
        outline['content_pillar'] = pillar
    # Reject repeated packaging before spending requests on twenty narrated chapters.
    check_recent_originality(outline, previous)
    if len(outline.get('scenes', [])) != 20:
        raise ValueError('Outline requires exactly twenty chapters')
    summaries = [scene['summary'] for scene in outline['scenes']]
    prior = ''
    for begin in (0, 5, 10, 15):
        # Separate bursts fit the free plan; never switch to a paid provider.
        text_batch_pause()
        keys = chapter_keys[begin:begin+5]
        group_schema = object_schema({'narrations': object_schema({k: text_schema for k in keys})})
        group = ask(f'''Write chapters {begin+1} through {begin+5} of this original fictional story.
        Content direction: {theme}
        {narration_direction(outline)}
        Story bible: {outline.get('story_bible', '')}
        Full continuity map (context only, do not narrate future events): {json.dumps([{'chapter': i+1, 'event': s['summary'], 'continuity': s.get('continuity_note', '')} for i, s in enumerate(outline['scenes'])])}.
        Title: {outline['title']}. Character: {outline['character_description']}.
        Assigned chapter events ONLY: {json.dumps([{'chapter': i+1, 'event': summaries[i]} for i in range(begin, begin+5)])}.
        Previous chapter ending: {prior[-700:]}.
        Return JSON with narrations: an object with the exact chapter keys {keys}, each value a narration string.
        Each string MUST contain 82-88 English spoken words; total for this request 410-440 words.
        Aim for about 1650-1800 spoken words across all twenty chapters including the final CTA.
        Natural narration with concrete actions and dialogue, not generic advice.
        Begin chapter 1 inside the promised money decision immediately, no welcome or setup preamble.
        Vary sentence length for natural speech. Explain an unfamiliar money term briefly in context.
        Preserve dates, balances and relationships from the continuity map; do not invent a new windfall or time jump.
        Each chapter must advance a choice, consequence or relationship rather than repeat a lesson.
        Escalate stakes, introduce reversals and emotional payoffs every few chapters.
        Resolve the initial crisis by chapter 20. Do not include any viewer call to action in any chapter;
        the application adds a final like, comment, and subscribe request separately.
        Narrate ONLY the five assigned events, one event per chapter in the listed order. Do not jump ahead.\n        No ending, farewell, viewer question, or call to action before chapter 20.
        Do not add chapter headings or directions to spoken text. No repeated introduction.''', 4200, group_schema)
        parts = [group['narrations'][k] for k in keys]
        if len(parts) != 5 or not all(isinstance(p, str) for p in parts):
            raise ValueError('Narration batch must contain five strings')
        if financial:
            for attempt in range(2):
                missing = [key for key, part in zip(keys, parts)
                           if not re.search(r'\b(you|your|yours|yourself)\b', part, re.I)]
                if not missing:
                    break
                print(json.dumps({'narration_pov_retry': attempt + 1, 'chapters': missing}), flush=True)
                text_batch_pause()
                repair_schema = object_schema({'narrations': object_schema({k: text_schema for k in missing})})
                repaired = ask(f'''Rewrite ONLY these chapters in second person, addressing the protagonist as you/your in EVERY chapter.
                Keep 82-88 English spoken words per chapter. Preserve the events, dialogue meaning, money amounts and timeline.
                {narration_direction(outline)}
                Story bible: {outline.get('story_bible', '')}
                Full continuity map: {json.dumps(outline['scenes'])}
                Previous chapter ending: {prior[-700:]}
                Chapters to rewrite: {json.dumps({key: part for key, part in zip(keys, parts) if key in missing})}
                Return narrations with exactly these keys: {missing}. No headings or viewer calls to action.''',
                    4200, repair_schema)
                for index, key in enumerate(keys):
                    if key in missing:
                        replacement = repaired['narrations'][key]
                        if not isinstance(replacement, str):
                            raise ValueError(f'Financial POV {key} narration must be a string')
                        parts[index] = replacement
            missing = [key for key, part in zip(keys, parts)
                       if not re.search(r'\b(you|your|yours|yourself)\b', part, re.I)]
            if missing:
                raise ValueError(f'Financial POV chapters lost second-person narration after two repairs: {", ".join(missing)}')
        for scene, narration in zip(outline['scenes'][begin:begin+5], parts):
            scene['narration'] = narration
        prior = parts[-1]
    outline['scenes'][-1]['narration'] += FINAL_CTA
    from long_video import validate_engagement
    validate_engagement(outline)
    return validate_story(outline)


def make_image(prompt, path):
    from human_history import IMAGE_PREFIX
    compact = prompt.startswith(IMAGE_PREFIX)
    if VISUAL_STYLE not in prompt and not compact:
        prompt += '. ' + VISUAL_STYLE
    if os.getenv('IMAGE_BACKEND', 'cpu') == 'cpu':
        from image_cpu import generate
        generate(prompt if compact else prompt + ', no text, no letters, no watermark', path)
        return
    if os.getenv('IMAGE_BACKEND') != 'hf':
        raise ValueError('IMAGE_BACKEND must be cpu or hf')
    from huggingface_hub import InferenceClient
    image = InferenceClient(api_key=required('HF_TOKEN')).text_to_image(
        prompt=prompt + ', no text, no letters, no watermarks',
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
    if os.getenv('TTS_BACKEND', 'kokoro') != 'kokoro':
        raise ValueError('Only local Kokoro narration is supported')
    from voice_cpu import generate
    generate(text, path)


def transcribe(audio):
    if os.getenv('CAPTION_BACKEND', 'cpu') != 'cpu':
        raise ValueError('Only local CPU captions are supported')
    from voice_cpu import transcribe_audio
    return transcribe_audio(audio)


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


def check_video(path, min_duration=600, max_duration=900):
    metadata = probe(path)
    video = next(s for s in metadata['streams'] if s['codec_type'] == 'video')
    assert (video['width'], video['height']) == (1920, 1080), 'Wrong output dimensions'
    assert min_duration <= float(metadata['format']['duration']) <= max_duration, 'Duration outside required range'
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
        creating = file_id is None
        if creating:
            file_id = self.client.files().generateIds(count=1, space='drive').execute()['ids'][0]
        metadata = {'name': key.replace('/', '__'), 'parents': [self.folder],
                    'appProperties': {'workflow_key': hashlib.sha256(key.encode()).hexdigest()}}
        if creating:
            metadata['id'] = file_id
        if os.getenv('RUN_SCOPED_CLEANUP') == 'true' and key.startswith('runs/'):
            parts = key.split('/')
            from daily_publish import disposable
            if len(parts) == 3 and disposable(parts[2]):
                metadata['appProperties'].update(automation_run=parts[1], disposable='v1')
        for attempt in range(5):
            try:
                if creating:
                    return self.client.files().create(body=metadata, media_body=media, fields='id').execute(num_retries=3)
                return self.client.files().update(fileId=file_id, media_body=media, fields='id').execute(num_retries=3)
            except Exception as error:
                status = getattr(getattr(error, 'resp', None), 'status', None)
                if creating and (status == 409 or isinstance(error, (TimeoutError, ConnectionError))):
                    # A timed-out create may already have completed. Never allocate a second ID.
                    try:
                        info = self.client.files().get(fileId=file_id, fields='id,size,parents,appProperties').execute(num_retries=3)
                        if (int(info.get('size', -1)) == size and self.folder in info.get('parents', [])
                                and info.get('appProperties', {}).get('workflow_key') == metadata['appProperties']['workflow_key']):
                            self.check_private(file_id)
                            return {'id': file_id}
                    except Exception:
                        if status == 409:
                            raise RuntimeError('Media upload conflict requires reconciliation') from error
                    if status == 409:
                        raise RuntimeError('Media upload conflict requires reconciliation') from error
                transient = isinstance(error, (TimeoutError, ConnectionError)) or status in (408, 429, 500, 502, 503, 504)
                if not transient or attempt == 4:
                    raise
                print(json.dumps({'check': 'Drive media upload', 'retry': attempt + 1,
                    'error_type': type(error).__name__}), flush=True)
                time.sleep(min(2 ** (attempt + 1), 16))

    def save(self, key, value):
        """Retry checkpoint writes against one fixed Drive ID, including ambiguous creates."""
        import io
        from googleapiclient.http import MediaIoBaseUpload
        payload = json.dumps(value).encode()
        self.check_private(self.folder)
        self.check_quota(len(payload))
        file_id = self.find(key)
        creating = file_id is None
        if creating:
            file_id = self.client.files().generateIds(count=1, space='drive').execute()['ids'][0]
        metadata = {'id': file_id, 'name': key.replace('/', '__'), 'parents': [self.folder],
            'appProperties': {'workflow_key': hashlib.sha256(key.encode()).hexdigest()}}
        for attempt in range(5):
            try:
                # Small JSON checkpoints do not need resumable upload sessions.
                media = MediaIoBaseUpload(io.BytesIO(payload), mimetype='application/json', resumable=False)
                if creating:
                    self.client.files().create(body=metadata, media_body=media, fields='id').execute()
                else:
                    self.client.files().update(fileId=file_id, media_body=media, fields='id').execute()
                return
            except Exception as error:
                status = getattr(getattr(error, 'resp', None), 'status', None)
                if creating and status == 409:
                    # The previous request may have succeeded before its response timed out.
                    self.check_private(file_id)
                    if json.loads(self.client.files().get_media(fileId=file_id).execute()) == value:
                        return
                    raise RuntimeError('Checkpoint creation conflict; refusing to overwrite') from None
                transient = isinstance(error, (TimeoutError, ConnectionError)) or status in (408, 429, 500, 502, 503, 504)
                if not transient or attempt == 4:
                    raise
                print(json.dumps({'check': 'Drive checkpoint save', 'retry': attempt+1,
                    'error_type': type(error).__name__}), flush=True)
                time.sleep(min(2 ** (attempt+1), 16))

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
        return ''
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
    from video_metadata import public_description
    state['upload_description'] = public_description(story['description'], music_credit)
    state['video_details_version'] = 1
    state['thumbnail_uploaded'] = False
    state['phase'] = 'upload_started'
    store.save(key, state)
    request = client.videos().insert(part='snippet,status,paidProductPlacementDetails', notifySubscribers=False,
        body={'snippet': {'title': story['title'], 'description': state['upload_description'], 'tags': story['tags'], 'categoryId': '27',
             'defaultLanguage': 'en-US', 'defaultAudioLanguage': 'en-US'},
             'paidProductPlacementDetails': {'hasPaidProductPlacement': False},
             'status': {'privacyStatus': 'private', 'selfDeclaredMadeForKids': False, 'containsSyntheticMedia': True}},
        media_body=MediaFileUpload(str(video), chunksize=8*1024*1024, resumable=True))
    result = None
    while result is None:
        _, result = request.next_chunk(num_retries=5)
    state.update(phase='uploaded', video_id=result['id'],
        uploaded_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        schedule_requested=os.getenv('SCHEDULE_PUBLISH') == 'true')
    store.save(key, state)
    client.thumbnails().set(videoId=result['id'], media_body=MediaFileUpload(str(thumbnail))).execute()
    state['thumbnail_uploaded'] = True
    store.save(key, state)
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
    if os.getenv('TEXT_BACKEND', 'qwen-local') != 'qwen-local':
        raise ValueError('Only the local Qwen text backend is supported')
    if os.getenv('TTS_BACKEND', 'kokoro') != 'kokoro' or os.getenv('CAPTION_BACKEND', 'cpu') != 'cpu':
        raise ValueError('Narration and captions must use local models')
    if not os.getenv('STORY_FILE'):
        import importlib.util
        if importlib.util.find_spec('llama_cpp') is None:
            needed.append('llama_cpp (local text dependency)')
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
    day = dt.datetime.now(ZoneInfo('Asia/Dhaka')).date().isoformat()
    run_id = day if daily else day + '-test'
    root = Path('output') / run_id
    root.mkdir(parents=True, exist_ok=True)
    store, key = Store(), f'runs/{run_id}/state.json'
    test_record = store.load('last-private-test.json', {}) if daily else {}
    if daily and (not test_record.get('passed') or not test_record.get('remote_verification', {}).get('private_test_passed') or test_record.get('validation', {}).get('image_interval_seconds') != IMAGE_INTERVAL_SECONDS or not test_record.get('validation', {}).get('storyboard_verified') or test_record.get('validation', {}).get('style') != VISUAL_STYLE_ID):
        raise RuntimeError('No fully verified private HD upload test is recorded')
    state = store.load(key, {})
    if state.get('phase') in ('upload_started', 'uploaded', 'complete', 'published', 'verified_private'):
        raise RuntimeError('Run already uploaded or needs upload reconciliation; inspect state before continuing')
    music_credit = load_music(store, root)
    history = store.load('history.json', [])
    story = state.get('story') or make_story(day, history[-30:])
    check_recent_originality(story, history)
    digest = hashlib.sha256(' '.join(s['narration'] for s in story['scenes']).encode()).hexdigest()
    if digest in [h.get('hash') for h in history]:
        raise RuntimeError('Exact duplicate story rejected')
    state.update(story=story, phase='generating', hash=digest)
    store.save(key, state)
    (root/'story.json').write_text(json.dumps(story, indent=2))
    from long_video import render_complete
    report = render_complete(story, root)
    video, thumb = root/'video.mp4', root/'thumbnail.jpg'
    for name in ('video.mp4', 'thumbnail.jpg', 'captions.srt', 'story.json', 'validation.json', 'plan.json'):
        store.upload(root/name, f'runs/{run_id}/{name}')
    state['validation'] = report
    state['phase'] = 'rendered'
    store.save(key, state)
    if os.getenv('UPLOAD_ENABLED') == 'true':
        upload_private(video, thumb, story, state, store, key, music_credit)
    if state['phase'] == 'complete':
        history.append({'title': story['title'], 'format': story.get('format'),
            'content_pillar': story.get('content_pillar'), 'content_profile': story.get('content_profile'),
            'hash': digest, 'run': run_id})
        store.save('history.json', history)
        if not daily:
            store.save('last-private-test.json', {'passed': True, 'run': run_id, 'video_id': state['video_id'], 'validation': state['validation']})
    print(json.dumps({'run': run_id, 'phase': state['phase'], 'video_id': state.get('video_id')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['preflight', 'test', 'daily'])
    command = parser.parse_args().command
    if command == 'preflight':
        preflight()
    else:
        run(daily=command == 'daily')
