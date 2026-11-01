"""Isolated, review-only cover preview; never changes episode generation settings."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from music_cpu import checkpoints, runtime, generation_progress, MODEL

LYRICS='''[Verse]
Little bunny come and play
Children smile along the way
[Chorus]
Dudi dudi dam dam dudi dudi dam
[Verse]
Butterflies are flying high
Wave hello beneath the sky
[Chorus]
Dudi dudi dam dam dudi dudi dam'''


def render():
    root=Path('output/cover-music-preview')
    root.mkdir(parents=True,exist_ok=True)
    reference=Path('assets/reference/style-reference.mp3').resolve()
    seconds=30
    # A PCM source removes decoder ambiguity; the user's reference is not looped.
    source_audio=root/'source.wav'
    subprocess.run(['ffmpeg','-y','-v','error','-i',str(reference),'-t',str(seconds),
                    '-ar','48000','-ac','2',str(source_audio)],check=True)
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
    print(json.dumps({'phase':'loading cover preview model','device':'cpu','model':MODEL}),flush=True)
    _,ready=handler.initialize_service(project_root=str(source),config_path=MODEL,
        device='cpu',use_flash_attention=False,compile_model=False,
        offload_to_cpu=False,offload_dit_to_cpu=False,quantization=None,
        prefer_source='huggingface',use_mlx_dit=False)
    if not ready or handler.device!='cpu':
        raise RuntimeError('ACE-Step CPU initialization failed')
    params=Params(task_type='cover',src_audio=str(source_audio.resolve()),
        reference_audio=str(reference),audio_cover_strength=0.5,cover_noise_strength=0.0,
        caption='Joyful nursery rhyme, sweet adult female singing voice, clear English diction, playful dudi dudi dam dam refrain, warm child-friendly mix. Follow the source musical style and arrangement.',
        lyrics=LYRICS,vocal_language='en',instrumental=False,duration=seconds,
        seed=20261101,inference_steps=8,thinking=False,use_cot_metas=False,
        use_cot_caption=False,use_cot_language=False)
    config=Config(batch_size=1,audio_format='wav',allow_lm_batch=False,use_random_seed=False)
    settings={'task_type':params.task_type,'audio_cover_strength':params.audio_cover_strength,
        'cover_noise_strength':params.cover_noise_strength,'seconds':seconds,'lyrics':LYRICS,
        'reference_sha256':hashlib.sha256(reference.read_bytes()).hexdigest(),
        'preview_only':True,'seed':params.seed,'inference_steps':params.inference_steps,
        'volume_gain':2.0,'volume_gain_db':6.0206,'limiter_peak':0.98}
    (root/'settings.json').write_text(json.dumps(settings,indent=2))
    print(json.dumps({'phase':'generating cover preview',**settings}),flush=True)
    with torch.inference_mode(),generation_progress():
        result=infer(handler,None,params,config,save_dir=str(root/'generated'))
    if not result.success or not result.audios:
        raise RuntimeError('Cover preview generation failed: '+str(result.error))
    audio=Path(result.audios[0]['path'])
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(audio)]))
    measured=float(info['format']['duration'])
    if abs(measured-seconds)>2 or not any(s['codec_type']=='audio' for s in info['streams']):
        raise RuntimeError('Cover preview duration/audio validation failed')
    preview=root/'cover-strength-50.mp3'
    subprocess.run(['ffmpeg','-y','-v','error','-i',str(audio),'-af','volume=2.0,alimiter=limit=0.98:level=false:latency=true','-c:a','libmp3lame','-b:a','192k',str(preview)],check=True)
    subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(preview),'-f','null','-'],check=True)
    settings.update(passed=True,actual_seconds=measured,
        preview_sha256=hashlib.sha256(preview.read_bytes()).hexdigest())
    (root/'settings.json').write_text(json.dumps(settings,indent=2))
    print(json.dumps({'phase':'cover preview ready','seconds':measured,'strength':0.5}),flush=True)


if __name__=='__main__':
    render()
