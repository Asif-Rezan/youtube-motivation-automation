"""10–15 minute videos with a distinct story image every seven seconds."""
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
INTERVAL = w.IMAGE_INTERVAL_SECONDS
SHARDS = 20
ASSETS = ('story.json', 'plan.json', 'narration.wav', 'captions.srt')
MIN_DURATION, MAX_DURATION = 600, 900
PREFERRED_MIN, PREFERRED_MAX = 720, 840
MAX_CORRECTIONS = 3
MAX_NATURAL_TEMPO = 1.04


def run_id():
    return os.getenv('SAVED_RUN_ID') or (dt.datetime.now(ZoneInfo('Asia/Dhaka')).strftime('%Y-%m-%d-%H%M%S')+'-improved-story')


def shot_plan(story, lengths, word_lists):
    """Anchor every visual to words actually spoken in its global seven-second window."""
    if len(lengths) != len(word_lists) or len(lengths) != len(story['scenes']):
        raise ValueError('Chapter audio, transcript and story must agree')
    total = sum(lengths)
    timeline, offset = [], 0.0
    for chapter, (length, words) in enumerate(zip(lengths, word_lists)):
        for word in words:
            start, end = float(word['start']), float(word['end'])
            if not 0 <= start < end <= length + .1:
                raise ValueError('Word timing outside measured narration')
            timeline.append({'start': offset+start, 'end': offset+min(end, length),
                             'word': word['word'].strip(), 'chapter': chapter})
        offset += length
    if not timeline:
        raise ValueError('Cannot synchronize images without word timings')
    shots = []
    for index in range(math.ceil(total/INTERVAL)):
        start, end = index*INTERVAL, min((index+1)*INTERVAL, total)
        spoken = [word for word in timeline if word['end'] > start and word['start'] < end]
        # Silence keeps the preceding narrated event; do not reveal a future event early.
        previous = [word for word in timeline if word['end'] <= start]
        anchor = spoken or [max(previous, key=lambda word: word['end']) if previous else timeline[0]]
        chapter = max(set(word['chapter'] for word in anchor),
                      key=lambda c: sum(max(0, min(end, word['end'])-max(start, word['start']))
                                        for word in anchor if word['chapter'] == c))
        shots.append({'index': index, 'start': start, 'duration': end-start,
            'chapter': chapter, 'chapters': sorted({word['chapter'] for word in anchor}),
            'narration': ' '.join(word['word'] for word in anchor),
            'seed': 1700+index})
    return {'duration_seconds': total, 'image_interval_seconds': INTERVAL,
        'style': w.VISUAL_STYLE_ID, 'alignment': 'measured-word-timestamps', 'shots': shots}


