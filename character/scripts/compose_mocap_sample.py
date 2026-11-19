from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageFilter
import subprocess,json,time,math
P=Path('/Users/asif/Documents/fitness-mocap-sample');W,H,FPS=1920,1080,24
deadline=time.monotonic()+240
while not (P/'shadows.json').exists():
 if time.monotonic()>deadline:raise RuntimeError('Motion prep did not finish')
 time.sleep(.2)
shadows=json.loads((P/'shadows.json').read_text())
bg=Image.open('/Users/asif/Documents/Projects/youtube-motivation-backup/environment/backgrounds/tropical-yoga-garden-v1.png').convert('RGBA').resize((W,H),Image.Resampling.LANCZOS)
font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf',34);small=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',26)
out=P/'kat-real-mocap-14s.mp4'
proc=subprocess.Popen(['ffmpeg','-y','-hide_banner','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-i',str(P/'sample-audio.wav'),'-c:v','libx264','-threads','3','-preset','fast','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-t','14','-movflags','+faststart',str(out)],stdin=subprocess.PIPE)
for f in range(1,337):
 path=P/'frames'/f'f-{f:04d}.png';deadline=time.monotonic()+240
 while True:
  try:char=Image.open(path).convert('RGBA');break
  except (FileNotFoundError,OSError,SyntaxError,ValueError):
   if time.monotonic()>deadline:raise RuntimeError(f'Render stopped at frame {f}')
   time.sleep(.1)
 t=(f-1)/FPS;im=bg.copy();shadow=Image.new('RGBA',(W,H));d=ImageDraw.Draw(shadow)
 for x,y,z in shadows[f-1]:
  h=max(0,z-.018);radius=43+min(35,h*130);alpha=round(88/(1+h*7));d.ellipse((x-radius,y-11-h*10,x+radius,y+11+h*10),fill=(12,22,8,alpha))
 im.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(10)))
 if abs(t-8)<.16:char.putalpha(char.getchannel('A').point(lambda v:round(v*abs(t-8)/.16)))
 im.alpha_composite(char)
 ui=Image.new('RGBA',(W,H));d=ImageDraw.Draw(ui);d.rounded_rectangle((36,30,710,133),radius=20,fill=(14,32,27,215))
 d.text((60,45),'MOTION CAPTURE  /  '+('EXERCISE' if t<8 else 'DANCE'),font=font,fill='white');d.text((60,91),'Captured human motion • Same character',font=small,fill=(240,214,157,255))
 d.rounded_rectangle((36,1010,955,1060),radius=14,fill=(14,32,27,200));d.text((56,1020),'Motion: CMU Graphics Lab  |  Animation demo, not workout instruction',font=small,fill=(236,240,235,255))
 im.alpha_composite(ui);proc.stdin.write(im.convert('RGB').tobytes())
 if f in [24,72,144,216,264,312]:im.convert('RGB').save(P/f'final-{f}.jpg',quality=95)
 if f%48:path.unlink()
 if f%48==0:print(f'Composited {f}/336',flush=True)
proc.stdin.close()
if proc.wait():raise RuntimeError('Video encoding failed')
print(out,flush=True)
