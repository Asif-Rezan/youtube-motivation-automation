"""Review-only text2music preview requesting the researched RIYA/Nunu chords."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from music_cpu import checkpoints, runtime, generation_progress, MODEL

LYRICS='''[Chorus]
Dudi dudi dam dam dudi dudi dam
Dudi dudi dam dam come and play
[Verse]
Little bunny come and play
Children smile along the way
[Chorus]
Dudi dudi dam dam dudi dudi dam
[Verse]
Wave hello beneath the sky
Little bunny jump up high
[Outro]
Dudi dudi dam dam dudi dudi dam'''


def render():
    root=Path('output/chord-vocal-preview')
    root.mkdir(parents=True,exist_ok=True)
    reference=Path('assets/reference/style-reference.mp3').resolve()
    seconds=30
    source=Path(os.environ.get('ACESTEP_SOURCE_DIR','.vendor/ace-step')).resolve()
    models=Path(os.environ.get('ACESTEP_CHECKPOINTS_DIR','.models/acestep')).resolve()
    checkpoints(models)
    os.environ['ACESTEP_CHECKPOINTS_DIR']=str(models)
    os.environ['ACESTEP_INIT_LLM']='false'
    os.environ['CUDA_VISIBLE_DEVICES']=''
    os.environ['ACESTEP_VAE_DECODE_CHUNK_SIZE']='128'
    torch,Handler,Params,Config,infer=runtime(source)
    torch.set_num_threads(min(4,os.cpu_count() or 1))
    torch.set_num_interop_threads(1)
    handler=Handler()
    print(json.dumps({'phase':'loading chord preview model','device':'cpu','model':MODEL}),flush=True)
    _,ready=handler.initialize_service(project_root=str(source),config_path=MODEL,
        device='cpu',use_flash_attention=False,compile_model=False,
        offload_to_cpu=False,offload_dit_to_cpu=False,quantization=None,
        prefer_source='huggingface',use_mlx_dit=False)
    if not ready or handler.device!='cpu':
        raise RuntimeError('ACE-Step CPU initialization failed')
    params=Params(task_type='text2music',reference_audio=str(reference),
        keyscale='D Major',bpm=120,timesignature='4',
        caption='Vocal nursery rhyme with a prominent dry solo adult female lead singing every supplied lyric clearly from the first beat. Loud intelligible foreground singing, sparse quiet ukulele and soft handclaps underneath. Immediate sung Dudi Dudi Dam Dam chorus, no instrumental intro or solo. Joyful playful melody. D major, 120 BPM, 4/4, chorus harmony A-Bm-A-Bm-Em-D. The singing is the main focus.',
        lyrics=LYRICS,vocal_language='en',instrumental=False,duration=seconds,
        seed=20261102,inference_steps=8,thinking=False,use_cot_metas=False,
        use_cot_caption=False,use_cot_language=False)
    config=Config(batch_size=1,audio_format='wav',allow_lm_batch=False,use_random_seed=False)
    settings={'task_type':params.task_type,'seconds':seconds,'lyrics':LYRICS,
        'requested_chords':['A','Bm','A','Bm','Em','D'],
        'keyscale':params.keyscale,'bpm':params.bpm,'timesignature':params.timesignature,
        'chords_source':'Chordify RIYA/Nunu transcription; requested, not audio-verified',
        'reference_sha256':hashlib.sha256(reference.read_bytes()).hexdigest(),
        'vocal_priority':True,'preview_only':True,'seed':params.seed,'inference_steps':params.inference_steps,
        'volume_gain':2.0,'volume_gain_db':6.0206,'limiter_peak':0.98}
    (root/'settings.json').write_text(json.dumps(settings,indent=2))
    print(json.dumps({'phase':'generating chord preview',**settings}),flush=True)
    from faster_whisper import WhisperModel
    import re
    recognizer=None
    vocal_report=None
    # Retry an inaudible/instrumental output; never label it a vocal sample just
    # because the file decodes successfully. Retain transcripts for review.
    for attempt in range(3):
        params.seed=20261102+attempt*103
        with torch.inference_mode(),generation_progress():
            result=infer(handler,None,params,config,save_dir=str(root/'generated'))
        if not result.success or not result.audios:
            raise RuntimeError('Vocal preview generation failed: '+str(result.error))
        audio=Path(result.audios[0]['path'])
        if recognizer is None:
            recognizer=WhisperModel('base.en',device='cpu',compute_type='int8',cpu_threads=4)
        segments,_=recognizer.transcribe(str(audio),language='en',beam_size=5,
            vad_filter=False,condition_on_previous_text=False)
        segments=list(segments)
        heard=' '.join(seg.text.strip() for seg in segments)
        words=set(re.findall(r'[a-z]+',heard.lower()))
        expected={'little','bunny','come','play','children','smile','along','way','wave','hello','beneath','sky','jump','high'}
        matched=sorted(words & expected)
        confident=any(seg.no_speech_prob<.6 and seg.avg_logprob>-1.2 for seg in segments)
        vocal_report=dict(attempt=attempt+1,seed=params.seed,transcript=heard,
            matched_lyric_words=matched,passed=len(matched)>=3 and confident,
            segments=[dict(start=seg.start,end=seg.end,text=seg.text,
                no_speech_prob=seg.no_speech_prob,avg_logprob=seg.avg_logprob) for seg in segments])
        (root/f'vocal-check-{attempt+1}.json').write_text(json.dumps(vocal_report,indent=2))
        print(json.dumps({'phase':'vocal intelligibility check',**vocal_report}),flush=True)
        if vocal_report['passed']:
            break
    else:
        raise RuntimeError('No candidate passed vocal lyric recognition; inspect saved transcripts')
    settings.update(seed=params.seed,vocal_check=vocal_report)
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(audio)]))
    measured=float(info['format']['duration'])
    if abs(measured-seconds)>2 or not any(s['codec_type']=='audio' for s in info['streams']):
        raise RuntimeError('Cover preview duration/audio validation failed')
    preview=root/'riya-chords-vocals.mp3'
    subprocess.run(['ffmpeg','-y','-v','error','-i',str(audio),'-af','volume=2.0,alimiter=limit=0.98:level=false:latency=true','-c:a','libmp3lame','-b:a','192k',str(preview)],check=True)
    subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(preview),'-f','null','-'],check=True)
    settings.update(passed=True,actual_seconds=measured,
        preview_sha256=hashlib.sha256(preview.read_bytes()).hexdigest())
    (root/'settings.json').write_text(json.dumps(settings,indent=2))
    print(json.dumps({'phase':'chord preview ready','seconds':measured,'requested_chords':settings['requested_chords']}),flush=True)


if __name__=='__main__':
    render()
