"""Native 1080p/24fps compositor. Consume frames as rendered to bound disk use."""
from PIL import Image,ImageDraw,ImageFont,ImageFilter
from pathlib import Path
import subprocess,math,time
P=Path('/Users/asif/Documents/fitness-garden-demo');W,H,FPS=1920,1080,24
BG=Path('/Users/asif/Documents/Projects/youtube-motivation-backup/environment/backgrounds/tropical-yoga-garden-v1.png')
bg=Image.open(BG).convert('RGBA').resize((W,H),Image.Resampling.LANCZOS)
font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf',36)
small=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',27)
labels=['ARM WARM-UP','JUMPING JACKS','SQUATS','KNEE LIFTS','LUNGES','PUSH-UPS','DANCE FINISH']
out=P/'garden-workout-dance-60s-hq.mp4'
proc=subprocess.Popen(['ffmpeg','-y','-hide_banner','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-i',str(P/'demo-voice-and-music.wav'),'-c:v','libx264','-threads','3','-preset','fast','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-t','60','-movflags','+faststart',str(out)],stdin=subprocess.PIPE)
for f in range(1,1441):
 path=P/'frames-hq'/f'f-{f:04d}.png';deadline=time.monotonic()+240
 while True:
  try:
   char=Image.open(path).convert('RGBA');break
  except (FileNotFoundError,OSError,SyntaxError,ValueError):
   if time.monotonic()>deadline:raise RuntimeError(f'Render stalled at frame {f}')
   time.sleep(.15)
 t=(f-1)/FPS;seg=min(6,int(t//8));im=bg.copy()
 shadow=Image.new('RGBA',(W,H));d=ImageDraw.Draw(shadow);cx=960+(82*math.sin((t-48)*math.tau/2.5) if seg==6 else 0)
 if seg==5:d.ellipse((cx-330,891,cx+330,939),fill=(10,20,8,65))
 else:d.ellipse((cx-135,885,cx+135,939),fill=(10,20,8,65))
 im.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(20)))
 fade=1
 for cut in [40,48]:
  if abs(t-cut)<.22:fade=min(fade,abs(t-cut)/.22)
 if fade<1:char.putalpha(char.getchannel('A').point(lambda a:round(a*fade)))
 im.alpha_composite(char)
 ui=Image.new('RGBA',(W,H));d=ImageDraw.Draw(ui)
 d.rounded_rectangle((42,38,758,137),radius=22,fill=(12,31,25,220));d.text((69,54),labels[seg],font=font,fill='white')
 d.text((69,97),'ANIMATION DEMO — NOT A WORKOUT GUIDE',font=small,fill=(246,210,140,255))
 d.rounded_rectangle((1710,38,1878,137),radius=22,fill=(12,31,25,220));d.text((1743,65),f'{max(0,60-int(t)):02d}s',font=font,fill='white')
 d.rounded_rectangle((45,1034,1875,1044),radius=5,fill=(255,255,255,100));d.rounded_rectangle((45,1034,max(54,45+1830*t/60),1044),radius=5,fill=(246,195,95,255))
 im.alpha_composite(ui)
 proc.stdin.write(im.convert('RGB').tobytes())
 if f in [25,277,49,1045,1300]:im.convert('RGB').save(P/f'final-review-{f}.jpg',quality=95)
 if f%192: path.unlink()
 if f%192==0:print(f'Composited {f}/1440',flush=True)
proc.stdin.close()
if proc.wait():raise RuntimeError('Video encoding failed')
print(out,flush=True)
