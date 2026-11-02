"""Continuous, louder nursery mixes without shortening the storyboard or looping."""
import json
from pathlib import Path
import re
import subprocess

VERSION='continuous-kids-mix-v1'
BPM=120
LOUDNESS='loudnorm=I=-14:TP=-1.5:LRA=9'


class AudioGapError(RuntimeError):
    pass


def verify_continuity(path,seconds):
    result=subprocess.run(['ffmpeg','-hide_banner','-nostats','-i',str(path),'-t',str(seconds),
        '-af','silencedetect=noise=-45dB:d=0.65','-f','null','-'],
        check=True,capture_output=True,text=True,timeout=300)
    start=None
    gaps=[]
    for line in result.stderr.splitlines():
        found=re.search(r'silence_start: ([\d.]+)',line)
        if found:
            start=float(found.group(1))
        found=re.search(r'silence_end: ([\d.]+)',line)
        if found and start is not None:
            gaps.append((start,float(found.group(1))))
            start=None
    if start is not None:
        gaps.append((start,float(seconds)))
    # Tiny onset/outro tails are normal; long internal silence is not.
    bad=[(a,b) for a,b in gaps if min(b,seconds-.25)-max(a,.15)>=.65]
    if bad:
        raise AudioGapError('Unexpected music silence at '+','.join(f'{a:.2f}-{b:.2f}s' for a,b in bad))


def master_parts(parts,target,seconds):
    """Join parts with 80ms crossfades and restore duration without padding."""
    target=Path(target)
    temporary=target.with_suffix('.master.tmp.wav')
    args=['ffmpeg','-y','-v','error']
    for part in parts:
        args+=['-i',str(part)]
    filters=[]
    previous='0:a'
    for i in range(1,len(parts)):
        label=f'join{i}'
        filters.append(f'[{previous}][{i}:a]acrossfade=d=0.08:c1=tri:c2=tri[{label}]')
        previous=label
    # Pitch-preserving compensation is below 0.1% for episode-sized parts.
    ratio=(seconds-.08*(len(parts)-1))/seconds
    filters.append(f'[{previous}]atempo={ratio:.12f},{LOUDNESS},atrim=duration={seconds},asetpts=N/SR/TB[out]')
    try:
        subprocess.run(args+['-filter_complex',';'.join(filters),'-map','[out]',
            '-ar','44100','-ac','2','-c:a','pcm_s16le',str(temporary)],
            check=True,capture_output=True,timeout=600)
        result=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration',
            '-of','json',str(temporary)],check=True,capture_output=True,text=True)
        measured=float(json.loads(result.stdout)['format']['duration'])
        if abs(measured-seconds)>.1:
            raise ValueError('Mastered music duration differs from the storyboard')
        verify_continuity(temporary,seconds)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
