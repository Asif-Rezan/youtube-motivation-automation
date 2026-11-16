"""Generate an original wildlife simulation video, soundtrack and thumbnail."""
import argparse
from dataclasses import replace
import json
import math
from pathlib import Path
import subprocess
import tempfile
import wave

import numpy as np

from .editing import paint_cue, scene_edit, zoom_frame
from .episodes import EPISODES, PREVIEW
from .visuals import frames
from .thumbnail import episode_cue, render_science_thumbnail, render_thumbnail
from .metadata import thumbnail_hook


FPS = 24
FULL_SIZE = (3840,2160)
PREVIEW_SIZE = (1280,720)
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


def music_bed(target, seconds, timeline=()):
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
    rng = np.random.default_rng(221)
    for entry in timeline:
        edit = entry.get('edit', {})
        if not edit:
            continue
        start = max(0, round((entry['start'] + edit['at'] - .42)*RATE))
        count = min(length-start, round(1.25*RATE))
        if count <= 0:
            continue
        t = np.arange(count,dtype=np.float32)/RATE
        signal[start:start+count] *= 1 - .55*np.sin(np.pi*t/1.25)**2
        sweep = np.sin(math.tau*(195*t - 48*t*t))
        texture = rng.uniform(-.25,.25,count)
        signal[start:start+count] += .055*(sweep+texture)*np.sin(np.pi*t/1.25)**4
    fade = min(length//2, RATE)
    if fade:
        signal[:fade] *= np.linspace(0,1,fade)
        signal[-fade:] *= np.linspace(1,0,fade)
    with wave.open(str(target),'wb') as output:
        output.setparams((1,2,RATE,0,'NONE',''))
        output.writeframes((signal*32767).astype('<i2').tobytes())


def encode_visuals(scene, seconds, size, target, *, edit=None, opening=None, **art):
    width, height = size
    command = ['ffmpeg','-v','error','-y','-f','rawvideo','-pixel_format','rgb24',
               '-video_size',f'{width}x{height}','-framerate',str(FPS),'-i','pipe:0',
               '-an','-c:v','libx264','-preset','fast','-threads','4','-crf','18',
               '-pix_fmt','yuv420p',str(target)]
    domain = art.pop('domain','wildlife')
    def render_frames(beat, length, fps, options):
        if domain == 'wildlife':
            return frames(size,beat,length,fps,**options)
        from .science_visuals import science_frames
        return science_frames(size,beat,length,fps,domain=domain,**options)

    before = None
    if opening is not None:
        scene = replace(scene,camera=opening.camera)
        before = next(render_frames(opening,1,1,{**art,'disclose':False}))
    use_shot_changes = seconds >= 20
    with subprocess.Popen(command, stdin=subprocess.PIPE) as proc:
        for index, frame in enumerate(render_frames(scene,seconds,FPS,art)):
            elapsed = index/FPS
            showing_comparison = before is not None and edit['at'] <= elapsed < edit['at'] + edit['duration']
            if use_shot_changes and not showing_comparison:
                frame = zoom_frame(frame,elapsed/seconds)
            paint_cue(frame,edit,elapsed,before)
            proc.stdin.write(frame.tobytes())
        proc.stdin.close()
        if proc.wait():
            raise RuntimeError(f'Visual encoding failed for {scene.label}')


def video_size(path):
    data = subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0',
                                    '-show_entries','stream=width,height','-of','json',str(path)])
    video = json.loads(data)['streams'][0]
    return video['width'], video['height']


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
    for index, beat in enumerate(beats):
        speech = len(beat.narration.split())*60/WORDS_PER_MINUTE
        seconds = 10 if preview else math.ceil((speech+1.5)*FPS)/FPS
        timeline.append({'chapter':beat.label,'start':round(elapsed,3),
                         'seconds':seconds,'population':beat.population,'forage':beat.forage,
                         'edit':scene_edit(beats,index,seconds)})
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
    size = PREVIEW_SIZE if preview else FULL_SIZE
    artwork = {}
    if manifest is not None:
        idea = manifest['idea']
        domain = idea.get('domain','wildlife')
        if domain == 'wildlife':
            artwork = {'species':idea['species'],'habitat':idea['habitat']}
        else:
            artwork = {'domain':domain,'topic':idea['topic']}
    edit = timeline[index]['edit']
    encode_visuals(beat, seconds, size, work/f'visual-{index:02}.mp4', edit=edit,
                   opening=beats[edit['compare_to']] if 'compare_to' in edit else None, disclose=index == 0, **artwork)
    print(json.dumps({'chapter':beat.label,'rendered':True,'seconds':seconds}),flush=True)


def assemble(episode, package, timeline, work, output, preview, manifest=None):
    if any(not (work/f'{kind}-{i:02}.{suffix}').is_file()
           for kind,suffix in [('visual','mp4'),('voice','wav')] for i in range(len(timeline))):
        raise ValueError('Missing planned wildlife scene or narration artifact')
    output.mkdir(parents=True, exist_ok=True)
    _, beats, _ = plan_episode(episode,preview,manifest)
    if manifest is None:
        render_thumbnail(beats,output/'thumbnail.jpg')
    else:
        idea = manifest['idea']
        cue = episode_cue(episode)
        if idea.get('domain','wildlife') == 'wildlife':
            render_thumbnail(beats,output/'thumbnail.jpg',label=thumbnail_hook(idea),
                             species=idea['species'],habitat=idea['habitat'],cue=cue)
        else:
            render_science_thumbnail(beats,output/'thumbnail.jpg',idea,cue)
        (output/'episode-plan.json').write_text(json.dumps(manifest,indent=2)+'\n')
    for label, kind, suffix in [('video', 'visual', 'mp4'), ('voice', 'voice', 'wav')]:
        (work/f'{label}.txt').write_text(''.join(
            f"file '{kind}-{i:02}.{suffix}'\n" for i in range(len(timeline))))
    music = work/'music.wav'
    music_bed(music,sum(item['seconds'] for item in timeline),timeline)
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
    expected_size = PREVIEW_SIZE if preview else FULL_SIZE
    if video_size(target) != expected_size:
        raise RuntimeError('Rendered video resolution differs from the episode settings')
    if abs(duration(target)-sum(x['seconds'] for x in timeline)) > .12:
        raise RuntimeError('Rendered duration differs from the narration timeline')
    metadata = package.build(timeline, preview=preview)
    (output/'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    (output/'episode.json').write_text(json.dumps({
        'title':metadata['title'],'illustrative_simulation':True,'preview':preview,
        'voice':VOICE,'pitch_semitones':SEMITONES,'words_per_minute_target':WORDS_PER_MINUTE,
        'music_bpm':BPM,'resolution':list(expected_size),'chapters':timeline},indent=2))


def render(episode, output, preview=False, manifest=None):
    package, beats, timeline = plan_episode(episode, preview, manifest)
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='wildlife-',dir=output) as scratch:
        work = Path(scratch)
        render_audio(beats, timeline, work)
        for index in range(len(beats)):
            render_scene(beats, timeline, index, work, preview, manifest)
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