def storyboard(root=ROOT, ask=None, pause=None):
    """Create concrete visual prompts AFTER narration timing, never from outline beats."""
    import time
    ask = ask or w.request_groq
    pause = pause or time.sleep
    story = json.loads((root/'story.json').read_text())
    plan = json.loads((root/'plan.json').read_text())
    character = story.get('character_description', '').strip()
    if not character:
        raise ValueError('Visual synchronization needs a character description')
    character = ' '.join(character.split()[:24])
    shots = plan['shots']
    for begin in range(0, len(shots), 8):
        if begin:
            pause(60)
        batch = shots[begin:begin+8]
        properties = {f"shot_{shot['index']:03}": {'type': 'string'} for shot in batch}
        schema = {'type': 'object', 'properties': properties,
                  'required': list(properties), 'additionalProperties': False}
        chapters = {chapter for shot in batch
                    for chapter in shot.get('chapters', [shot['chapter']])}
        context = {str(chapter): story['scenes'][chapter]['narration'] for chapter in chapters}
        from human_history import direction
        prompt = f"""Storyboard this narrated video. {direction(story)} Return one image prompt per exact shot key.
Each shot is a measured {INTERVAL}-second narration window (the final shot may be shorter). Depict ONLY the concrete action, location,
objects and emotion being spoken in that window. Chapter text resolves pronouns and continuity only;
NEVER illustrate a later or earlier chapter event in place of the current window.
During a pause, continue the preceding scene rather than showing a future event early.
For abstract reflection or dialogue, show the current character in the current physical scene.
No metaphorical mountains, gardens or random scenery unless literally present in that event.
Keep recurring characters and clothes consistent. Main character design: {character}.
For second-person narration, you/your refers to the protagonist named {story.get('protagonist_name', 'in the story')}.
Depict that character externally, naming them in the prompt; never draw a narrator or a literal viewer camera.
Each prompt MUST be 12-22 English words: subject and concrete action FIRST, then relevant objects
and location. Identify the active character, physical action, important objects, and visible emotion
when the narration supplies them. Describe one drawable composition with a detailed, accurate setting.
If the action concerns an object, name that object in the opening phrase and keep it fully visible;
never replace the object with the person holding it or a minor component such as its chain.
Use natural poses and facial expressions. Include other people only when narrated.
Do not invent scenery, props, weather, clothing, or characters to add visual interest.
Name the active character instead of using a pronoun when chapter context identifies them.
When a window crosses events, depict the event occupying most of its spoken time; never combine different times or places.
Use adjacent spoken words only to resolve a cut-off sentence, pronoun or location, never to jump ahead.
Do not put style, camera lists, narration text, typography or character design into the prompt;
the renderer adds character design and hand-drawn cartoon styling. Do not replace specific objects with generic ones.
For explainers, illustrate the physical mechanism rather than adding the mascot to every frame.
Use a white background for an isolated explanatory object; use a concrete place for an environmental action.
Never merge different time periods, add modern equipment to prehistoric scenes, or repeat one camp background everywhere.
Chapter context: {json.dumps(context)}
Exact shot windows: {json.dumps([{'key': f"shot_{shot['index']:03}", 'start_seconds': shot['start'], 'duration_seconds': shot['duration'], 'end_seconds': shot['start']+shot['duration'], 'primary_chapter': shot['chapter'], 'spoken': shot['narration'], 'previous_spoken': shots[shot['index']-1]['narration'] if shot['index'] else '', 'next_spoken': shots[shot['index']+1]['narration'] if shot['index']+1 < len(shots) else ''} for shot in batch])}
"""
        result = ask('chat/completions', {'model': os.getenv('STORY_MODEL', 'openai/gpt-oss-120b'),
            'messages': [{'role': 'user', 'content': prompt}],
            'response_format': {'type': 'json_schema', 'json_schema': {'name': 'aligned_shots',
                'strict': True, 'schema': schema}}, 'reasoning_effort': 'low',
            'temperature': .2, 'max_completion_tokens': 1800})
        choice = result['choices'][0]
        if choice.get('finish_reason') == 'length':
            raise RuntimeError('Storyboard response truncated')
        values = json.loads(choice['message']['content'])
        if set(values) != set(properties):
            raise ValueError('Storyboard must cover every narration window exactly once')
        for shot in batch:
            visual = values[f"shot_{shot['index']:03}"]
            if not isinstance(visual, str) or not 5 <= len(visual.split()) <= 30:
                raise ValueError('Visual prompt must be a concise concrete scene')
            shot['visual_action'] = visual
            shot['prompt'] = visual + '. Character: ' + character
        # Private local checkpoint; do not log unpublished narration or prompts.
        (root/'plan.json').write_text(json.dumps(plan, indent=2))
        print(json.dumps({'aligned_shots': min(begin+8, len(shots)), 'total': len(shots)}), flush=True)
    plan['storyboard_verified'] = True
    (root/'plan.json').write_text(json.dumps(plan, indent=2))
    return plan


def duration_action(total):
    """Use measured speech; reserve tempo changes for barely excessive audio."""
    if MIN_DURATION <= total <= MAX_DURATION:
        return 'accept'
    if MAX_DURATION < total <= 895 * MAX_NATURAL_TEMPO:
        return 'tempo'
    return 'rewrite'


