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


def encode_visuals(scene, seconds, size, target):
    width, height = size
    command = ['ffmpeg','-v','error','-y','-f','rawvideo','-pixel_format','rgb24',
               '-video_size',f'{width}x{height}','-framerate',str(FPS),'-i','pipe:0',
               '-an','-c:v','libx264','-preset','fast','-threads','4','-crf','18',
               '-pix_fmt','yuv420p',str(target)]
    with subprocess.Popen(command, stdin=subprocess.PIPE) as proc:
        for frame in frames(size, scene, seconds, FPS):
            proc.stdin.write(frame.tobytes())
        proc.stdin.close()
        if proc.wait():
            raise RuntimeError(f'Visual encoding failed for {scene.label}')


def thumbnail(episode, target):
    with Image.open(ROOT/'assets'/'wildlife'/f'{episode}.jpg') as original:
        image = original.convert('RGB')
    draw = ImageDraw.Draw(image)
    label = 'AFTER THE BOOM'
    font = ImageFont.truetype(str(FONT), 143)
    draw.text((640,18), label, font=font, anchor='mt', fill='#fff5dc', stroke_width=10,
              stroke_fill='#211b18')
    image.save(target, quality=92, optimize=True)
    if target.stat().st_size >= 2 * 1024**2:
        raise RuntimeError('Thumbnail is larger than 2 MiB')


def render(episode, output, preview=False):
    import torch
    from kokoro import KPipeline

    title, beats = EPISODES[episode]
    if preview:
        beats = PREVIEW
    output.mkdir(parents=True, exist_ok=True)
    thumbnail(episode,output/'thumbnail.jpg')
    size = (1280,720) if preview else (1920,1080)
    torch.set_num_threads(2)
    speech = KPipeline(lang_code='a',device='cpu',repo_id='hexgrad/Kokoro-82M')
    with tempfile.TemporaryDirectory(prefix='wildlife-',dir=output) as scratch:
        work = Path(scratch)
        timeline = []
        for index, beat in enumerate(beats):
            raw, voice = work/'voice-raw.wav', work/f'voice-{index:02}.wav'
            visual = work/f'visual-{index:02}.mp4'
            read_voice(speech,beat.narration,raw)
            voice_seconds = len(beat.narration.split())*60/WORDS_PER_MINUTE
            seconds = 10 if preview else math.ceil((voice_seconds+1.5)*FPS)/FPS
            desired = min(voice_seconds,seconds-1)
            pitch = 2**(SEMITONES/12)
            tempo = duration(raw)/(desired*pitch)
            ffmpeg('-i',raw,'-af',f'asetrate={RATE*pitch:.7f},aresample={RATE},atempo={tempo:.7f},'
                   'highpass=f=75,adelay=300,apad','-t',f'{seconds:.6f}',voice)
            encode_visuals(beat,seconds,size,visual)
            timeline.append({'chapter':beat.label,'start':round(sum(x['seconds'] for x in timeline),3),
                             'seconds':seconds,'population':beat.population,'forage':beat.forage})
            print(json.dumps({'chapter':beat.label,'rendered':True,'seconds':seconds}),flush=True)
        for label, files in [('video', sorted(work.glob('visual-*.mp4'))),
                             ('voice', sorted(work.glob('voice-[0-9][0-9].wav')))]:
            (work/f'{label}.txt').write_text(''.join(f"file '{file.name}'\n" for file in files))
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
    (output/'episode.json').write_text(json.dumps({
        'title':title,'illustrative_simulation':True,'preview':preview,
        'voice':VOICE,'pitch_semitones':SEMITONES,'words_per_minute_target':WORDS_PER_MINUTE,
        'music_bpm':BPM,'chapters':timeline},indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--episode',choices=EPISODES,default='goat-island')
    parser.add_argument('--output',type=Path,default=Path('output/wildlife'))
    parser.add_argument('--preview',action='store_true')
    args=parser.parse_args()
    render(args.episode,args.output,args.preview)
