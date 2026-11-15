"""Generate an original wildlife simulation video, soundtrack and thumbnail."""
import argparse
import json
import math
from pathlib import Path
import subprocess
import tempfile
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .episodes import EPISODES, PREVIEW
from .visuals import FONT, frames


ROOT = Path(__file__).resolve().parents[1]
FPS = 24
RATE = 24000
BPM = 102
VOICE = 'am_michael'
SEMITONES = -1
WORDS_PER_MINUTE = 145


def ffmpeg(*args):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', *map(str,args)], check=True)


def duration(path):
    return float(subprocess.check_output(['ffprobe','-v','error','-show_entries',
                 'format=duration','-of','csv=p=0',str(path)]))


def read_voice(pipeline, text, target):
    parts = [audio.numpy() for _,_,audio in pipeline(text, voice=VOICE, speed=1.) if audio is not None]
    if not parts:
        raise RuntimeError('Speech synthesis returned no audio')
    pcm = (np.clip(np.concatenate(parts), -1, 1)*32767).astype('<i2')
    with wave.open(str(target),'wb') as output:
        output.setparams((1,2,RATE,0,'NONE',''))
        output.writeframes(pcm.tobytes())


def music_bed(target, seconds):
    """Original plucked ostinato and soft pads. The final mix ducks against voice."""
    length = math.ceil(seconds * RATE)
    signal = np.zeros(length, dtype=np.float32)
    step = 60/BPM/2
    chords = [(45,52,57,60),(41,48,53,57),(48,55,60,64),(43,50,55,59)]
    for beat in range(math.ceil(seconds/step)):
        chord = chords[(beat//8)%len(chords)]
        note = chord[(0,2,1,3,1,2,3,2)[beat%8]] + 12
        start = round(beat * step * RATE)
        count = min(length-start, round(1.5*RATE))
        t = np.arange(count,dtype=np.float32)/RATE
        freq = 440 * 2**((note-69)/12)
        attack = np.minimum(t*180,1)
        pluck = (np.sin(t*math.tau*freq)+.21*np.sin(t*math.tau*freq*2))*attack*np.exp(-4*t)
        signal[start:start+count] += .14*pluck
        if beat%8 == 0:
            count = min(length-start,round(8*step*RATE))
            t = np.arange(count,dtype=np.float32)/RATE
            swell = np.sin(np.pi*np.arange(count)/max(round(8*step*RATE),1))**2
            for note in chord[:3]:
                freq = 440*2**((note-69)/12)
                signal[start:start+count] += .04*np.sin(t*math.tau*freq)*swell
    fade = min(length//2, RATE)
    if fade:
        signal[:fade] *= np.linspace(0,1,fade)
        signal[-fade:] *= np.linspace(1,0,fade)
    with wave.open(str(target),'wb') as output:
        output.setparams((1,2,RATE,0,'NONE',''))
        output.writeframes((signal*32767).astype('<i2').tobytes())


def encode_visuals(scene, seconds, size, target, **art):
    width, height = size
    command = ['ffmpeg','-v','error','-y','-f','rawvideo','-pixel_format','rgb24',
               '-video_size',f'{width}x{height}','-framerate',str(FPS),'-i','pipe:0',
               '-an','-c:v','libx264','-preset','fast','-threads','4','-crf','18',
               '-pix_fmt','yuv420p',str(target)]
    with subprocess.Popen(command, stdin=subprocess.PIPE) as proc:
        for frame in frames(size, scene, seconds, FPS, **art):
            proc.stdin.write(frame.tobytes())
        proc.stdin.close()
        if proc.wait():
            raise RuntimeError(f'Visual encoding failed for {scene.label}')


def thumbnail(episode, target, *, artwork=None, label='AFTER THE BOOM'):
    from PIL import ImageOps
    source = artwork or ROOT/'assets'/'wildlife'/f'{episode}.jpg'
    with Image.open(source) as original:
        image = ImageOps.fit(original.convert('RGB'),(1280,720),Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(image)
    label = label.upper()
    for size in range(143,50,-2):
        font = ImageFont.truetype(str(FONT),size)
        if draw.textlength(label,font=font) <= 1150:
            break
    draw.text((640,18), label, font=font, anchor='mt', fill='#fff5dc', stroke_width=10,
              stroke_fill='#211b18')
    image.save(target, quality=92, optimize=True)
    if target.stat().st_size >= 2 * 1024**2:
        raise RuntimeError('Thumbnail is larger than 2 MiB')


def plan_episode(episode, preview, manifest=None):
    if manifest is None:
        package, beats = EPISODES[episode]
        if preview:
            beats = PREVIEW
    else:
        from .generate import decode
        package, beats = decode(manifest,episode)
        if preview:
            raise ValueError('AI daily episodes are rendered at full length')
    package.validate()
    timeline = []
    elapsed = 0
    for beat in beats:
        speech = len(beat.narration.split())*60/WORDS_PER_MINUTE
        seconds = 10 if preview else math.ceil((speech+1.5)*FPS)/FPS
        timeline.append({'chapter':beat.label,'start':round(elapsed,3),
                         'seconds':seconds,'population':beat.population,'forage':beat.forage})
        elapsed += seconds
    if not preview and (len(beats) != 20 or not 600 <= elapsed <= 900):
        raise ValueError('A full wildlife episode needs 20 scenes and a 10–15 minute runtime')
    return package, beats, timeline


def render_audio(beats, timeline, work):
    import torch
    from kokoro import KPipeline

    work.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(2)
    speech = KPipeline(lang_code='a',device='cpu',repo_id='hexgrad/Kokoro-82M')
    raw = work/'voice-raw.wav'
    try:
        for index, (beat, entry) in enumerate(zip(beats, timeline)):
            seconds = entry['seconds']
            read_voice(speech,beat.narration,raw)
            desired = min(len(beat.narration.split())*60/WORDS_PER_MINUTE,seconds-1)
            pitch = 2**(SEMITONES/12)
            tempo = duration(raw)/(desired*pitch)
            voice = work/f'voice-{index:02}.wav'
            ffmpeg('-i',raw,'-af',f'asetrate={RATE*pitch:.7f},aresample={RATE},atempo={tempo:.7f},'
                   'highpass=f=75,adelay=300,apad','-t',f'{seconds:.6f}',voice)
    finally:
        raw.unlink(missing_ok=True)


def render_scene(beats, timeline, index, work, preview, manifest=None):
    if not 0 <= index < len(beats):
        raise ValueError('Scene index is outside the episode')
    work.mkdir(parents=True, exist_ok=True)
    beat, seconds = beats[index], timeline[index]['seconds']
    size = (1280,720) if preview else (1920,1080)
    artwork = {}
    if manifest is not None:
        idea = manifest['idea']
        artwork = {'species':idea['species'],'habitat':idea['habitat']}
    encode_visuals(beat, seconds, size, work/f'visual-{index:02}.mp4',**artwork)
    print(json.dumps({'chapter':beat.label,'rendered':True,'seconds':seconds}),flush=True)


def assemble(episode, package, timeline, work, output, preview, manifest=None):
    if any(not (work/f'{kind}-{i:02}.{suffix}').is_file()
           for kind,suffix in [('visual','mp4'),('voice','wav')] for i in range(len(timeline))):
        raise ValueError('Missing planned wildlife scene or narration artifact')
    output.mkdir(parents=True, exist_ok=True)
    if manifest is None:
        thumbnail(episode,output/'thumbnail.jpg')
    else:
        thumbnail(episode,output/'thumbnail.jpg',artwork=work/'thumbnail-art.png',
                  label=manifest['idea']['thumbnail_text'])
        (output/'episode-plan.json').write_text(json.dumps(manifest,indent=2)+'\n')
    for label, kind, suffix in [('video', 'visual', 'mp4'), ('voice', 'voice', 'wav')]:
        (work/f'{label}.txt').write_text(''.join(
            f"file '{kind}-{i:02}.{suffix}'\n" for i in range(len(timeline))))
    music = work/'music.wav'
    music_bed(music,sum(item['seconds'] for item in timeline))
    target = output/'video.mp4'
    ffmpeg('-f','concat','-safe','0','-i',work/'video.txt','-f','concat','-safe','0','-i',work/'voice.txt',
           '-i',music,'-filter_complex',
           '[1:a]loudnorm=I=-16:TP=-2:LRA=7,aresample=48000,asplit[v][sc];'
           '[2:a]volume=0.34,aresample=48000[m];[m][sc]sidechaincompress='
           'threshold=0.025:ratio=4:attack=22:release=260[bed];[v][bed]amix=inputs=2:'
           'duration=first:normalize=0,alimiter=limit=0.93[a]',
           '-map','0:v','-map','[a]','-c:v','copy','-c:a','aac','-b:a','192k',
           '-movflags','+faststart','-shortest',target)
    ffmpeg('-xerror','-i',target,'-f','null','-')
    if abs(duration(target)-sum(x['seconds'] for x in timeline)) > .12:
        raise RuntimeError('Rendered duration differs from the narration timeline')
    metadata = package.build(timeline, preview=preview)
    (output/'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    (output/'episode.json').write_text(json.dumps({
        'title':metadata['title'],'illustrative_simulation':True,'preview':preview,
        'voice':VOICE,'pitch_semitones':SEMITONES,'words_per_minute_target':WORDS_PER_MINUTE,
        'music_bpm':BPM,'chapters':timeline},indent=2))


def render(episode, output, preview=False, manifest=None):
    package, beats, timeline = plan_episode(episode, preview, manifest)
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='wildlife-',dir=output) as scratch:
        work = Path(scratch)
        render_audio(beats, timeline, work)
        for index in range(len(beats)):
            render_scene(beats, timeline, index, work, preview, manifest)
        if manifest is not None:
            from .art import make_art
            make_art(manifest,work/'thumbnail-art.png')
        assemble(episode, package, timeline, work, output, preview, manifest)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--episode',default='goat-island')
    parser.add_argument('--output',type=Path,default=Path('output/wildlife'))
    parser.add_argument('--preview',action='store_true')
    parser.add_argument('--stage',choices=('all','plan','audio','scene','assemble'),default='all')
    parser.add_argument('--work',type=Path,default=Path('output/wildlife-parts'))
    parser.add_argument('--index',type=int)
    parser.add_argument('--manifest',type=Path)
    args=parser.parse_args()
    manifest = json.loads(args.manifest.read_text()) if args.manifest else None
    package, beats, timeline = plan_episode(args.episode,args.preview,manifest)
    if args.stage == 'plan':
        print(json.dumps(list(range(len(beats)))))
    elif args.stage == 'audio':
        render_audio(beats,timeline,args.work)
    elif args.stage == 'scene':
        if args.index is None:
            parser.error('--stage scene requires --index')
        render_scene(beats,timeline,args.index,args.work,args.preview,manifest)
    elif args.stage == 'assemble':
        assemble(args.episode,package,timeline,args.work,args.output,args.preview,manifest)
    else:
        render(args.episode,args.output,args.preview,manifest)