def narration_digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def rewrite_for_duration(story, total, lengths, ask=None):
    """Rewrite only the chapters needed to move measured speech toward the safe band."""
    ask = ask or w.request_groq
    # Aim for the nearest comfortable edge; this limits how many chapters need
    # new speech when the script is only a little outside the allowed range.
    target = PREFERRED_MAX if total > MAX_DURATION else PREFERRED_MIN
    # Spread a large adjustment across chapters so no one chapter loses its story beat.
    candidates = list(range(len(lengths)))
    candidates.sort(key=lambda i: lengths[i], reverse=total > MAX_DURATION)
    needed = abs(total - target)
    selected = []
    for index in candidates:
        selected.append(index)
        if sum(lengths[i] for i in selected) * .35 >= needed:
            break
    selected.sort()
    selected_seconds = sum(lengths[i] for i in selected)
    ratio = max(.65, min(1.45, 1 + (target-total)/selected_seconds))
    updates = {}
    for begin in range(0, len(selected), 5):
        group = selected[begin:begin+5]
        keys = [f'chapter_{i+1:02}' for i in group]
        schema = {'type': 'object', 'properties': {key: {'type': 'string'} for key in keys},
                  'required': keys, 'additionalProperties': False}
        context = [{'chapter': i+1, 'previous': story['scenes'][i-1]['narration'][-250:] if i else '',
                    'current': story['scenes'][i]['narration'],
                    'next': story['scenes'][i+1]['narration'][:250] if i+1 < len(lengths) else ''}
                   for i in group]
        from content_strategy import narration_direction
        prompt = (narration_direction(story) + f' Story bible: {story.get("story_bible", "")}. '
                  f'Rewrite only these chapters of the existing narrated video to make spoken narration '
                  f'{"shorter" if ratio < 1 else "longer"}. Preserve each chapter event, character continuity, '
                  f'natural dialogue, opening hook, and ending. Keep the final like, comment, and subscribe CTA '
                  f'unchanged at the end of chapter 20 if present. Add meaningful explanation or action when expanding; '
                  f'never pad or repeat. Original measured duration is {total:.1f}s; target is about {target:.0f}s. '
                  f'Aim for approximately {ratio:.2f} times the current word count in each returned chapter. '
                  f'Return only JSON with exactly these keys: {keys}. Context: {json.dumps(context)}')
        result = ask('chat/completions', {'model': os.getenv('STORY_MODEL', 'openai/gpt-oss-120b'),
            'messages': [{'role': 'user', 'content': prompt}],
            'response_format': {'type': 'json_schema', 'json_schema': {'name': 'duration_rewrite',
                'strict': True, 'schema': schema}}, 'reasoning_effort': 'low',
            'temperature': .35, 'max_completion_tokens': 3000})
        choice = result['choices'][0]
        if choice.get('finish_reason') == 'length':
            raise RuntimeError('Duration rewrite response was truncated')
        values = json.loads(choice['message']['content'])
        if set(values) != set(keys) or not all(isinstance(v, str) and v.strip() for v in values.values()):
            raise ValueError('Duration rewrite returned incomplete chapters')
        updates.update({i: values[f'chapter_{i+1:02}'].strip() for i in group})
    revised = json.loads(json.dumps(story))
    from human_history import PROFILE as HISTORY_PROFILE, CTA as HISTORY_CTA
    cta = HISTORY_CTA if story.get('content_profile') == HISTORY_PROFILE else w.FINAL_CTA
    for index, text in updates.items():
        if index == len(lengths)-1 and story['scenes'][-1]['narration'].endswith(cta):
            # The CTA is application-owned text, not material for the model to revise.
            text = text.split(cta.strip().split('?')[0], 1)[0].rstrip() + cta
        revised['scenes'][index]['narration'] = text
    validate_engagement(revised)
    w.validate_story(revised)
    return revised, selected


def measure_chapters(story, root):
    lengths, word_lists, audios = [], [], []
    for index, scene in enumerate(story['scenes']):
        audio = root/f'narration-{index:02}.wav'
        words_path = root/f'words-{index:02}.json'
        digest_path = root/f'narration-{index:02}.sha256'
        digest = narration_digest(scene['narration'])
        if not digest_path.exists() or digest_path.read_text() != digest or not audio.exists():
            audio.unlink(missing_ok=True)
            words_path.unlink(missing_ok=True)
        if not audio.exists():
            w.make_narration(scene['narration'], audio)
            digest_path.write_text(digest)
        length = w.duration(audio)
        if not words_path.exists():
            words_path.write_text(json.dumps(w.transcribe(audio)))
        words = json.loads(words_path.read_text())
        w.aligned_subtitles([words], [length], root/'chapter-check.srt')
        lengths.append(length)
        word_lists.append(words)
        audios.append(audio)
        print(json.dumps({'chapter': index+1, 'seconds': length, 'audio_passed': True}), flush=True)
    return lengths, word_lists, audios


def adjust_tempo(root, audios, lengths, word_lists, total):
    # Reach a small safety margin; never exceed a four-percent speed change.
    target = min(895, total / 1.005)
    factor = total / target
    if factor > MAX_NATURAL_TEMPO:
        raise ValueError('Required tempo adjustment exceeds natural-speech limit')
    changed_lengths, changed_words = [], []
    for index, (audio, old_length, words) in enumerate(zip(audios, lengths, word_lists)):
        adjusted = audio.with_name(audio.stem + '-adjusted.wav')
        w.shell('ffmpeg', '-y', '-i', str(audio), '-filter:a', f'atempo={factor:.8f}',
                '-c:a', 'pcm_s16le', str(adjusted))
        new_length = w.duration(adjusted)
        scale = new_length / old_length
        scaled = [{**word, 'start': float(word['start'])*scale,
                   'end': min(float(word['end'])*scale, new_length)} for word in words]
        w.aligned_subtitles([scaled], [new_length], root/'chapter-check.srt')
        adjusted.replace(audio)
        (root/f'words-{index:02}.json').write_text(json.dumps(scaled))
        changed_lengths.append(new_length)
        changed_words.append(scaled)
    return changed_lengths, changed_words, factor


