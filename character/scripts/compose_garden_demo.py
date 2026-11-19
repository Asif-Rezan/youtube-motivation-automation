"""Composite the rendered Daz character over the approved static garden plate."""
from PIL import Image,ImageDraw,ImageFont,ImageFilter
from pathlib import Path
import subprocess,math,argparse
ROOT=Path('/Users/asif/Documents/fitness-garden-demo')
BG=Path('/Users/asif/Documents/Projects/youtube-motivation-backup/environment/backgrounds/tropical-yoga-garden-v1.png')
W,H=1280,720;FPS=12
args=argparse.ArgumentParser();args.add_argument('--frames',type=int,default=720);args.add_argument('--output',default='garden-workout-dance-60s.mp4');opt=args.parse_args()
bg=Image.open(BG).convert('RGBA').resize((W,H),Image.Resampling.LANCZOS)
font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf',24)
small=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',18)
labels=['ARM WARM-UP','JUMPING JACKS','SQUATS','KNEE LIFTS','LUNGES','PUSH-UPS','DANCE FINISH']
proc=subprocess.Popen(['ffmpeg','-y','-hide_banner','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-i',str(ROOT/'original-workout-beat.wav'),'-vf','minterpolate=fps=24:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,tpad=stop_mode=clone:stop_duration=0.25','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-t',str(opt.frames/FPS),'-movflags','+faststart',str(ROOT/opt.output)],stdin=subprocess.PIPE)
for f in range(1,opt.frames+1):
 t=(f-1)/FPS;seg=min(6,int(t//8));im=bg.copy()
 sh=Image.new('RGBA',(W,H));d=ImageDraw.Draw(sh)
 cx=640+ (55*math.sin((t-48)*math.tau/2.5) if seg==6 else 0)
 if seg==5:d.ellipse((cx-220,594,cx+220,626),fill=(10,20,8,65))
 else:d.ellipse((cx-90,590,cx+90,626),fill=(10,20,8,65))
 im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(13)))
 char=Image.open(ROOT/'frames'/f'f-{f:04d}.png').convert('RGBA').resize((W,H),Image.Resampling.LANCZOS)
 # A short fade masks the cut into and out of the floor routine.
 fade=1
 for cut in [40,48]:
  if abs(t-cut)<.22:fade=min(fade,abs(t-cut)/.22)
 if fade<1:char.putalpha(char.getchannel('A').point(lambda a:round(a*fade)))
 im.alpha_composite(char)
 ui=Image.new('RGBA',(W,H));d=ImageDraw.Draw(ui)
 d.rounded_rectangle((28,25,505,91),radius=15,fill=(12,31,25,220))
 d.text((46,36),labels[seg],font=font,fill=(255,255,255,255))
 d.text((46,65),'ANIMATION DEMO — NOT A WORKOUT GUIDE',font=small,fill=(246,210,140,255))
 remain=max(0,60-int(t));d.rounded_rectangle((1140,25,1252,91),radius=15,fill=(12,31,25,220))
 d.text((1162,43),f'{remain:02d}s',font=font,fill='white')
 d.rounded_rectangle((30,689,1250,696),radius=3,fill=(255,255,255,100))
 d.rounded_rectangle((30,689,max(36,30+1220*t/60),696),radius=3,fill=(246,195,95,255))
 im.alpha_composite(ui)
 proc.stdin.write(im.convert('RGB').tobytes())
proc.stdin.close()
if proc.wait():raise SystemExit('ffmpeg encode failed')
print(ROOT/opt.output)
