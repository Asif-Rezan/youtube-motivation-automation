"""Real neural narration and ACE-Step instrumental music, with no canned fallback."""
import argparse,json,math,subprocess,wave
from pathlib import Path
import numpy as np

def voice(out):
    import torch
    from kokoro import KPipeline
    torch.set_num_threads(2)
    plan=json.loads((out/'plan.json').read_text());pipeline=KPipeline(lang_code='a',device='cpu',repo_id='hexgrad/Kokoro-82M')
    rate=24000;track=np.zeros(rate*60,dtype=np.float32);cues=[]
    for i,cue in enumerate(plan['narration']):
        pieces=[x.numpy() for _,_,x in pipeline(cue['text'],voice='af_heart',speed=1.) if x is not None]
        if not pieces:raise RuntimeError('Neural voice returned no audio')
        pcm=np.concatenate(pieces);raw=out/'cue-raw.wav';fitted=out/'cue-fitted.wav'
        if not np.isfinite(pcm).all() or np.max(np.abs(pcm))<.001:raise RuntimeError('Neural voice is silent or invalid')
        import soundfile as sf
        sf.write(raw,pcm,rate,subtype='PCM_16')
        ratio=max(1.,len(pcm)/rate/cue['window'])
        if ratio>1.6:raise ValueError('AI cue is too long for natural coaching speech')
        subprocess.run(['ffmpeg','-v','error','-y','-i',str(raw),'-af',f'atempo={ratio:.6f},afade=t=out:st={max(0,cue["window"]-.04)}:d=0.04','-ar',str(rate),str(fitted)],check=True)
        pcm,sr=sf.read(fitted,dtype='float32');start=round(cue['start']*rate)
        if start+len(pcm)>len(track):raise ValueError('Voice exceeds the exact preview duration')
        track[start:start+len(pcm)]+=pcm
        cues.append(dict(**cue,audio_seconds=len(pcm)/sr,voice='af_heart'))
        print('NEURAL_VOICE_CUE',i+1,flush=True)
    import soundfile as sf
    sf.write(out/'voice.wav',track,rate,subtype='PCM_16')
    envelope=[]
    for frame in range(1440):
        clip=track[frame*1000:(frame+1)*1000]
        envelope.append(min(1.,math.sqrt(float(np.mean(clip*clip)))*9))
    (out/'speech-envelope.json').write_text(json.dumps(envelope))
    (out/'voice-cues.json').write_text(json.dumps(cues,indent=2))
    raw.unlink(missing_ok=True);fitted.unlink(missing_ok=True)

def music(out):
    from music_cpu import generate_segment
    plan=json.loads((out/'plan.json').read_text());state={}
    def save():(out/'music-state.json').write_text(json.dumps(state,indent=2))
    request=dict(_segment=True,prompt=plan['music_prompt']+' Instrumental only, no singing, no speech.',
        lyrics='[Instrumental]',duration=24,bpm=plan['bpm'],instrumental=True)
    generate_segment(request,out/'music-original.wav',state,save)
    # Crossfade overlapping AI music sections, avoiding a hard loop boundary.
    import soundfile as sf
    pcm,rate=sf.read(out/'music-original.wav',dtype='float32',always_2d=True)
    if not 22<=len(pcm)/rate<=26:raise ValueError('Unexpected AI instrumental length')
    if not np.isfinite(pcm).all() or np.max(np.abs(pcm))<.001:raise RuntimeError('AI instrumental is silent or invalid')
    result=pcm.copy();fade=min(round(1.5*rate),len(pcm)//4)
    ramp=np.linspace(0,1,fade)[:,None]
    while len(result)<60*rate:
        join=result[-fade:]*(1-ramp)+pcm[:fade]*ramp
        result=np.concatenate([result[:-fade],join,pcm[fade:]],axis=0)
    result=result[:60*rate];n=rate
    result[:n]*=np.linspace(0,1,n)[:,None];result[-n:]*=np.linspace(1,0,n)[:,None]
    sf.write(out/'music.wav',result,rate,subtype='PCM_16')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['voice','music']);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();globals()[a.stage](a.out)