def prepare(story=None, root=ROOT):
    root.mkdir(parents=True, exist_ok=True)
    story = story or json.loads(Path(os.getenv('STORY_FILE', str(root/'story.json'))).read_text())
    w.validate_story(story)
    print(json.dumps({'story_words': sum(len(s['narration'].split()) for s in story['scenes'])}), flush=True)
    (root/'story.json').write_text(json.dumps(story, indent=2))
    original = None
    for attempt in range(MAX_CORRECTIONS + 1):
        lengths, word_lists, audios = measure_chapters(story, root)
        total = sum(lengths)
        if original is None:
            original = total
            print(json.dumps({'original_narration_seconds': round(original, 3)}), flush=True)
        action = duration_action(total)
        if action == 'accept':
            break
        if attempt == MAX_CORRECTIONS:
            raise RuntimeError(f'Narration duration recovery failed after {MAX_CORRECTIONS} attempts: '
                               f'original={original:.1f}s, final={total:.1f}s, required=600–900s')
        print(json.dumps({'duration_correction_attempt': attempt+1, 'seconds': round(total, 3),
                          'action': action}), flush=True)
        if action == 'tempo':
            lengths, word_lists, factor = adjust_tempo(root, audios, lengths, word_lists, total)
            print(json.dumps({'tempo_factor': round(factor, 5),
                              'adjusted_seconds': round(sum(lengths), 3)}), flush=True)
            # Re-measure the cached corrected audio on the next pass.
        else:
            try:
                revised, changed = rewrite_for_duration(story, total, lengths)
            except (RuntimeError, ValueError, KeyError, json.JSONDecodeError) as error:
                print(json.dumps({'duration_rewrite_failed': True, 'attempt': attempt+1,
                                  'error_type': type(error).__name__, 'reason': str(error)}), flush=True)
                continue
            story = revised
            (root/'story.json').write_text(json.dumps(story, indent=2))
            print(json.dumps({'rewritten_chapters': [i+1 for i in changed],
                              'story_words': sum(len(s['narration'].split()) for s in story['scenes'])}), flush=True)
    print(json.dumps({'final_narration_seconds': round(total, 3),
                      'preferred_range': PREFERRED_MIN <= total <= PREFERRED_MAX}), flush=True)
    w.aligned_subtitles(word_lists, lengths, root/'captions.srt')
    (root/'audio-list.txt').write_text(''.join(f"file '{p.name}'\n" for p in audios))
    w.shell('ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(root/'audio-list.txt'),
        '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s16le', str(root/'narration.wav'))
    plan = shot_plan(story, lengths, word_lists)
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


def render_image_with_retry(prompt, image, image_meta, shot_index):
    """Retry transient model/network faults without retrying safety or validation failures."""
    import time
    for attempt in range(3):
        try:
            w.make_image(prompt, image)
            return
        except (ConnectionError, TimeoutError, OSError) as error:
            reason = str(error).lower()
            transient = isinstance(error, (ConnectionError, TimeoutError)) or any(
                marker in reason for marker in ('timed out', 'connection', 'temporarily unavailable',
                                                 'too many requests', '429', '502', '503', '504'))
            if not transient or attempt == 2:
                raise
            image.unlink(missing_ok=True)
            image_meta.unlink(missing_ok=True)
            print(json.dumps({'shot': shot_index, 'image_render_retry': attempt+1,
                              'error_type': type(error).__name__}), flush=True)
            time.sleep(5 * (attempt+1))


def render_safe_scene(shot, image, image_meta):
    """Retry a rejected image, then use a family-friendly prompt with fresh seeds."""
    from image_cpu import ImageSafetyRejected
    base_seed = int(os.environ.get('IMAGE_SEED', shot['seed']))
    action = shot.get('visual_action') or shot.get('semantic_target') or shot['prompt']
    safer_prompt = (
        'Family-friendly editorial illustration of an ordinary everyday scene. '
        'All people are fully clothed adults in modest everyday clothing. '
        'Show the following action without nudity, sexual content, injury, blood or violence: '
        + action + '. Use a neutral wide composition and focus on the everyday objects and task.')
    try:
        seed_offset = 0
        for phase, (prompt, attempts) in enumerate(((shot['prompt'], 2), (safer_prompt, 5))):
            if phase:
                print(json.dumps({'shot': shot['index'], 'image_prompt_rewritten': True,
                                  'reason': 'two safety-rejected candidates'}), flush=True)
            for attempt in range(attempts):
                os.environ['IMAGE_SEED'] = str(base_seed + (seed_offset+attempt)*1000)
                try:
                    render_image_with_retry(prompt, image, image_meta, shot['index'])
                    return
                except ImageSafetyRejected:
                    image.unlink(missing_ok=True)
                    image_meta.unlink(missing_ok=True)
                    print(json.dumps({'shot': shot['index'], 'image_safety_rejected': True,
                                      'prompt_phase': phase+1, 'attempt': attempt+1}), flush=True)
                    if phase == 1 and attempt == attempts-1:
                        raise RuntimeError(f"Image safety rejected all {seed_offset+attempts} candidates for {shot['index']}") from None
            seed_offset += attempts
    finally:
        os.environ['IMAGE_SEED'] = str(base_seed)


