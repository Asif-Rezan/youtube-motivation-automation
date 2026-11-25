"""CPU neural nature images, instrumental music, rain audio and a one-minute film."""
import argparse,hashlib,json,math,os,subprocess,time
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
SECONDS=60;FPS=24;SIZE=(1280,720)
RAIN_MODEL='cvssp/audioldm-s-full-v2';RAIN_REV='feeb3d14203495a4b6ac0893cbdedb2159b4819c'
SCENES=[
 'A tranquil tropical rainforest pond in light rain, green fern foreground, smooth stones, soft mist, diffused dawn light, calm reflective water, photorealistic landscape, no people',
 'A peaceful wooden terrace overlooking a lush tropical garden in gentle rain, wet timber, palm leaves, warm soft dawn glow, realistic nature photography, no people',
 'A secluded forest creek with mossy rocks and delicate ferns in a rainy green jungle, soft overcast light, realistic landscape photography, no people',
 'A serene lotus pond with white flowers and broad green leaves covered in raindrops, distant rainforest mist, soft cinematic natural light, realistic landscape, no people',
 'A quiet bamboo grove and a small reflecting pool in soft rain, mossy stones, lush foliage, atmospheric mist, peaceful realistic landscape photography, no people',
 'A sheltered tropical garden beside a still lake after gentle rain, dew on leaves, pale morning sky, subtle warm light, tranquil photorealistic landscape, no people']

def seed(run,index):return int(hashlib.sha256(f'{run}:{index}'.encode()).hexdigest()[:8],16)%(2**31-1)
def plan(out,run):
 out.mkdir(parents=True,exist_ok=True)
 data=dict(run_id=run,seconds=SECONDS,fps=FPS,resolution=SIZE,publish=False,
  title='Rain Garden — Gentle Piano & Soft Rain',
  scenes=[dict(index=i,start=i*10,duration=10,prompt=p,seed=seed(run,i)) for i,p in enumerate(SCENES)],
  music_prompt='Peaceful ambient relaxation music, very slow gentle sparse felt piano, warm soft sustained pads, tranquil rainy tropical garden atmosphere, calm spacious arrangement, no drums, no sudden loud sounds, no vocals, no speech.',
  rain_prompt='Gentle steady rain falling on broad tropical leaves beside a quiet garden pond, soft water droplets, peaceful continuous natural rain ambience, no thunder, no voices, no music.',
  models=dict(images='segmind/SSD-1B',music='ACE-Step/Ace-Step1.5',nature=RAIN_MODEL),
  nature_license='CC-BY-NC-SA-4.0: private noncommercial evaluation only; do not publish or monetize this preview',
  audio_design='AI instrumental and AI rain loops with overlapping crossfades; not a continuous 60-second model inference')
 (out/'plan.json').write_text(json.dumps(data,indent=2));return data

def image(out,index):
 from image_cpu import MODEL,REVISION
 import torch
 from diffusers import DiffusionPipeline,DPMSolverMultistepScheduler
 torch.set_num_threads(min(4,os.cpu_count() or 2))
 data=json.loads((out/'plan.json').read_text());scene=data['scenes'][index]
 p=DiffusionPipeline.from_pretrained(MODEL,revision=REVISION,torch_dtype=torch.float32,use_safetensors=True,trust_remote_code=False,token=False)
 p.scheduler=DPMSolverMultistepScheduler.from_config(p.scheduler.config,algorithm_type='dpmsolver++',use_karras_sigmas=True)
 p.to('cpu');p.enable_attention_slicing();p.enable_vae_slicing()
 for attempt in range(3):
  with torch.inference_mode():r=p(scene['prompt'],negative_prompt='text, typography, watermark, logo, person, people, human, cartoon, illustration, blurry, low quality, collage, border',width=768,height=432,num_inference_steps=16,guidance_scale=7,generator=torch.Generator(device='cpu').manual_seed(scene['seed']+attempt))
  if any(getattr(r,'nsfw_content_detected',None) or []):continue
  im=r.images[0];target=out/f'scene-{index:02d}.png';tmp=target.with_suffix('.partial.png');im.save(tmp)
  with Image.open(tmp) as check:
   check.load()
   if check.size!=(768,432) or np.asarray(check).std()<3:raise ValueError('Invalid/blank AI image')
  tmp.replace(target);print('AI_IMAGE_READY',index,flush=True);return
 raise RuntimeError('Image safety checker rejected all three attempts; no fallback artwork')

def music(out):
 from music_cpu import generate_segment
 data=json.loads((out/'plan.json').read_text());state={}
 def save():(out/'music-state.json').write_text(json.dumps(state,indent=2))
 generate_segment(dict(_segment=True,prompt=data['music_prompt'],lyrics='[Instrumental]',duration=24,bpm=60,instrumental=True),out/'music-original.wav',state,save)

def nature(out):
 import torch,soundfile as sf
 from diffusers import AudioLDMPipeline
 torch.set_num_threads(min(4,os.cpu_count() or 2))
 data=json.loads((out/'plan.json').read_text())
 p=AudioLDMPipeline.from_pretrained(RAIN_MODEL,revision=RAIN_REV,torch_dtype=torch.float32,use_safetensors=True,trust_remote_code=False,token=False).to('cpu')
 p.enable_attention_slicing()
 with torch.inference_mode():
  audio=p(data['rain_prompt'],negative_prompt='speech, voices, singing, music, thunder, loud bangs, distortion',num_inference_steps=25,audio_length_in_s=10.,guidance_scale=2.5,generator=torch.Generator(device='cpu').manual_seed(seed(data['run_id'],99))).audios[0]
 audio=np.asarray(audio,dtype=np.float32)
 validate_audio(audio,16000,10)
 sf.write(out/'rain-original.wav',audio,16000,subtype='PCM_16')
 (out/'nature-license.txt').write_text(data['nature_license']+'\nSource: https://huggingface.co/'+RAIN_MODEL+'\n')
 print('AI_RAIN_READY',flush=True)

