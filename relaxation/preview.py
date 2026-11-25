"""CPU neural nature images, instrumental music, rain audio and a one-minute film."""
import argparse,hashlib,json,math,os,subprocess,time
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageChops
SECONDS=60;FPS=24;SIZE=(1280,720)
RAIN_MODEL='cvssp/audioldm-s-full-v2';RAIN_REV='feeb3d14203495a4b6ac0893cbdedb2159b4819c'
def seed(run,index):return int(hashlib.sha256(f'{run}:{index}'.encode()).hexdigest()[:8],16)%(2**31-1)
def plan(out,run):
 from .planning import generate
 return generate(out,run,seed)

def image_pipeline():
 from image_cpu import MODEL,REVISION
 import torch
 from diffusers import DiffusionPipeline,DPMSolverMultistepScheduler
 torch.set_num_threads(min(4,os.cpu_count() or 2))
 p=DiffusionPipeline.from_pretrained(MODEL,revision=REVISION,torch_dtype=torch.float32,use_safetensors=True,trust_remote_code=False,token=False)
 p.scheduler=DPMSolverMultistepScheduler.from_config(p.scheduler.config,algorithm_type='dpmsolver++',use_karras_sigmas=True)
 p.to('cpu');p.enable_attention_slicing();p.enable_vae_slicing()
 return p

def image(out,index,pipeline=None,make_depth=True):
 import torch
 data=json.loads((out/'plan.json').read_text());scene=data['scenes'][index]
 p=pipeline if pipeline is not None else image_pipeline()
 for attempt in range(3):
  with torch.inference_mode():r=p(scene['prompt'],negative_prompt='text, typography, watermark, logo, person, people, human, cartoon, illustration, blurry, low quality, collage, border',width=1024,height=576,num_inference_steps=20,guidance_scale=7,generator=torch.Generator(device='cpu').manual_seed(scene['seed']+attempt))
  if any(getattr(r,'nsfw_content_detected',None) or []):continue
  im=r.images[0];target=out/f'scene-{index:02d}.png';tmp=target.with_suffix('.partial.png');im.save(tmp)
  with Image.open(tmp) as check:
   check.load()
   if check.size!=(1024,576) or np.asarray(check).std()<3:raise ValueError('Invalid/blank AI image')
  tmp.replace(target)
  if pipeline is None:del p
  if make_depth:depth_mask(out,index,target)
  print('AI_IMAGE_READY',index,flush=True);return
 raise RuntimeError('Image safety checker rejected all three attempts; no fallback artwork')

def music(out):
 from music_cpu import generate_segment
 data=json.loads((out/'plan.json').read_text());state={}
 def save():(out/'music-state.json').write_text(json.dumps(state,indent=2))
 generate_segment(dict(_segment=True,prompt=data['music_prompt'],lyrics='[Instrumental]',duration=24,bpm=60,instrumental=True),out/'music-original.wav',state,save)

def depth_mask(out,index,target):
 import torch
 from transformers import AutoImageProcessor,AutoModelForDepthEstimation
 model='depth-anything/Depth-Anything-V2-Small-hf';rev='5426e4f0f36572d16453bbda7a8389317b1bef99'
 proc=AutoImageProcessor.from_pretrained(model,revision=rev,token=False)
 net=AutoModelForDepthEstimation.from_pretrained(model,revision=rev,use_safetensors=True,token=False).eval()
 with Image.open(target) as im:
  inputs=proc(images=im.convert('RGB'),return_tensors='pt')
 with torch.inference_mode():d=net(**inputs).predicted_depth[0].numpy()
 d=(d-d.min())/max(float(d.max()-d.min()),1e-6)
 Image.fromarray((d*255).astype('uint8')).resize((1024,576),Image.Resampling.BICUBIC).save(out/f'depth-{index:02d}.png')