def render_safe_thumbnail(prompt, source):
    """Apply scene image recovery to the final thumbnail."""
    from image_cpu import metadata_path
    render_safe_scene({'index': 'thumbnail', 'seed': int(os.environ.get('IMAGE_SEED', '9931')),
                       'prompt': prompt, 'visual_action': prompt}, source, metadata_path(source))


def refine_visual_plan(root=ROOT):
    """Keep each physical action dominant; omit the heroine from object-only shots."""
    import re
    story = json.loads((root/'story.json').read_text())
    plan = json.loads((root/'plan.json').read_text())
    character = ' '.join(story['character_description'].split()[:24])
    name = story.get('protagonist_name')
    if not name:
        candidates = re.findall(r'(?<=[ ,])([A-Z][a-z]{2,})(?=[, .])', story['scenes'][0]['narration'])
        name = next((n for n in candidates if n not in ('The', 'This', 'With', 'Later', 'Below')), None)
    if not name:
        raise ValueError('Protagonist name is needed for scene-specific character inclusion')
    for shot in plan['shots']:
        action = shot['visual_action'].strip().rstrip('.')
        main = bool(re.search(r'\b'+re.escape(name)+r'\b', action, re.I))
        group = bool(re.search(r'\b(workers|crew|team|locals|people|crowd|volunteers)\b', action, re.I))
        group = group or bool(main and re.search(r'\b(boss|mayor|mother|father|brother|coworker)\b|\bMr\.', action, re.I))
        human = bool(re.search(
            r'\b(man|woman|worker|coworker|engineer|mayor|boss|forecaster|roommate|manager|'
            r'humans|human|hunter|gatherer|child|children|client|friend|neighbor|colleague|mentor|partner|mother|father|brother|sister|'
            r'son|daughter)\b|\bMr\.', action, re.I))
        # Storyboard names can differ from the outline's protagonist spelling.
        # A named person performing an action must never get a "no people" prompt.
        human = human or bool(re.search(
            r'\b[A-Z][a-z]{2,}\s+(?:at|on|in|showing|handing|holding|typing|'
            r'listening|staring|raising|smiling|drafting|presenting|pointing|'
            r'walking|speaking|standing|sitting|looking|reading|writing)\b', action))
        focus = 'group' if group else ('person' if main or human else 'object')
        composition = 'wide scene showing multiple people together, ' if group else 'wide scene, '
        shot['prompt'] = composition + action
        if main:
            shot['prompt'] += '. Main character: ' + character
        shot['prompt'] += '. Keep the narrated action prominent. ' + w.VISUAL_STYLE
        shot['focus'] = focus
        shot['negative_prompt'] = 'portrait, headshot, close-up face, face filling frame'
        from human_history import PROFILE as HISTORY_PROFILE, visual_prompt, image_negative
        if story.get('content_profile') == HISTORY_PROFILE:
            shot['prompt'] = visual_prompt(action, name, people=focus != 'object')
            shot['negative_prompt'] = image_negative(action)
        # Heuristic focus labels must not erase a narrated person with an unfamiliar name or action.
        if focus == 'group':
            shot['negative_prompt'] += ', solo, one person alone'
        shot['semantic_target'] = action
    # Competing events catch a plausible-looking image from the wrong story moment.
    for index, shot in enumerate(plan['shots']):
        shot['semantic_alternatives'] = [other['semantic_target']
            for other in plan['shots'][max(0, index-2):index+3] if other is not shot]
    plan['storyboard_verified'] = True
    plan['style'] = w.VISUAL_STYLE_ID
    plan['visual_review'] = {'passed': False, 'phase': 'corrected-object-and-group-render-required'}
    plan['scene_composition_version'] = 2
    (root/'plan.json').write_text(json.dumps(plan, indent=2))
    print(json.dumps({'scene_plan_refined': True, 'shots': len(plan['shots'])}), flush=True)
    return plan


