"""Prepare timed voice cues, then composite the reviewed Blender frames."""
import json, math, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT=Path('/Users/asif/Documents/fitness-pilates-review')
FPS=24
RATE=48000
DURATION=12
CUES=[(0,'Stand tall.'),(1,'Shift forward.'),(2.5,'Lift your heels.'),
      (4.6,'Hold.'),(5.6,'Lower slowly.'),(8.7,'Stand tall.')]
def audio():
    voice=np.zeros(RATE*DURATION,dtype=np.float32)
    for i,(at,text) in enumerate(CUES):
        path=OUT/f'cue-{i}.aiff'
        subprocess.run(['say','-v','Samantha','-r','155','-o',str(path),text],check=True)
        result=subprocess.run(['ffmpeg','-v','error','-i',str(path),'-f','f32le','-ac','1','-ar',str(RATE),'-'],capture_output=True,check=True)
        samples=np.frombuffer(result.stdout,dtype='<f4')
        start=round(at*RATE);end=min(len(voice),start+len(samples))
        voice[start:end]+=samples[:end-start]
    voice*=.76/max(.01,np.max(np.abs(voice)))
    envelope=[]
    for i in range(FPS*DURATION):
        v=voice[max(0,int((i/FPS-.015)*RATE)):min(len(voice),int((i/FPS+.035)*RATE))]
        envelope.append(float(np.sqrt(np.mean(v*v))))
    scale=max(.01,np.percentile(envelope,90))
    envelope=np.clip(np.array(envelope)/scale,0,1)
    envelope=np.convolve(envelope,[.15,.7,.15],mode='same')
    (OUT/'speech-envelope.json').write_text(json.dumps(envelope.tolist()))
    music=np.zeros_like(voice)
    for beat in range(21):
        start=round(beat*60/100*RATE)
        if start>=len(music):break
        length=min(round(.42*RATE),len(music)-start)
        t=np.arange(length)/RATE
        # Quiet original plucked chord and soft kick under the voice.
        chord=sum(np.sin(2*math.pi*freq*t)*np.exp(-9*t) for freq in [220,277.18,329.63])*.014
        kick=np.sin(2*math.pi*(54*t+12*(1-np.exp(-30*t))/30))*np.exp(-22*t)*.045
        music[start:start+length]+=chord+kick
    mixed=np.tanh((voice+music)*1.04)*.94
    with wave.open(str(OUT/'audio.wav'),'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(RATE)
        wav.writeframes((mixed*32767).astype('<i2').tobytes())

def compose():
    frames=OUT/'frames'
    missing=[i for i in range(1,289) if not (frames/f'f-{i:04d}.png').exists()]
    if missing:raise RuntimeError(f'Missing rendered frames: {missing[:8]}')
    W,H=1920,1080
    background=Image.open('/Users/asif/Documents/Projects/youtube-motivation-backup/environment/backgrounds/tropical-yoga-garden-v1.png').convert('RGBA').resize((W,H),Image.Resampling.LANCZOS)
    review=json.loads((OUT/'contact-review.json').read_text())
    fontpath='/System/Library/Fonts/Supplemental/Arial Bold.ttf'
    large=ImageFont.truetype(fontpath,42);small=ImageFont.truetype(fontpath,27)
    output=OUT/'kat-pilates-heel-raise-12s.mp4'
    proc=subprocess.Popen(['ffmpeg','-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s','1920x1080','-r','24','-i','-',
        '-i',str(OUT/'audio.wav'),'-c:v','libx264','-threads','3','-preset','fast','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-t','12','-movflags','+faststart',str(output)],stdin=subprocess.PIPE)
    for f in range(1,289):
        t=(f-1)/FPS
        im=background.copy()
        shadow=Image.new('RGBA',(W,H));draw=ImageDraw.Draw(shadow)
        for contact in review['frames'][f-1]['contacts']:
            x,y=contact['pixel']
            y-=60  # Register the 3D ground contacts to the garden plate's mat.
            draw.ellipse((x-44,y-7,x+44,y+13),fill=(22,25,10,90))
        im.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(8)))
        im.alpha_composite(Image.open(frames/f'f-{f:04d}.png').convert('RGBA'),dest=(0,-60))
        ui=Image.new('RGBA',(W,H));d=ImageDraw.Draw(ui)
        d.rounded_rectangle((45,40,715,158),radius=20,fill=(14,35,29,230))
        d.text((68,55),'STANDING HEEL RAISE',font=large,fill=(255,246,222))
        d.text((70,112),'Continuous view · Slow controlled movement',font=small,fill=(208,231,212))
        cue='Stand tall' if t<1 or t>=10 else 'Shift forward' if t<2.5 else 'Lift slowly' if t<4.5 else 'Hold' if t<5.5 else 'Lower slowly' if t<8.5 else 'Reset'
        d.rounded_rectangle((1440,48,1875,190),radius=24,fill=(14,35,29,225))
        d.text((1472,64),f'{math.ceil(12-t):02d} sec',font=large,fill='white')
        d.text((1472,128),cue,font=small,fill=(245,211,135))
        d.rounded_rectangle((45,997,795,1054),radius=16,fill=(14,35,29,220))
        d.text((66,1010),'Animation review · Form review pending',font=small,fill='white')
        d.rounded_rectangle((45,1065,45+round(1830*(f/288)),1072),radius=3,fill=(231,188,104))
        im.alpha_composite(ui)
        proc.stdin.write(im.convert('RGB').tobytes())
        if f in [1,61,109,181,239]:im.convert('RGB').save(OUT/f'review-{f}.jpg',quality=96)
    proc.stdin.close()
    if proc.wait():raise RuntimeError('ffmpeg failed')
    print(output)

if '--audio' in sys.argv:audio()
else:compose()
