"""CPU composition, timed coaching UI, title-specific thumbnail and final media gates."""
import argparse,colorsys,json,math,subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageFilter,ImageEnhance,ImageOps
from .timeline import FRAMES_PER_SHARD,SHARDS
ROOT=Path(__file__).resolve().parents[1]
SIZE=(1920,1080)
def font(size):
    for path in ['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf','/System/Library/Fonts/Supplemental/Arial Bold.ttf']:
        if Path(path).exists():return ImageFont.truetype(path,size)
    raise FileNotFoundError('A production TrueType font is required')
def textfit(draw,text,width,size=40):
    while draw.textbbox((0,0),text,font=font(size))[2]>width and size>16:size-=1
    return font(size)
def hull(points):
    pts=sorted(set(map(tuple,points)))
    def cross(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    halves=[]
    for sequence in [pts,pts[::-1]]:
        half=[]
        for p in sequence:
            while len(half)>1 and cross(half[-2],half[-1],p)<=0:half.pop()
            half.append(p)
        halves.append(half[:-1])
    return halves[0]+halves[1]
def background():return Image.open(ROOT/'environment/backgrounds/tropical-yoga-garden-v1.png').convert('RGBA').resize(SIZE,Image.Resampling.LANCZOS)
def check_frame(path):
    with Image.open(path) as im:
        im.load()
        if im.size!=SIZE:raise ValueError('Rendered character frame has wrong resolution: '+str(path))
def ui(im,plan,frame):
    from .sequence import compile_sequence
    sequence=compile_sequence(plan)
    row=next(r for r in sequence if r['start_frame']<=frame<r['start_frame']+r['frames'])
    t=frame/24;cycle=row['rep']-1;phase=(frame-row['start_frame'])/row['frames']*12
    name=next((n for n,start,end in [('ready',0,2.2),('lift',2.2,4.3),('hold',4.3,6.3),('lower',6.3,8.7),('reset',8.7,12)] if start<=phase<end),'reset')
    layer=Image.new('RGBA',SIZE);d=ImageDraw.Draw(layer)
    d.rounded_rectangle((40,22,1880,88),20,fill=(12,29,26,225))
    title=plan['title'];d.text((68,35),title,font=textfit(d,title,1780,33),fill='white')
    d.rounded_rectangle((1340,210,1875,600),28,fill=(13,34,29,225))
    d.text((1370,239),f'REP {cycle+1} / 5',font=font(37),fill=(255,219,104))
    cue=plan['cycles'][cycle][name];words=cue.split();lines=['']
    for word in words:
        candidate=(lines[-1]+' '+word).strip()
        if d.textbbox((0,0),candidate,font=font(37))[2]>465:lines.append(word)
        else:lines[-1]=candidate
    for j,line in enumerate(lines):d.text((1370,305+j*48),line,font=font(37),fill='white')
    remaining=max(0,round(60-t));d.text((1450,473),f'{remaining//60:02d}:{remaining%60:02d}',font=font(68),fill=(255,238,187))
    d.rounded_rectangle((40,1000,1880,1052),20,fill=(13,34,29,220))
    d.rounded_rectangle((48,1008,48+max(1,1824*(frame+1)/1440),1044),14,fill=(238,182,78))
    im.alpha_composite(layer)
    return im
def shard(out,index):
    plan=json.loads((out/'plan.json').read_text());folder=out/f'render-{index:02d}'
    contacts=json.loads((folder/'contacts.json').read_text());bg=background()
    expected=list(range(index*FRAMES_PER_SHARD,(index+1)*FRAMES_PER_SHARD))
    if [row['frame'] for row in contacts]!=expected:raise ValueError('Missing, duplicated or out-of-order render frames')
    for row in contacts:check_frame(folder/f'f-{row["frame"]:04d}.png')
    target=out/f'visual-{index:02d}.mp4'
    proc=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1920x1080','-r','24','-i','-',
        '-c:v','libx264','-threads','2','-preset','medium','-crf','17','-pix_fmt','yuv420p','-movflags','+faststart',str(target)],stdin=subprocess.PIPE)
    try:
        for row in contacts:
            im=bg.copy();shadow=Image.new('RGBA',SIZE);d=ImageDraw.Draw(shadow)
            for foot in row['feet'].values():
                points=hull(foot['points'])
                if len(points)>2:d.polygon(points,fill=(12,25,8,115))
            im.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(4)))
            im.alpha_composite(Image.open(folder/f'f-{row["frame"]:04d}.png').convert('RGBA'))
            im=ui(im,plan,row['frame']);proc.stdin.write(im.convert('RGB').tobytes())
    finally:proc.stdin.close()
    if proc.wait():raise RuntimeError('Fitness video encoding failed')
    if len(contacts)!=FRAMES_PER_SHARD:raise ValueError(f'A production shard must contain exactly {FRAMES_PER_SHARD} frames')