def generate_shard(shard, root=ROOT, count=SHARDS):
    from scene_check import check_scene, scene_signature
    from image_cpu import image_config, metadata_path
    plan = json.loads((root/'plan.json').read_text())
    if plan.get('image_interval_seconds') != INTERVAL:
        raise RuntimeError('Saved visual plan uses a different image interval; prepare a new run')
    if not 0 <= shard < count:
        raise ValueError(f'Image shard must be between 0 and {count-1}')
    if not plan.get('storyboard_verified') or not all(s.get('prompt') for s in plan['shots']):
        raise RuntimeError('Narration-aligned storyboard is required before image generation')
    if plan.get('style') != w.VISUAL_STYLE_ID:
        raise RuntimeError('Scene plan must use the current cinematic story style')
    if plan.get('scene_composition_version') != 2:
        raise RuntimeError('Scene-specific object and group composition is required')
    shots = [s for s in plan['shots'] if s['index']%count == shard]
    for shot in shots:
        index = shot['index']
        image, clip = root/f'shot-{index:03}.png', root/f'shot-{index:03}.mp4'
        check = root/f'shot-{index:03}.qa.json'
        image_meta = metadata_path(image)
        signature = scene_signature(shot)
        if image.exists():
            try:
                previous_check = json.loads(check.read_text())
            except (FileNotFoundError, json.JSONDecodeError):
                previous_check = {}
            if previous_check.get('source_signature') != signature:
                image.unlink()
                image_meta.unlink(missing_ok=True)
                clip.unlink(missing_ok=True)
        expected = image_config() if os.getenv('IMAGE_BACKEND', 'cpu') == 'cpu' else None
        if image.exists() and expected:
            try:
                cached = json.loads(image_meta.read_text())
            except (FileNotFoundError, json.JSONDecodeError):
                cached = {}
            if any(cached.get(field) != getattr(expected, field) for field in
                   ('model', 'revision', 'width', 'height', 'steps', 'guidance_scale',
                    'reference_sha256', 'reference_strength', 'reference_mode', 'reference_style')):
                image.unlink()
                image_meta.unlink(missing_ok=True)
                clip.unlink(missing_ok=True)
        os.environ['IMAGE_NEGATIVE_PROMPT'] = shot.get('negative_prompt', '')
        for attempt in range(3):
            os.environ['IMAGE_SEED'] = str(shot['seed']+attempt*10000)
            if not image.exists():
                clip.unlink(missing_ok=True)
                render_safe_scene(shot, image, image_meta)
            report = check_scene(image, shot)
            if report['passed']:
                report['source_signature'] = signature
                if expected:
                    report['image_generation'] = json.loads(image_meta.read_text())
                check.write_text(json.dumps(report))
                if report.get('semantic_match') is False:
                    print(json.dumps({'shot': index, 'semantic_review': 'mismatch',
                                      'scene_score': report['scene_score'],
                                      'alternative_score': report['alternative_score']}), flush=True)
                elif report.get('semantic_review_error'):
                    print(json.dumps({'shot': index, 'semantic_review': 'unavailable',
                                      'error_type': report['semantic_review_error']}), flush=True)
                break
            image.unlink()
            image_meta.unlink(missing_ok=True)
            clip.unlink(missing_ok=True)
            print(json.dumps({'shot': index, 'visual_check_passed': False,
                              'method': report.get('method'), 'detail_score': report.get('detail_score'),
                              'attempt': attempt+1}), flush=True)
        else:
            raise RuntimeError(f'Shot {index} failed image detail check after three CPU renders')
        if not clip.exists():
            picture_clip(image, shot['duration'], clip)
        print(json.dumps({'shard': shard, 'shot': index+1, 'total': len(plan['shots']), 'rendered': True,
            'visual_check_passed': report['passed']}), flush=True)


def validate_engagement(story):
    import re
    for scene in story['scenes'][:-1]:
        if re.search(r'\bsubscribe\b', scene['narration'], re.IGNORECASE):
            raise ValueError('Premature call to action before the final chapter')
    ending = story['scenes'][-1]['narration'].lower()
    if not all(re.search(r'\b'+word+r'\b', ending) for word in ('like', 'comment', 'subscribe')):
        raise ValueError('Closing narration must request like, comment, and subscribe')
    if not story.get('character_description', '').strip():
        raise ValueError('Fresh story requires a consistent character description')


def mix_audio(voice, music, target, seconds):
    """Normalize music first and use mild ducking; verify its actual contribution."""
    import numpy as np
    import subprocess
    bed = target.with_name('music-bed.wav')
    w.shell('ffmpeg', '-y', '-i', str(voice), '-stream_loop', '-1', '-i', str(music),
        '-filter_complex',
        '[0:a]loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,asplit=2[voice][side];'
        '[1:a]loudnorm=I=-27:TP=-3:LRA=7,aresample=48000[music];'
        '[music][side]sidechaincompress=threshold=0.08:ratio=2:attack=100:release=700:mix=0.35,asplit=2[bed][check];'
        '[voice][bed]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95:level=0[a]',
        '-map', '[a]', '-t', str(seconds), '-ac', '2', '-c:a', 'pcm_s16le', str(target),
        '-map', '[check]', '-t', str(seconds), '-ac', '2', '-c:a', 'pcm_s16le', str(bed))
    def rms_db(path):
        raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path),
            '-ac', '1', '-ar', '8000', '-f', 'f32le', 'pipe:1'])
        audio = np.frombuffer(raw, dtype='<f4')
        if not len(audio) or not np.isfinite(audio).all():
            raise RuntimeError('Invalid audio samples')
        rms = float(np.sqrt(np.mean(audio**2)))
        return 20*math.log10(max(rms, 1e-12))
    bed_db, mix_db = rms_db(bed), rms_db(target)
    gap = mix_db-bed_db
    if not -40 < bed_db < -18 or not 5 < gap < 22:
        raise RuntimeError(f'Music mix is inaudible or too loud: bed={bed_db:.1f}dB, gap={gap:.1f}dB')
    return {'music_bed_rms_db': round(bed_db, 2), 'mix_rms_db': round(mix_db, 2),
        'music_gap_db': round(gap, 2), 'music_audibility_passed': True}