def nature(out):
 import torch,soundfile as sf
 from scipy.signal import butter,sosfiltfilt
 from diffusers import AudioLDMPipeline
 torch.set_num_threads(min(4,os.cpu_count() or 2))
 data=json.loads((out/'plan.json').read_text())
 p=AudioLDMPipeline.from_pretrained(RAIN_MODEL,revision=RAIN_REV,torch_dtype=torch.float32,use_safetensors=True,trust_remote_code=False,token=False).to('cpu');p.enable_attention_slicing()
 selected=[];reviews=[]
 for take in range(4):
  with torch.inference_mode():
   audio=p(data['rain_prompt'],negative_prompt='speech, voices, singing, melody, music, thunder, loud bangs, distortion, crackling, clicks',num_inference_steps=40,audio_length_in_s=15.,guidance_scale=2.5,generator=torch.Generator(device='cpu').manual_seed(seed(data['run_id'],99+take))).audios[0]
  audio=np.asarray(audio,dtype=np.float32)
  try:validate_audio(audio,16000,15)
  except ValueError as error:
   reviews.append(dict(take=take,accepted=False,error=str(error)))
   (out/'rain-review.json').write_text(json.dumps(dict(candidates=reviews),indent=2));continue
  sf.write(out/f'rain-take-{take:02d}.wav',audio,16000,subtype='PCM_16')
  # Select a steady 10-second window: reject silence, extreme peaks and unstable energy.
  best=None
  for offset in range(0,5):
   clip=audio[offset*16000:(offset+10)*16000];score,valid=rain_score(clip,16000)
   if valid and (best is None or score<best[0]):best=(score,offset,clip)
  reviews.append(dict(take=take,accepted=best is not None,score=best[0] if best else None,offset=best[1] if best else None))
  if best is not None:
   clip=sosfiltfilt(butter(2,[90,5800],btype='bandpass',fs=16000,output='sos'),best[2]).astype('float32')
   # Soft peak control rather than hard clipping; final gain stays below the piano.
   rms=max(float(np.sqrt(np.mean(clip**2))),1e-6);clip=np.tanh(clip/(rms*8))*(rms*8)
   selected.append((best[0],clip))
  (out/'rain-review.json').write_text(json.dumps(dict(candidates=reviews),indent=2))
  if len(selected)>=3:break
 if len(selected)<3:raise RuntimeError('Insufficient steady AI rain takes; preserve candidates for review')
 selected.sort(key=lambda item:item[0]);clips=[c for _,c in selected[:3]]
 sf.write(out/'rain-original.wav',overlap(clips,16000,4),16000,subtype='PCM_16')
 (out/'rain-review.json').write_text(json.dumps(dict(candidates=reviews,selected=3,overlap_seconds=4,checks='signal-level screening only; naturalness and absence of voices still require listening'),indent=2))
 (out/'nature-license.txt').write_text(data['nature_license']+'\nSource: https://huggingface.co/'+RAIN_MODEL+'\n')
 print('THREE_AI_RAIN_TAKES_READY',flush=True)

def rain_score(clip,rate):
 windows=np.asarray([np.sqrt(np.mean(c.astype(float)**2)) for c in np.array_split(clip,20)])
 mean=float(windows.mean());rms=float(np.sqrt(np.mean(clip.astype(float)**2)))
 crest=float(np.max(np.abs(clip)))/max(rms,1e-8)
 variation=float(windows.std())/max(mean,1e-8)
 valid=mean>1e-5 and np.isfinite(clip).all() and crest<18 and variation<.8 and float(windows.min())>mean*.08
 return variation+crest*.03,valid

def overlap(clips,rate,fade_seconds):
 result=np.asarray(clips[0]);fade=round(rate*fade_seconds)
 for clip in clips[1:]:
  if min(len(result),len(clip))<=fade:raise ValueError('Clip shorter than crossfade')
  ramp=np.linspace(0,1,fade)
  if result.ndim==2:ramp=ramp[:,None]
  result=np.concatenate([result[:-fade],result[-fade:]*(1-ramp)+clip[:fade]*ramp,clip[fade:]])
 return result

def validate_audio(pcm,rate,expected):
 if rate<=0 or abs(len(pcm)/rate-expected)>1:raise ValueError('Unexpected generated audio duration')
 if not np.isfinite(pcm).all() or np.sqrt(np.mean(pcm.astype(float)**2))<1e-5:raise ValueError('Invalid or silent AI audio')