def thumbnail(out):
    plan=json.loads((out/'plan.json').read_text());brief=plan['thumbnail'];bg=background();im=Image.new('RGB',SIZE)
    hue=brief['accent_hue']/360
    colors=[tuple(round(c*255) for c in colorsys.hsv_to_rgb(h,.72,.95)) for h in [hue,(hue+.5)%1]]
    panels=[];characters=[]
    for i,name in enumerate(['before','after']):
        panel=bg.crop((i*960,0,(i+1)*960,1080)).convert('RGB')
        tint=Image.new('RGB',panel.size,colors[i]);panel=Image.blend(panel,tint,.22)
        char=Image.open(out/f'thumbnail-{name}.png').convert('RGBA');box=char.getbbox()
        if not box:raise ValueError('Thumbnail character is empty')
        char=char.crop(box)
        focus=brief['focus']
        if focus=='calves':char=char.crop((0,int(char.height*.39),char.width,char.height))
        elif focus=='posture':char=char.crop((0,0,char.width,int(char.height*.86)))
        char.thumbnail((840,790),Image.Resampling.LANCZOS)
        characters.append(char)
        panel=panel.convert('RGBA');panel.alpha_composite(char,((960-char.width)//2,1050-char.height))
        panels.append(panel.convert('RGB'))
    layout=brief.get('layout','split')
    if layout=='inset':
        im=bg.convert('RGB');im=Image.blend(im,Image.new('RGB',SIZE,colors[1]),.18)
        im.paste(panels[1],(960,0));small=panels[0].resize((680,765),Image.Resampling.LANCZOS)
        im.paste(small,(65,280));d=ImageDraw.Draw(im);d.rounded_rectangle((55,270,755,1055),22,outline=(255,246,214),width=12)
    elif layout=='diagonal':
        canvases=[]
        for i,char in enumerate(characters):
            canvas=Image.blend(bg.convert('RGB'),Image.new('RGB',SIZE,colors[i]),.22).convert('RGBA')
            canvas.alpha_composite(char,(i*960+(960-char.width)//2,1050-char.height));canvases.append(canvas.convert('RGB'))
        mask=Image.new('L',SIZE);ImageDraw.Draw(mask).polygon([(1120,0),(1920,0),(1920,1080),(820,1080)],fill=255)
        im=Image.composite(canvases[1],canvases[0],mask)
        d=ImageDraw.Draw(im);d.line([(1120,0),(820,1080)],fill=(255,245,214),width=18)
    else:
        im.paste(panels[0],(0,0));im.paste(panels[1],(960,0))
        d=ImageDraw.Draw(im);d.line([(960,0),(960,1080)],fill=(255,245,214),width=18)
    d=ImageDraw.Draw(im)
    def outlined(x,y,text,width,size,fill):
        f=textfit(d,text,width,size);d.text((x,y),text,font=f,fill=fill,stroke_width=9,stroke_fill=(24,18,14))
    outlined(45,30,brief['headline'].upper(),1810,105,(255,248,223))
    outlined(55,185,'BEFORE · '+brief['before_label'].upper(),835,49,colors[1])
    outlined(1020,185,'AFTER · '+brief['after_label'].upper(),835,49,colors[0])
    # A high-contrast red curved direction cue preserves the before/after comparison.
    d.line([(800,730),(950,665),(1110,730)],fill=(255,54,49),width=25)
    d.polygon([(1110,730),(1040,665),(1035,760)],fill=(255,54,49))
    im.save(out/'thumbnail.jpg',quality=96)
    im.save(out/'thumbnail.png')
    (out/'thumbnail-brief.json').write_text(json.dumps(dict(title=plan['title'],**brief),indent=2))

def assemble(out):
    listing=out/'visuals.txt'
    listing.write_text(''.join(f"file '{(out/f'visual-{i:02d}.mp4').resolve()}'\n" for i in range(SHARDS)))
    subprocess.run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(listing),'-i',str(out/'voice.wav'),'-i',str(out/'music.wav'),
        '-filter_complex','[1:a]highpass=f=70,loudnorm=I=-17:TP=-2:LRA=7,asplit=2[v][side];[2:a]volume=0.18[m];[m][side]sidechaincompress=threshold=0.025:ratio=6:attack=20:release=400[duck];[v][duck]amix=inputs=2:normalize=0,loudnorm=I=-16:TP=-1:LRA=8[a]',
        '-map','0:v','-map','[a]','-c:v','copy','-c:a','aac','-b:a','192k','-ar','48000','-t','60','-movflags','+faststart',str(out/'fitness-preview.mp4')],check=True)
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(out/'fitness-preview.mp4')]))
    video=next(x for x in info['streams'] if x['codec_type']=='video');audio=next(x for x in info['streams'] if x['codec_type']=='audio')
    assert (video['width'],video['height'])==SIZE
    assert int(video['nb_frames'])==1440 and abs(float(info['format']['duration'])-60)<.1
    assert audio['codec_name']=='aac'
    subprocess.run(['ffmpeg','-v','error','-i',str(out/'fitness-preview.mp4'),'-f','null','-'],check=True)
    thumbnail(out)
    (out/'quality-report.json').write_text(json.dumps(dict(seconds=60,frames=1440,fps=24,resolution=SIZE,
        thumbnail=[1920,1080],models=json.loads((out/'plan.json').read_text())['models'],voice=True,ai_music=True,published=False),indent=2))
    print('FITNESS_PREVIEW_VERIFIED',out/'fitness-preview.mp4',flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['shard','assemble','thumbnail']);p.add_argument('--out',type=Path,required=True);p.add_argument('--index',type=int,default=0)
    a=p.parse_args();shard(a.out,a.index) if a.stage=='shard' else globals()[a.stage](a.out)