def validate_audio(pcm,rate,expected):
 if rate<=0 or abs(len(pcm)/rate-expected)>1:raise ValueError('Unexpected generated audio duration')
 if not np.isfinite(pcm).all() or np.sqrt(np.mean(pcm.astype(float)**2))<1e-5:raise ValueError('Invalid or silent AI audio')

def extend(pcm,rate,seconds=60,fade_seconds=1.5):
 if pcm.ndim==1:pcm=np.column_stack([pcm,pcm])
 if pcm.shape[1]!=2:raise ValueError('Expected mono/stereo source')
 n=round(rate*seconds);fade=min(round(rate*fade_seconds),len(pcm)//4)
 if fade<2:raise ValueError('Clip too short for a smooth loop')
 ramp=np.linspace(0,1,fade)[:,None];result=pcm.copy()
 while len(result)<n:
  join=result[-fade:]*(1-ramp)+pcm[:fade]*ramp
  result=np.concatenate([result[:-fade],join,pcm[fade:]],axis=0)
 return result[:n]

def mixed_audio(out):
 import soundfile as sf
 from scipy.signal import resample_poly
 rate=48000;tracks=[]
 for filename,expected,target_db in [('music-original.wav',24,-26),('rain-original.wav',10,-28)]:
  pcm,sr=sf.read(out/filename,dtype='float32',always_2d=True);validate_audio(pcm,sr,expected)
  pcm=extend(pcm,sr);g=math.gcd(sr,rate);pcm=resample_poly(pcm,rate//g,sr//g,axis=0)
  rms=np.sqrt(np.mean(pcm.astype(float)**2));pcm*=min(8,10**(target_db/20)/rms);tracks.append(pcm)
 mix=sum(tracks);fade=rate*2;r=np.linspace(0,1,fade)[:,None];mix[:fade]*=r;mix[-fade:]*=r[::-1]
 peak=float(np.max(np.abs(mix)))
 if peak>.89:mix*=.89/peak
 sf.write(out/'relaxation-mix.wav',mix,rate,subtype='PCM_16')
 return dict(raw_mix_peak=peak,mixed_seconds=len(mix)/rate,sample_rate=rate)

def image_at(images,t):
 i=min(5,int(t//10));u=(t%10)/10;im=images[i]
 # Very slow zoom; new AI scene every ten seconds with a soft dissolve.
 def crop(source,z):
  w,h=source.size;cw=round(w/z);ch=round(h/z);x=(w-cw)//2;y=(h-ch)//2
  return source.crop((x,y,x+cw,y+ch)).resize(SIZE,Image.Resampling.BICUBIC)
 current=crop(im,1+.025*u)
 if t%10>9.2 and i<5:current=Image.blend(current,crop(images[i+1],1),((t%10)-9.2)/.8)
 return current

def compose(out):
 audio_report=mixed_audio(out)
 images=[]
 for i in range(6):
  with Image.open(out/f'scene-{i:02d}.png') as im:im.load();images.append(im.convert('RGB'))
 started=time.monotonic()
 target=out/'rain-garden-60s.mp4';tmp=out/'rain-garden-60s.partial.mp4'
 cmd=['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1280x720','-r',str(FPS),'-i','pipe:0','-i',str(out/'relaxation-mix.wav'),'-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-af','alimiter=limit=0.89:level=false','-t','60','-movflags','+faststart',str(tmp)]
 proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
 try:
  for f in range(SECONDS*FPS):
   im=image_at(images,f/FPS)
   # No narration, workout graphics or persistent text over the relaxing scenes.
   proc.stdin.write(im.tobytes())
   if f%(FPS*10)==0:print('COMPOSE_SECONDS',f//FPS,flush=True)
 finally:proc.stdin.close()
 if proc.wait()!=0:raise RuntimeError('FFmpeg encoding failed')
 probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(tmp)]))
 video=next(s for s in probe['streams'] if s['codec_type']=='video')
 if (video['width'],video['height'])!=SIZE or int(video['nb_frames'])!=1440 or abs(float(probe['format']['duration'])-60)>.05:raise ValueError('Final preview dimensions/duration mismatch')
 subprocess.run(['ffmpeg','-v','error','-i',str(tmp),'-f','null','-'],check=True)
 tmp.replace(target)
 report=dict(seconds=60,frames=1440,resolution=SIZE,scene_change_seconds=10,ai_images=6,publish=False,compose_seconds=round(time.monotonic()-started,2),**audio_report)
 (out/'quality-report.json').write_text(json.dumps(report,indent=2))
 # One honest preview contact sheet for browsing the result.
 sheet=Image.new('RGB',(1280,1080))
 for i,im in enumerate(images):sheet.paste(im.resize((640,360)),((i%2)*640,(i//2)*360))
 sheet.save(out/'scene-preview.jpg',quality=92);print(json.dumps(report),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('stage',choices=['plan','image','music','nature','compose']);p.add_argument('--out',type=Path,default=Path('output/relaxation-preview'));p.add_argument('--run-id',default='local');p.add_argument('--index',type=int,choices=range(6),default=0)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 if a.stage=='plan':plan(a.out,a.run_id)
 elif a.stage=='image':image(a.out,a.index)
 else:globals()[a.stage](a.out)
