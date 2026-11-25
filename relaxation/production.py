"""Three-hour draft: 20 AI images, reusable ten-second clips and timed chapters.

No publication. Music/rain source license still prevents commercial rollout.
"""
import argparse,json,random,subprocess,math
from pathlib import Path
from .preview import seed,image_at,atmospheric,thumbnail,extend
from PIL import Image
import numpy as np

def build_timeline(image_count=20,seconds=10800,seed_value=0):
 if type(seconds)is not int or seconds<10 or seconds%10:raise ValueError('Duration must contain complete ten-second slots')
 if not 2<=image_count<=100:raise ValueError('At least two images are needed to avoid adjacent repeats')
 rng=random.Random(seed_value);order=list(range(image_count));rng.shuffle(order);rows=[]
 # Stable episode-specific order makes transitions reusable as well as images.
 # A new run gets a different order, while four camera takes rotate each cycle.
 for slot,start in enumerate(range(0,seconds,10)):
  image=order[slot%image_count];variant=(slot//image_count)%4
  rows.append(dict(start=start,duration=10,image=image,variant=variant,chapter=start//900))

 return rows

def timestamp(seconds):
 h,rest=divmod(seconds,3600);m,s=divmod(rest,60)
 return f'{h:02d}:{m:02d}:{s:02d}' if h else f'{m:02d}:{s:02d}'
def chapter_text(titles,seconds=10800):
 count=math.ceil(seconds/900)
 if len(titles)!=count or any(not isinstance(t,str) or not t.strip() for t in titles):raise ValueError('One nonempty AI chapter title per fifteen-minute block is required')
 return '\n'.join(f'{timestamp(i*900)} {t.strip()}' for i,t in enumerate(titles))

def clip_worker(out,index):
 data=json.loads((out/'plan.json').read_text());scene=data['scenes'][index]
 with Image.open(out/f'scene-{index:02d}.png') as im:source=im.convert('RGB')
 with Image.open(out/f'depth-{index:02d}.png') as d:depth=d.convert('L')
 rng=np.random.default_rng(seed(data['run_id'],index+1100));points=[(float(rng.uniform(0,1280)),float(rng.uniform(0,720)),float(rng.uniform(100,240))) for _ in range(70)]
 order=[r['image'] for r in data['timeline'][:20]];position=order.index(index);next_index=order[(position+1)%20]
 with Image.open(out/f'scene-{next_index:02d}.png') as im:next_source=im.convert('RGB')
 with Image.open(out/f'depth-{next_index:02d}.png') as d:next_depth=d.convert('L')
 cameras=['pan_left','pan_right','zoom_in','zoom_out']
 for variant,camera in enumerate(cameras):
  row=dict(scene,camera=camera);target=out/f'clip-{index:02d}-{variant}.mp4'
  cmd=['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1280x720','-r','24','-i','pipe:0','-an','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-video_track_timescale','24000',str(target)]
  proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
  next_variant=(variant+1)%4 if position==19 else variant
  next_row=dict(data['scenes'][next_index],camera=cameras[next_variant])
  next_frame=image_at([next_source]*6,0,[next_row]*6)
  next_frame=atmospheric(next_frame,image_at([next_depth]*6,0,[next_row]*6),0,next_row,points)
  try:
   for f in range(240):
    t=f/24;im=image_at([source]*6,t,[row]*6);d=image_at([depth]*6,t,[row]*6)
    im=atmospheric(im,d,t,row,points)
    if t>8:
     fraction=(t-8)/2;fraction=fraction*fraction*(3-2*fraction)
     im=Image.blend(im,next_frame,fraction)
    proc.stdin.write(im.tobytes())
  finally:proc.stdin.close()
  if proc.wait()!=0:raise RuntimeError('Clip encoding failed')
  print('REUSABLE_CLIP_READY',index,variant,flush=True)

def audio_worker(out):
 import soundfile as sf
 from .preview import mixed_audio
 data=json.loads((out/'plan.json').read_text());mixed_audio(out)
 # Build a short continuous bed from already crossfaded originals, before the
 # compositor's global end fades. No need for a 3-hour NumPy/WAV allocation.
 from scipy.signal import resample_poly
 tracks=[]
 for filename,db in [('music-original.wav',-25),('rain-original.wav',-33)]:
  pcm,sr=sf.read(out/filename,dtype='float32',always_2d=True);pcm=extend(pcm,sr,seconds=70,fade_seconds=4)
  g=math.gcd(sr,48000);pcm=resample_poly(pcm,48000//g,sr//g,axis=0)
  rms=max(float(np.sqrt(np.mean(pcm.astype(float)**2))),1e-6);tracks.append(pcm*min(8,10**(db/20)/rms))
 bed=sum(tracks);sf.write(out/'production-bed.wav',bed,48000,subtype='PCM_16')
 # Ten seconds overlap makes the loop seam smooth; keep the central 60 seconds.
 # Blend the previous tail into its beginning rather than looping a faded bed.
 n=48000*5;r=np.linspace(0,1,n)[:,None]
 join=bed[60*48000:65*48000]*(1-r)+bed[:n]*r
 a=np.concatenate([join,bed[n:60*48000]])
 sf.write(out/'production-loop.wav',a,48000,subtype='PCM_16')
 seconds=data['seconds']
 subprocess.run(['ffmpeg','-v','error','-y','-stream_loop','-1','-i',str(out/'production-loop.wav'),'-t',str(seconds),'-af',f'afade=t=in:d=4,afade=t=out:st={seconds-5}:d=5,alimiter=limit=0.89:level=false','-c:a','aac','-b:a','192k',str(out/'production-audio.m4a')],check=True)

def assemble(out):
 data=json.loads((out/'plan.json').read_text());rows=data['timeline']
 if len(rows)!=1080 or data['seconds']!=10800:raise ValueError('Expected exact three-hour timeline')
 for a,b in zip(rows,rows[1:]):
  if a['image']==b['image']:raise ValueError('Adjacent duplicate image in production timeline')
 with (out/'concat.txt').open('w') as f:
  for row in rows:
   path=out/f"clip-{row['image']:02d}-{row['variant']}.mp4"
   if not path.exists():raise ValueError('Missing reusable clip '+str(path))
   f.write("file '"+path.name+"'\n")
 target=out/'relaxation-3-hours.mp4'
 def escaped(text):
  text=' '.join(text.split())
  for char in ['\\','=',';','#']:text=text.replace(char,'\\'+char)
  return text
 metadata=[';FFMETADATA1','title='+escaped(data['title'])]
 for i,title in enumerate(data['chapter_titles']):
  metadata.extend(['[CHAPTER]','TIMEBASE=1/1000',f'START={i*900000}',f'END={(i+1)*900000}','title='+escaped(title)])
 (out/'chapters.ffmeta').write_text('\n'.join(metadata)+'\n')
 subprocess.run(['ffmpeg','-v','error','-y','-f','concat','-safe','1','-i',str(out/'concat.txt'),'-i',str(out/'production-audio.m4a'),'-f','ffmetadata','-i',str(out/'chapters.ffmeta'),'-map_metadata','2','-map_chapters','2','-map','0:v:0','-map','1:a:0','-c','copy','-t','10800','-movflags','+faststart',str(target)],check=True)
 probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-show_chapters','-of','json',str(target)]))
 if abs(float(probe['format']['duration'])-10800)>.1:raise ValueError('Wrong production draft duration')
 video=next(s for s in probe['streams'] if s['codec_type']=='video')
 if int(video['nb_frames'])!=259200:raise ValueError('Wrong production video frame count')
 if len(probe.get('chapters',[]))!=12:raise ValueError('Embedded chapters are missing')
 images=[Image.open(out/f'scene-{i:02d}.png').convert('RGB') for i in range(20)];thumbnail(out,images,data)
 (out/'chapters.txt').write_text(data['chapters']+'\n')
 (out/'production-report.json').write_text(json.dumps(dict(seconds=10800,frames=259200,unique_images=20,reusable_clips=80,slots=1080,adjacent_duplicate_images=False,chapters=12,publication=False,transitions='Two-second smooth dissolves baked into reusable clips'),indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('stage',choices=['plan','clips','audio','assemble']);p.add_argument('--out',type=Path,default=Path('output/relaxation-production'));p.add_argument('--run-id',default='local');p.add_argument('--index',type=int,choices=range(20),default=0);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 if a.stage=='plan':
  from .planning import generate
  generate(a.out,a.run_id,seed,seconds=10800,image_count=20)
 elif a.stage=='clips':clip_worker(a.out,a.index)
 else:globals()[a.stage](a.out)
