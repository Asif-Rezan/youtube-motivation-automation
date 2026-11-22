"""Fixed-view garden composition of the continuous captured walking sample."""
from pathlib import Path
import json,math,subprocess,wave,os
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
P=Path(os.environ.get('FITNESS_REVIEW_DIR','/Users/asif/Documents/fitness-walk-review'));FPS=24;N=240;W,H=1920,1080;RATE=48000
contacts=json.loads((P/'contact-shadows.json').read_text())
metrics=P/'walk-metrics.json'
rows=(json.loads(metrics.read_text()) if metrics.exists() else
      [{'feet':{side:{'contact':feet[side]['height']<.015} for side in ['l','r']}} for feet in contacts])
audio=np.zeros(RATE*10,dtype=np.float32)
for beat in range(17):
    start=round(beat*.6*RATE)
    if start>=len(audio):break
    n=min(round(.5*RATE),len(audio)-start);t=np.arange(n)/RATE
    audio[start:start+n]+=sum(np.sin(math.tau*hz*t) for hz in [220,277.18,329.63])*.012*np.exp(-8*t)
rng=np.random.default_rng(382)
for side in ['l','r']:
    before=True
    for i,row in enumerate(rows):
        contact=row['feet'][side]['contact']
        if contact and not before:
            start=round(i/FPS*RATE);n=min(round(.09*RATE),len(audio)-start);t=np.arange(n)/RATE
            step=(np.sin(math.tau*95*t)*.055+rng.normal(0,.009,n))*np.exp(-55*t)
            audio[start:start+n]+=step
        before=contact
with wave.open(str(P/'audio.wav'),'wb') as wav:
    wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(RATE)
    wav.writeframes((np.clip(audio,-.95,.95)*32767).astype('<i2').tobytes())
missing=[f for f in range(1,N+1) if not (P/'frames'/f'f-{f:04d}.png').exists()]
if missing:raise RuntimeError(f'Missing frames {missing[:8]}')
background=Image.open('/Users/asif/Documents/Projects/youtube-motivation-backup/environment/backgrounds/tropical-yoga-garden-v1.png').convert('RGBA').resize((W,H),Image.Resampling.LANCZOS)
font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf',32)
small=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',24)
output=P/os.environ.get('FITNESS_VIDEO_NAME','kat-continuous-human-walk-10s.mp4')
proc=subprocess.Popen(['ffmpeg','-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s','1920x1080','-r','24','-i','-',
    '-i',str(P/'audio.wav'),'-c:v','libx264','-threads','3','-preset','fast','-crf','17','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-t','10','-movflags','+faststart',str(output)],stdin=subprocess.PIPE)
for f,row in enumerate(rows,1):
    im=background.copy();shadow=Image.new('RGBA',(W,H));d=ImageDraw.Draw(shadow)
    for foot in contacts[f-1].values():
        patch=Image.new('RGBA',(W,H));pd=ImageDraw.Draw(patch);height=max(0,foot['height']);opacity=round(135/(1+height*18))
        if len(foot['outline'])>=3:pd.polygon([tuple(p) for p in foot['outline']],fill=(14,26,8,opacity))
        shadow.alpha_composite(patch.filter(ImageFilter.GaussianBlur(3+height*75)))
    im.alpha_composite(shadow)
    im.alpha_composite(Image.open(P/'frames'/f'f-{f:04d}.png').convert('RGBA'))
    ui=Image.new('RGBA',(W,H));d=ImageDraw.Draw(ui)
    d.rounded_rectangle((42,30,815,124),radius=16,fill=(14,35,29,225))
    d.text((66,43),'WALK · TURN · WALK BACK',font=font,fill=(255,246,222))
    d.text((68,87),os.environ.get('FITNESS_REVIEW_LABEL','Captured body motion · Fixed camera'),font=small,fill=(214,231,216))
    d.rounded_rectangle((42,1007,912,1059),radius=14,fill=(14,35,29,215))
    d.text((62,1018),'CMU body motion · Heel-to-toe foot roll · Foot contact IK',font=small,fill='white')
    im.alpha_composite(ui);proc.stdin.write(im.convert('RGB').tobytes())
    if f in [1,48,96,144,192,240]:im.convert('RGB').save(P/f'final-{f}.jpg',quality=96)
proc.stdin.close()
if proc.wait():raise RuntimeError('Video encoder failed')
print(output)
