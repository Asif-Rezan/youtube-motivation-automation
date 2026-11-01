"""Deterministic CPU puppet-animation demo, independent of production uploads."""
import argparse
import json
import math
from pathlib import Path
import subprocess
import wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS, SECONDS = 1280, 720, 24, 18
TEXT = ('Hi! I am Sami. Watch me walk, wave, and talk! '
        'Every big adventure begins with one little step. '
        'Try again, keep learning, and celebrate your progress!')


def render(root):
    root.mkdir(parents=True, exist_ok=True)
    voice = root/'voice.wav'
    subprocess.run(['espeak-ng', '-s', '142', '-p', '62', '-w', str(voice), TEXT], check=True)
    with wave.open(str(voice)) as source:
        rate = source.getframerate()
        samples = np.frombuffer(source.readframes(source.getnframes()), dtype='<i2').astype(float)/32768
    if len(samples)/rate > SECONDS:
        raise RuntimeError('Narration exceeds animation')
    font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
    title_font = ImageFont.truetype(font_path, 34)
    caption_font = ImageFont.truetype(font_path, 27)
    small_font = ImageFont.truetype(font_path, 18)
    output = root/'character-animation-demo.mp4'
    proc = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
        '-s', f'{W}x{H}', '-r', str(FPS), '-i', 'pipe:0', '-i', str(voice),
        '-filter_complex', '[1:a]apad,afade=t=out:st=17:d=1[a]', '-map', '0:v', '-map', '[a]',
        '-t', str(SECONDS), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20',
        '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-movflags', '+faststart', str(output)], stdin=subprocess.PIPE)
    def segment(draw, points, color, width):
        draw.line(points, fill='#293858', width=width+7, joint='curve')
        draw.line(points, fill=color, width=width, joint='curve')
        for x,y in points[1:-1]:
            draw.ellipse((x-width/2,y-width/2,x+width/2,y+width/2), fill=color)
    captions = [(0, 4, 'Hi! I am Sami. Watch me walk, wave, and talk!'),
                (4, 10, 'Every big adventure begins with one little step.'),
                (10, 15.5, 'Try again, keep learning, and celebrate your progress!'),
                (15.5, 18, 'ONE LITTLE STEP. ONE BIG ADVENTURE!')]
    try:
        for frame in range(FPS*SECONDS):
            t = frame/FPS
            im = Image.new('RGB', (W,H), '#BFEFFA')
            d = ImageDraw.Draw(im)
            d.ellipse((1050,65,1170,185), fill='#FFD96B')
            for cx, cy in [(90,140),(470,100),(900,190)]:
                cx = (cx+t*7) % 1500-80
                for dx,dy,r in [(0,0,32),(40,-15,45),(85,0,30)]:
                    d.ellipse((cx+dx-r,cy+dy-r,cx+dx+r,cy+dy+r), fill='#FFFFFF')
            d.ellipse((-200,410,850,930), fill='#8DD9AE')
            d.ellipse((650,385,1500,950), fill='#73C8A4')
            d.rectangle((0,555,W,H), fill='#4EA77C')
            d.rounded_rectangle((360,80,920,140), radius=22, fill='#FFFFFF')
            d.text((640,109), 'LET\'S TAKE A LITTLE STEP!', font=title_font, fill='#293858', anchor='mm')
            walking = t < 4
            phase = t*2*math.pi*1.6
            x = 270+min(t/4,1)*370
            jump = max(0, math.sin((t-15.5)*math.pi*1.3))*65 if t>15.5 else 0
            bob = math.sin(phase*2)*4 if walking else math.sin(t*3)*2
            y = 355+bob-jump
            d.ellipse((x-83,575-jump*.1,x+83,598-jump*.1), fill='#398565')
            # Jointed legs; opposite feet swing during the entrance walk.
            for side in (-1,1):
                swing = math.sin(phase)*side if walking else side*.12
                hip=(x+side*23,y+110)
                knee=(x+side*25+swing*22,y+156-abs(swing)*8)
                foot=(x+side*30+swing*45,y+222- max(0,swing)*20)
                segment(d,[hip,knee,foot],'#415FA4',26)
                d.rounded_rectangle((foot[0]-23,foot[1]-8,foot[0]+30,foot[1]+14),radius=9,fill='#F9CA67',outline='#293858',width=4)
            d.rounded_rectangle((x-56,y-4,x+56,y+117),radius=27,fill='#FF786C',outline='#293858',width=5)
            d.ellipse((x-18,y+32,x+18,y+68),fill='#FFE486')
            # Left hand rests/sways. Right arm waves with an articulated elbow.
            segment(d,[(x-48,y+15),(x-76,y+65),(x-80+(math.sin(phase)*15 if walking else 0),y+105)],'#FF786C',25)
            d.ellipse((x-94,y+88,x-65,y+118),fill='#FFD4AC',outline='#293858',width=3)
            wave_angle = math.sin(t*8)*.35
            shoulder=(x+48,y+16)
            elbow=(x+91,y-20)
            hand=(x+100+math.sin(wave_angle)*57,y-92+math.cos(wave_angle)*8)
            segment(d,[shoulder,elbow,hand],'#FF786C',25)
            d.ellipse((hand[0]-17,hand[1]-24,hand[0]+17,hand[1]+13),fill='#FFD4AC',outline='#293858',width=3)
            for finger in range(3):
                fx=hand[0]-11+finger*10
                d.line((fx,hand[1]-10,fx+math.sin(t*8)*3,hand[1]-31),fill='#FFD4AC',width=7)
            # Head, hair, brows and periodic eye blinks.
            hx=x+math.sin(t*2)*3
            hy=y-79
            d.rounded_rectangle((hx-67,hy-72,hx+67,hy+67),radius=52,fill='#FFD4AC',outline='#293858',width=5)
            d.pieslice((hx-74,hy-94,hx+73,hy+37),180,360,fill='#30344D')
            for dx,dy,r in [(-43,-64,26),(-9,-79,30),(28,-70,29)]:
                d.ellipse((hx+dx-r,hy+dy-r,hx+dx+r,hy+dy+r),fill='#30344D')
            blink = (t % 3.3) < .13
            for dx in (-25,25):
                ex=hx+dx
                d.arc((ex-13,hy-29,ex+13,hy-12),190,340,fill='#30344D',width=4)
                if blink:
                    d.line((ex-8,hy-2,ex+8,hy-2),fill='#293858',width=4)
                else:
                    d.ellipse((ex-8,hy-12,ex+8,hy+8),fill='#FFFFFF')
                    d.ellipse((ex-4,hy-8,ex+5,hy+6),fill='#293858')
            chunk=samples[int(t*rate):int((t+1/FPS)*rate)]
            rms=float(np.sqrt(np.mean(chunk**2))) if len(chunk) else 0
            opening=min(22,rms*180)
            if opening>3:
                d.ellipse((hx-18,hy+25-opening*.3,hx+18,hy+29+opening),fill='#713D50',outline='#293858',width=2)
                d.arc((hx-12,hy+29,hx+12,hy+31+opening),0,180,fill='#F397A6',width=5)
            else:
                d.arc((hx-18,hy+12,hx+18,hy+37),0,180,fill='#713D50',width=4)
            # Foreground flowers give independent depth, without flashing effects.
            for fx in (90,180,1060,1170):
                sway=math.sin(t*2+fx)*5
                d.line((fx,615,fx+sway,584),fill='#236C56',width=5)
                d.ellipse((fx+sway-9,575,fx+sway+9,593),fill='#FFE486')
            caption=next(text for start,end,text in captions if start<=t<end)
            d.rounded_rectangle((110,630,1170,690),radius=18,fill='#25354D')
            d.text((640,660),caption,font=caption_font,fill='white',anchor='mm')
            d.text((25,25),'CPU PUPPET ANIMATION DEMO',font=small_font,fill='#34556A')
            if frame in (48,144,240,384):
                im.save(root/f'frame-{frame:03}.jpg')
            proc.stdin.write(im.tobytes())
    finally:
        proc.stdin.close()
    if proc.wait():
        raise RuntimeError('Animation encoding failed')
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(output)]))
    assert abs(float(info['format']['duration'])-SECONDS)<.1
    assert any(s['codec_type']=='audio' for s in info['streams'])
    subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(output),'-f','null','-'],check=True)
    (root/'validation.json').write_text(json.dumps({'passed':True,'duration':SECONDS,'frames':FPS*SECONDS,
        'width':W,'height':H,'renderer':'Pillow CPU puppet animation','features':['walk','wave','blink','audio-driven mouth','jump'],
        'voice':'espeak-ng demo voice; production narration unchanged'},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=Path('output/character-animation-demo'))
    render(parser.parse_args().output)