def finish(root=ROOT):
    from PIL import Image, ImageOps
    from music_cpu import generate
    from scene_check import scene_signature
    plan = json.loads((root/'plan.json').read_text())
    scene_reports = [json.loads((root/f"shot-{s['index']:03}.qa.json").read_text()) for s in plan['shots']]
    if not scene_reports or not all(report.get('passed') and report.get('required') and
            report.get('source_signature') == scene_signature(shot)
            for shot, report in zip(plan['shots'], scene_reports)):
        raise RuntimeError('Every image must pass current narration-aligned scene checks before assembly')
    clips = [root/f"shot-{s['index']:03}.mp4" for s in plan['shots']]
    if not all(p.exists() for p in clips):
        raise RuntimeError('Not every seven-second image clip exists')
    for shot, clip in zip(plan['shots'], clips):
        if abs(w.duration(clip)-shot['duration']) > .04:
            raise RuntimeError('Shot timing differs from the global seven-second plan')
    (root/'clips.txt').write_text(''.join(f"file '{p.name}'\n" for p in clips))
    w.shell('ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(root/'clips.txt'), '-c', 'copy', str(root/'joined.mp4'))
    if not (root/'music.audio').exists():
        generate(root/'music.audio')
    audio_report = mix_audio(root/'narration.wav', root/'music.audio', root/'mixed.wav', plan['duration_seconds'])
    w.shell('ffmpeg', '-y', '-i', str(root/'joined.mp4'), '-i', str(root/'mixed.wav'),
        '-vf', f"subtitles={root/'captions.srt'}:force_style='FontName=DejaVu Sans,FontSize=22,Outline=2,MarginV=35'",
        '-map', '0:v', '-map', '1:a', '-t', str(plan['duration_seconds']), '-ar', '48000',
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '21', '-c:a', 'aac', '-movflags', '+faststart', str(root/'video.mp4'))
    metadata = w.check_video(root/'video.mp4')
    story = json.loads((root/'story.json').read_text())
    os.environ['IMAGE_NEGATIVE_PROMPT'] = ''
    os.environ['IMAGE_SEED'] = '9931'
    thumbnail_prompt = (story['thumbnail_prompt'] + '. Main character: ' +
        story['character_description'] + '. Make a single topic-specific hand-drawn cartoon thumbnail '
        'with the protagonist prominent and a clear contrasting background or supporting characters. '
        'No title text, labels, numbers, arrows, or interface elements.')
    from human_history import PROFILE as HISTORY_PROFILE, visual_prompt, image_negative
    if story.get('content_profile') == HISTORY_PROFILE:
        thumbnail_prompt = visual_prompt(story['thumbnail_prompt'], story['protagonist_name'], thumbnail=True)
        os.environ['IMAGE_NEGATIVE_PROMPT'] = image_negative(story['thumbnail_prompt'])
    render_safe_thumbnail(thumbnail_prompt, root/'thumbnail-source.png')
    image = ImageOps.fit(Image.open(root/'thumbnail-source.png').convert('RGB'), (1280, 720))
    from human_history import PROFILE as HISTORY_PROFILE
    if story.get('content_profile') == HISTORY_PROFILE:
        from thumbnail_style import add_caption
        add_caption(image, story['thumbnail_text'])
    image.save(root/'thumbnail.jpg', quality=92)
    if (root/'thumbnail.jpg').stat().st_size >= 2*1024*1024:
        raise RuntimeError('Thumbnail exceeds size limit')
    image_models = {r.get('image_generation', {}).get('model') for r in scene_reports}
    if os.getenv('IMAGE_BACKEND', 'cpu') == 'cpu' and image_models != {os.getenv('CPU_IMAGE_MODEL', 'segmind/SSD-1B')}:
        raise RuntimeError(f'Image model mismatch across rendered shots: {image_models}')
    report = {'render_passed': True, 'duration_seconds': float(metadata['format']['duration']),
        'width': 1920, 'height': 1080, 'images': len(clips), 'image_interval_seconds': INTERVAL,
        'style': w.VISUAL_STYLE_ID, 'privacy': 'private', 'voice': 'Kokoro am_michael',
        'music': 'Magenta MusicRNN', 'image_model': next(iter(image_models)),
        'audio_validation': audio_report, 'timeline_verified': True, 'storyboard_verified': plan.get('storyboard_verified', False),
        'alignment': plan.get('alignment'), 'scene_composition_version': plan.get('scene_composition_version'),
        'semantic_checked_images': sum(r.get('required', False) for r in scene_reports),
        'semantic_review_mismatches': sum(r.get('semantic_match') is False for r in scene_reports),
        'semantic_review_unavailable': sum(bool(r.get('semantic_review_error')) for r in scene_reports)}
    (root/'validation.json').write_text(json.dumps(report))
    print(json.dumps(report), flush=True)
    return report


def render_complete(story, root):
    prepare(story, root)
    storyboard(root)
    refine_visual_plan(root)
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
    print(json.dumps({'check': 'Private Drive store', 'passed': True}), flush=True)
    if os.getenv('GENERATE_FRESH_STORY') == 'true':
        if os.getenv('STORY_FILE'):
            raise RuntimeError('Fresh daily stories cannot use STORY_FILE')
        if store.load(f'runs/{run_id()}/state.json', {}).get('phase') in ('upload_started', 'uploaded', 'complete', 'published', 'verified_private'):
            raise RuntimeError('Run already uploaded; use cleanup-only recovery')
        history = store.load('history.json', [])
        story = w.make_story(run_id(), history[-20:])
        validate_engagement(story)
        (ROOT/'story.json').write_text(json.dumps(story, indent=2))
        print(json.dumps({'fresh_story_ready': True, 'title': story['title'],
            'words': sum(len(s['narration'].split()) for s in story['scenes'])}), flush=True)
        return
    file_id = store.find(os.getenv('PRIVATE_STORY_KEY', 'inputs/ghibli-long-story.json'))
    if not file_id:
        raise RuntimeError('Private story input is not configured')
    store.download(file_id, ROOT/'story.json')
    story = w.validate_story(json.loads((ROOT/'story.json').read_text()))
    print(json.dumps({'private_story_accessible': True,
        'words': sum(len(s['narration'].split()) for s in story['scenes'])}), flush=True)


def save_preparation():
    store = w.Store()
    key = f'runs/{run_id()}/state.json'
    if store.load(key, {}).get('phase') in ('upload_started', 'uploaded', 'complete', 'published', 'verified_private'):
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
    if plan.get('image_interval_seconds') != INTERVAL:
        raise RuntimeError('Saved visual plan uses a different image interval; prepare a new run')
    if not 0 <= shard < SHARDS:
        raise ValueError(f'Image shard must be between 0 and {SHARDS-1}')
    for shot in plan['shots']:
        if shot['index']%SHARDS == shard:
            for ext in ('png', 'mp4', 'qa.json'):
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
            raise RuntimeError('Saved seven-second clip missing')
        store.download(file_id, ROOT/name)
        qa_name = f"shot-{shot['index']:03}.qa.json"
        qa_id = store.find(f'runs/{run_id()}/{qa_name}')
        if not qa_id:
            raise RuntimeError('Visual-check record missing')
        store.download(qa_id, ROOT/qa_name)


def upload():
    report = json.loads((ROOT/'validation.json').read_text())
    if not report.get('render_passed') or report.get('image_interval_seconds') != INTERVAL or not report.get('storyboard_verified'):
        raise RuntimeError('New-format render has not passed validation')
    w.check_video(ROOT/'video.mp4')
    store, key = w.Store(), f'runs/{run_id()}/state.json'
    if store.load(key, {}).get('phase') in ('upload_started', 'uploaded', 'complete', 'published', 'verified_private'):
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
    history.append({'title': story['title'], 'format': story.get('format'),
        'content_pillar': story.get('content_pillar'), 'content_profile': story.get('content_profile'),
        'hash': digest, 'run': run_id(), 'video_id': state['video_id']})
    store.save('history.json', history)
    store.save('last-private-test.json', {'passed': True, 'run': run_id(),
        'video_id': state['video_id'], 'validation': report, 'processing_status': state['processing_status']})
    print(json.dumps({'private_test_passed': True, 'video_id': state['video_id'], **report}), flush=True)


if __name__ == '__main__':
    command = sys.argv[1]
    shard = int(sys.argv[2]) if len(sys.argv)>2 else 0
    actions = {'init-input': init_input, 'stage-story': stage_story, 'prepare': prepare, 'restore-preparation': restore_preparation, 'refine-plan': refine_visual_plan, 'storyboard': storyboard, 'save-preparation': save_preparation,
        'restore-images': lambda: restore_preparation(True), 'generate-shard': lambda: generate_shard(shard),
        'save-shard': lambda: save_shard(shard), 'restore-clips': restore_clips,
        'finish': finish, 'upload': upload}
    try:
        actions[command]()
    except Exception as error:
        print(json.dumps({'command': command, 'passed': False, 'error_type': type(error).__name__,
            'http_status': getattr(getattr(error, 'resp', None), 'status', None),
            'reason': str(error) if isinstance(error, (RuntimeError, ValueError)) else type(error).__name__}), flush=True)
        if command in ('prepare', 'generate-shard', 'finish'):
            raise
        raise SystemExit(1)