def extend(pcm,rate,seconds=60,fade_seconds=1.5):
 if pcm.ndim==1:pcm=np.column_stack([pcm,pcm])
 elif pcm.ndim==2 and pcm.shape[1]==1:pcm=np.repeat(pcm,2,axis=1)
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
 version=json.loads((out/'plan.json').read_text()).get('version',1)
 for filename,expected,target_db in [('music-original.wav',24,-25),('rain-original.wav',22 if version>=2 else 10,-33)]:
  pcm,sr=sf.read(out/filename,dtype='float32',always_2d=True);validate_audio(pcm,sr,expected)
  pcm=extend(pcm,sr,fade_seconds=4 if filename.startswith('rain') else 3);g=math.gcd(sr,rate);pcm=resample_poly(pcm,rate//g,sr//g,axis=0)
  rms=np.sqrt(np.mean(pcm.astype(float)**2));pcm*=min(8,10**(target_db/20)/rms);tracks.append(pcm)
 mix=sum(tracks);fade=rate*3;r=np.linspace(0,1,fade)[:,None];mix[:fade]*=r;mix[-fade:]*=r[::-1]
 peak=float(np.max(np.abs(mix)))
 if peak>.89:mix*=.89/peak
 sf.write(out/'relaxation-mix.wav',mix,rate,subtype='PCM_16')
 return dict(raw_mix_peak=peak,mixed_seconds=len(mix)/rate,sample_rate=rate)

def image_at(images,t,scenes=None):
 i=min(5,int(t//10));u=(t%10)/10
 def view(source,phase,kind):
  w,h=source.size;z=1.035+.02*(1-phase if kind=='zoom_out' else phase)
  cw,ch=w/z,h/z
  x=(w-cw)*({'pan_left':1-phase,'pan_right':phase}.get(kind,.5));y=(h-ch)*.5
  return source.transform(SIZE,Image.Transform.AFFINE,(cw/SIZE[0],0,x,0,ch/SIZE[1],y),resample=Image.Resampling.BICUBIC)
 kind=scenes[i].get('camera','zoom_in') if scenes else 'zoom_in';current=view(images[i],u,kind)
 if t%10>8 and i<5:
  fraction=((t%10)-8)/2;fraction=fraction*fraction*(3-2*fraction)
  current=Image.blend(current,view(images[i+1],0,scenes[i+1].get('camera','zoom_in') if scenes else 'zoom_in'),fraction)
 return current

def atmospheric(im,depth,t,scene,rng_points):
 # Nearer drops move faster and are more visible; distant layers get light mist.
 from PIL import ImageFilter
 d=depth.resize(SIZE,Image.Resampling.BILINEAR)
 far=ImageChops.invert(d).point(lambda x:round(x*.055))
 mist=Image.new('RGBA',SIZE,(210,226,222,0));mist.putalpha(far)
 im=im.convert('RGBA');im.alpha_composite(mist)
 layer=Image.new('RGBA',SIZE);draw=ImageDraw.Draw(layer)
 for x,y,speed in rng_points:
  xx=int((x+t*18)%SIZE[0]);yy=int((y+t*speed)%SIZE[1]);near=d.getpixel((xx,yy))/255
  draw.line((xx,yy,xx-2,yy+3+int(near*7)),fill=(209,226,229,round(8+near*24)),width=1)
 region=scene.get('water_region','none')
 if region!='none':
  # AI art direction bounds candidate water; image colour/texture rejects solid ground.
  small=im.convert('RGB').resize((320,180),Image.Resampling.BILINEAR)
  a=np.asarray(small,dtype=float);luma=a.mean(2)
  edges=np.asarray(small.convert('L').filter(ImageFilter.FIND_EDGES),dtype=float)
  xcenter={'lower_left':.25,'lower_center':.5,'lower_right':.75}[region]*SIZE[0]
  yy,xx=np.mgrid[:180,:320]
  region_mask=((xx-xcenter/4)/(320*.19))**2+((yy-180*.79)/(180*.14))**2<1
  water=region_mask & (edges<18) & (a[:,:,2]>a[:,:,0]*.75) & (luma>25)
  rings=Image.new('RGBA',SIZE);rd=ImageDraw.Draw(rings)
  for k in range(6):
   age=(t*.38+k*.157)%1;cx=xcenter+math.sin(k*21)*110;cy=SIZE[1]*(.73+(k%3)*.05);r=4+age*17
   rd.ellipse((cx-r,cy-r*.23,cx+r,cy+r*.23),outline=(205,225,222,int(25*(1-age))),width=1)
  mask=Image.fromarray((water*255).astype('uint8')).resize(SIZE,Image.Resampling.BILINEAR).filter(ImageFilter.GaussianBlur(4))
  rings.putalpha(ImageChops.multiply(rings.getchannel('A'),mask));layer.alpha_composite(rings)
 im.alpha_composite(layer);return im.convert('RGB')

def thumbnail(out,images,data):
 from PIL import ImageFilter,ImageStat
 i=data['thumbnail']['scene_index'];im=images[i].resize((1920,1080),Image.Resampling.LANCZOS)
 headline=data['thumbnail']['headline'];fontpath=next(p for p in [Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),Path('/System/Library/Fonts/Supplemental/Arial Bold.ttf')] if p.exists())
 f=ImageFont.truetype(str(fontpath),100);draw=ImageDraw.Draw(im)
 while draw.textbbox((0,0),headline,font=f)[2]>1700:f=ImageFont.truetype(str(fontpath),f.size-2)
 candidates=[(90,85),(90,845)];chosen=min(candidates,key=lambda p:ImageStat.Stat(im.crop((p[0],p[1],p[0]+1700,p[1]+150)).convert('L').filter(ImageFilter.FIND_EDGES)).mean[0])
 draw.text(chosen,headline,font=f,fill='#fff2cf',stroke_width=7,stroke_fill='#132d2a')
 im.save(out/'thumbnail.jpg',quality=95)

def compose(out):
 audio_report=mixed_audio(out)
 data=json.loads((out/'plan.json').read_text());images=[];depths=[]
 for i in range(6):
  with Image.open(out/f'scene-{i:02d}.png') as im:im.load();images.append(im.convert('RGB'))
  depth_path=out/f'depth-{i:02d}.png'
  if depth_path.exists():
   with Image.open(depth_path) as d:d.load();depths.append(d.convert('L'))
  elif data.get('version',1)>=2:raise ValueError('Missing generated depth mask')
  else:depths.append(Image.new('L',(1024,576),128))
 if 'thumbnail' in data:thumbnail(out,images,data)
 rng=np.random.default_rng(seed(data['run_id'],801));points=[(float(rng.uniform(0,1280)),float(rng.uniform(0,720)),float(rng.uniform(100,240))) for _ in range(95)]
 started=time.monotonic()
 target=out/'rain-garden-60s.mp4';tmp=out/'rain-garden-60s.partial.mp4'
 cmd=['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1280x720','-r',str(FPS),'-i','pipe:0','-i',str(out/'relaxation-mix.wav'),'-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-af','alimiter=limit=0.89:level=false','-t','60','-movflags','+faststart',str(tmp)]
 proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
 try:
  for f in range(SECONDS*FPS):
   t=f/FPS;im=image_at(images,t,data['scenes']);depth=image_at(depths,t,data['scenes'])
   if data.get('version',1)>=2:im=atmospheric(im,depth,t,data['scenes'][min(5,int(t//10))],points)
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
 report=dict(seconds=60,frames=1440,resolution=SIZE,scene_change_seconds=10,ai_images=6,source_image_resolution=[1024,576],dissolve_seconds=2,depth_aware_effects=data.get('version',1)>=2,publish=False,compose_seconds=round(time.monotonic()-started,2),**audio_report)
 (out/'quality-report.json').write_text(json.dumps(report,indent=2))
 # One honest preview contact sheet for browsing the result.
 sheet=Image.new('RGB',(1280,1080))
 for i,im in enumerate(images):sheet.paste(im.resize((640,360)),((i%2)*640,(i//2)*360))
 sheet.save(out/'scene-preview.jpg',quality=92);print(json.dumps(report),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('stage',choices=['plan','image','music','nature','compose']);p.add_argument('--out',type=Path,default=Path('output/relaxation-preview'));p.add_argument('--run-id',default='local');p.add_argument('--index',type=int,choices=range(100),default=0)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 if a.stage=='plan':plan(a.out,a.run_id)
 elif a.stage=='image':image(a.out,a.index)
 else:globals()[a.stage](a.out)
