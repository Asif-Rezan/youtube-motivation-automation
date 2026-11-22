"""Supervise short Blender batches, with atomic frame checkpoints and bounded retries."""
import argparse,json,os,subprocess,time,resource,signal,sys,math,hashlib,shutil
from pathlib import Path
from PIL import Image
from .timeline import FPS,SIZE,FRAMES_PER_SHARD,BATCH_FRAMES,SHARDS

class RenderFailure(RuntimeError):pass

def valid_checkpoint(folder,frame):
    path=folder/f'f-{frame:04d}.png';meta=folder/f'f-{frame:04d}.json'
    try:
        row=json.loads(meta.read_text())
        if row['frame']!=frame or set(row['feet'])!={'l','r'}:return False
        if any(not isinstance(v['height'],(int,float)) or not math.isfinite(v['height']) or v['height']<-.002 for v in row['feet'].values()):return False
        if any(len(v['points'])<3 or any(len(p)!=2 or not all(math.isfinite(x) for x in p) for p in v['points']) for v in row['feet'].values()):return False
        with Image.open(path) as im:
            if im.size!=SIZE or im.mode!='RGBA':return False
            im.load()
            return im.getbbox() is not None
    except (OSError,ValueError,KeyError,TypeError):return False

def execute_process(command,**kwargs):
    timeout=kwargs.pop('timeout')
    proc=subprocess.Popen(command,start_new_session=True,**kwargs)
    started=time.monotonic()
    try:
        while True:
            remaining=timeout-(time.monotonic()-started)
            if remaining<=0:raise subprocess.TimeoutExpired(command,timeout)
            try:return subprocess.CompletedProcess(command,proc.wait(timeout=min(60,remaining)))
            except subprocess.TimeoutExpired:
                if time.monotonic()-started>=timeout:raise
                print(json.dumps(dict(stage='Blender batch running',elapsed_seconds=round(time.monotonic()-started))),flush=True)
    except subprocess.TimeoutExpired:
        try:os.killpg(proc.pid,signal.SIGTERM)
        except ProcessLookupError:pass
        try:proc.wait(timeout=5)
        except subprocess.TimeoutExpired:pass
        try:os.killpg(proc.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        proc.wait()
        raise

def run(out,index,blender,source,*,execute=execute_process,count=FRAMES_PER_SHARD,batch=BATCH_FRAMES,timeout=1800):
    if not 0<=index<SHARDS or not 1<=count<=FRAMES_PER_SHARD or batch<1:raise ValueError('Invalid render shard bounds')
    folder=out/f'render-{index:02d}';folder.mkdir(parents=True,exist_ok=True)
    paths=[source,out/'speech-envelope.json',Path(__file__).with_name('render_character.py')]
    plan=json.loads((out/'plan.json').read_text())
    for key in ['run_id','recovery_source_run']:plan.pop(key,None)
    identity_data=json.dumps(plan,sort_keys=True,separators=(',',':')).encode()
    signature=hashlib.sha256(identity_data+b''.join(hashlib.sha256(p.read_bytes()).digest() for p in paths)).hexdigest()
    identity=folder/'worker-input.json'
    if identity.exists() and json.loads(identity.read_text()).get('signature')!=signature:
        retained=out/f'retained-render-{index:02d}-{time.time_ns()}'
        folder.rename(retained);folder.mkdir()
    identity.write_text(json.dumps(dict(signature=signature,profile='native-eevee32-1080p24-v2')))
    first=index*FRAMES_PER_SHARD;receipt=[]
    for begin in range(first,first+count,batch):
        frames=list(range(begin,min(first+count,begin+batch)))
        for attempt in range(1,4):
            invalid=[f for f in frames if not valid_checkpoint(folder,f)]
            if not invalid:break
            # Only discard invalid generated files; completed frames survive crashes.
            for f in invalid:
                for suffix in ['.png','.json']:(folder/f'f-{f:04d}{suffix}').unlink(missing_ok=True)
            env=os.environ.copy();env.update(FITNESS_OUTPUT=str(out),FITNESS_SHARD=str(index),
                FITNESS_FRAME_FIRST=str(begin),FITNESS_FRAME_COUNT=str(len(frames)))
            command=[blender,'-b',str(source),'--python-exit-code','2','--python','fitness/render_character.py']
            if os.name!='nt' and sys.platform=='linux':command=['xvfb-run','-a',*command]
            log=folder/f'batch-{begin:04d}-attempt-{attempt}.log';started=time.monotonic();wall=time.time();code=None
            print(json.dumps(dict(stage='render_batch',first=begin,count=len(frames),attempt=attempt)),flush=True)
            try:
                with log.open('w') as stream:
                    result=execute(command,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=timeout)
                code=result.returncode
            except subprocess.TimeoutExpired:code='timeout'
            text=log.read_text(errors='replace')
            crash=Path('/tmp')/(source.stem+'.crash.txt')
            if code in (139,-11) and crash.exists() and crash.stat().st_mtime>=wall-1:
                shutil.copy2(crash,folder/f'batch-{begin:04d}-attempt-{attempt}.crash.txt')
            remaining=[f for f in frames if not valid_checkpoint(folder,f)]
            receipt.append(dict(first=begin,attempt=attempt,returncode=code,remaining=remaining,
                elapsed_seconds=round(time.monotonic()-started),peak_child_memory_mb=round(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss/(1024 if sys.platform=='linux' else 1024**2))))
            (folder/'worker-receipt.json').write_text(json.dumps(receipt,indent=2))
            # Semantic/script errors must be corrected, never hidden as GPU retries.
            if 'Traceback (most recent call last)' in text or (code not in (0,139,-11,-9,137,'timeout')):
                raise RenderFailure(f'Blender script/render failed ({code}); log {log}\n'+text[-3500:])
            if not remaining:
                if code:print('Recovered complete validated batch after abnormal Blender shutdown',code,flush=True)
                break
            print(json.dumps(dict(stage='render_batch_retry',remaining=remaining,returncode=code)),flush=True)
            if attempt==3:raise RenderFailure(f'Blender failed after three attempts; {len(remaining)} frames pending; completed frame checkpoints retained. Log: {log}\n'+text[-2500:])
    all_frames=list(range(first,first+count))
    if any(not valid_checkpoint(folder,f) for f in all_frames):raise RenderFailure('Incomplete or invalid final shard')
    rows=[json.loads((folder/f'f-{f:04d}.json').read_text()) for f in all_frames]
    (folder/'contacts.json').write_text(json.dumps(rows))
    (folder/'render-review.json').write_text(json.dumps(dict(frames=count,first_frame=first,
        minimum_sole_z_m=min(v['height'] for r in rows for v in r['feet'].values()),fps=FPS,resolution=SIZE,
        batch_frames=batch,recovered=True,validated_pngs=True),indent=2))
    print('FITNESS_SHARD_VERIFIED',index,count,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--index',type=int,required=True)
    p.add_argument('--blender',default=os.environ.get('FITNESS_BLENDER','blender'))
    p.add_argument('--source',type=Path,default=Path('character/blender/kat-heel-raise-v1.blend'))
    args=p.parse_args();run(args.out,args.index,args.blender,args.source)
