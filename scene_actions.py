"""Small timed stories for CPU puppet scenes; no external inference calls.

Face coordinates are normalized to the cropped actor, never the whole scene.
Uncertain/multiple faces retain their original artwork rather than guessed eyes.
"""
import math
import re
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

VERSION = 'scene-stories-v1'


def smooth(value):
    value = max(0., min(1., value))
    return value * value * (3 - 2 * value)


def plan_scene(prompt, index=0):
    words = set(re.findall(r'[a-z]+', prompt.lower()))
    if words & {'sleep', 'sleepy', 'sleeping', 'bed', 'night', 'moon'}:
        kind, prop, action = 'rest', 'star', 'settle'
    elif words & {'rain', 'rainy', 'water', 'splash', 'puddle'}:
        kind, prop, action = 'rain', 'droplet', 'sway'
    elif words & {'ball', 'roll', 'rolling', 'kick', 'catch'}:
        kind, prop, action = 'play', 'ball', 'approach'
    elif words & {'rabbit', 'bunny', 'hare', 'hop', 'hopping', 'jump', 'jumping'}:
        kind, prop, action = 'discover', 'butterfly', 'two_hops'
    else:
        kind, prop, action = 'discover', 'butterfly', 'approach'
    return dict(version=VERSION, kind=kind, prop=prop, action=action,
                direction=1 if index % 2 == 0 else -1,
                beats=[dict(at=0., action='blink'), dict(at=.65, action='prop_enters'),
                       dict(at=1.35, action='look'), dict(at=2.1, action=action),
                       dict(at=4.1, action='close_up_reaction')])


def state_at(plan, t):
    progress = smooth((t - 2.1) / 1.7)
    hop = landing = 0.
    if plan['action'] == 'two_hops':
        for start in (2.1, 3.0):
            u = (t - start) / .65
            if 0 < u < 1:
                hop = math.sin(math.pi * u)
            landing += math.exp(-((t - start - .68) / .09)**2)
    blink = max(0., 1 - abs(t - .3) / .13)
    return dict(progress=progress, hop=hop, landing=landing, blink=blink,
                look=smooth((t - 1.35) / .5), reaction=smooth((t - 4.1) / .65),
                direction=plan['direction'])


def detect_face(actor):
    """Conservative dark-eye pair proposal, restricted to one opaque silhouette.

This is deliberately optional: full scenes with kids AND animals can have
multiple faces. Never apply a guessed blink to a whole multi-character group.
"""
    from scipy import ndimage
    pixels = np.asarray(actor)
    h, w = pixels.shape[:2]
    dark = (pixels[:, :, :3].max(axis=2) < 85) & (pixels[:, :, 3] > 240)
    dark[:int(h*.15)] = False
    dark[int(h*.7):] = False
    labels, count = ndimage.label(dark)
    candidates = []
    for label, region in enumerate(ndimage.find_objects(labels), 1):
        if region is None:
            continue
        ys, xs = region
        bw, bh = xs.stop-xs.start, ys.stop-ys.start
        area = int((labels[region] == label).sum())
        if w*.025 < bw < w*.19 and h*.025 < bh < h*.17 and area > w*h*.0008:
            candidates.append((xs.start, ys.start, xs.stop, ys.stop))
    pairs = []
    for i, a in enumerate(candidates):
        for b in candidates[i+1:]:
            ac, bc = ((a[0]+a[2])/2,(a[1]+a[3])/2), ((b[0]+b[2])/2,(b[1]+b[3])/2)
            gap = abs(ac[0]-bc[0])
            ratio = (a[3]-a[1])/(b[3]-b[1])
            if .12*w < gap < .42*w and abs(ac[1]-bc[1]) < .045*h and .6 < ratio < 1.7:
                pairs.append((a,b))
    if len(pairs) != 1:
        return None
    return dict(eyes=[[a[0]/w,a[1]/h,a[2]/w,a[3]/h] for a in pairs[0]], source='conservative-eye-pair')


def face_motion(actor, rig, state):
    if not rig:
        return actor
    image = actor.copy()
    w, h = image.size
    # Replace only the small verified eye region; eyelid color comes from fur/skin.
    for box in rig['eyes']:
        x0,y0,x1,y1 = [round(v*(w if i%2==0 else h)) for i,v in enumerate(box)]
        pad = max(1, round(w*.006))
        x0,y0,x1,y1 = max(0,x0-pad),max(0,y0-pad),min(w,x1+pad),min(h,y1+pad)
        if state['blink'] > 0 and x1>x0 and y1>y0:
            patch = image.crop((x0,y0,x1,y1))
            samples=[image.getpixel((max(0,min(w-1,x)),max(0,min(h-1,y))))
                     for x,y in [(x0-pad,(y0+y1)//2),(x1+pad,(y0+y1)//2),((x0+x1)//2,y0-3*pad)]]
            color=max(samples,key=lambda c:sum(c[:3]) if c[3]>240 else -1)
            lid = Image.new('RGBA',patch.size,color)
            eye = patch.resize((patch.width,max(1,round(patch.height*(1-.96*state['blink'])))),Image.Resampling.BICUBIC)
            lid.alpha_composite(eye,(0,(patch.height-eye.height)//2))
            mask = Image.new('L',patch.size,0)
            ImageDraw.Draw(mask).rounded_rectangle((1,1,patch.width-2,patch.height-2),radius=max(2,pad),fill=255)
            mask = mask.filter(ImageFilter.GaussianBlur(max(.5,pad/2)))
            image.paste(lid,(x0,y0),mask)
    # Local head turn (2D puppet approximation), leaving the body and feet fixed.
    eyes = rig['eyes']
    cx = sum((b[0]+b[2])/2 for b in eyes)/len(eyes)*w
    cy = sum((b[1]+b[3])/2 for b in eyes)/len(eyes)*h
    radius = max(abs(eyes[0][0]-eyes[-1][2])*w,.22*w)
    mesh=[]
    def point(x,y):
        weight=math.exp(-((x-cx)/(radius*1.1))**4-((y-cy)/(.19*h))**4)
        dx = -.025*w*state['look']*state['direction']*weight
        # Subtle cheek lift on the final happy reaction, retaining the original mouth.
        cheek=math.exp(-((x-cx)/(radius*.8))**4-((y-cy-.11*h)/(.055*h))**4)
        return x+dx, y+state['reaction']*.008*h*cheek
    for y in range(0,h,16):
        for x in range(0,w,16):
            r,b=min(w,x+16),min(h,y+16)
            mesh.append(((x,y,r,b),tuple(c for p in [point(x,y),point(x,b),point(r,b),point(r,y)] for c in p)))
    return image.transform(image.size,Image.Transform.MESH,mesh,Image.Resampling.BICUBIC)


def draw_prop(canvas, plan, t, anchor, travel):
    if t < .65:
        return
    w,h = canvas.size
    direction=plan['direction']
    enter=smooth((t-.65)/1.0)
    destination=anchor[0]+direction*max(abs(travel)*1.25,w*.12)
    x=(w+30 if direction>0 else -30)*(1-enter)+destination*enter
    y=anchor[1] + h*.025*math.sin(t*4)
    size=max(5,round(min(w,h)*.025))
    d=ImageDraw.Draw(canvas)
    if plan['prop']=='butterfly':
        flap=.22+.78*abs(math.sin(t*12))
        wing=max(2,round(size*flap))
        for side in (-1,1):
            d.ellipse((x+side*wing-wing,y-size,x+side*wing+wing,y+size*.4),fill=(247,172,76,235))
            d.ellipse((x+side*wing*.8-wing*.7,y,x+side*wing*.8+wing*.7,y+size),fill=(247,121,162,235))
        d.line((x,y-size*.6,x,y+size*.6),fill=(94,64,87,255),width=max(1,size//5))
    elif plan['prop']=='ball':
        y=anchor[1]+h*.22-abs(math.sin(t*4))*size
        d.ellipse((x-size,y-size,x+size,y+size),fill=(255,181,78,255),outline=(232,120,106,255),width=2)
    elif plan['prop']=='star':
        points=[(x+math.cos(i*math.pi/5-math.pi/2)*size*(1 if i%2==0 else .45),
                 y+math.sin(i*math.pi/5-math.pi/2)*size*(1 if i%2==0 else .45)) for i in range(10)]
        d.polygon(points,fill=(255,225,145,220))
    else:
        for i in range(5):
            px=(x+i*w*.09)%w
            py=(t*h*.17+i*h*.14)%(h*.7)
            d.line((px,py,px-2,py+size),fill=(151,207,245,175),width=max(1,size//5))


def compose_frame(bg, subject, bbox, plan, t, rig=None, camera=True, prop=True):
    state=state_at(plan,t)
    w,h=bg.size
    room_right=max(0,w-bbox[2]-4)
    room_left=max(0,bbox[0]-4)
    # Pick the safe side once, before movement starts.
    direction=1 if room_right>=room_left else -1
    plan=dict(plan,direction=direction)
    state['direction']=direction
    travel=direction*min(w*.13,room_right if direction>0 else room_left)
    lift=state['hop']*min(h*.075,max(0,bbox[1]*.4))
    stretch=1+.035*state['hop']-.035*state['landing']
    if plan['action']=='settle':
        stretch-=.025*state['progress']
    elif plan['action']=='sway':
        stretch+=.008*math.sin(t*4)
    actor=face_motion(subject,rig,state)
    actor=actor.resize((max(1,round(subject.width/stretch**.4)),max(1,round(subject.height*stretch))),Image.Resampling.BICUBIC)
    cx=(bbox[0]+bbox[2])/2+travel*state['progress']
    x=max(0,min(w-actor.width,round(cx-actor.width/2)))
    y=max(0,round(bbox[3]-actor.height-lift))
    canvas=bg.copy().convert('RGBA')
    shadow=Image.new('RGBA',bg.size)
    d=ImageDraw.Draw(shadow)
    radius=subject.width*.28*(1-.25*state['hop'])
    d.ellipse((cx-radius,bbox[3]-h*.012,cx+radius,bbox[3]+h*.012),fill=(45,47,60,round(45-15*state['hop'])))
    canvas=Image.alpha_composite(canvas,shadow.filter(ImageFilter.GaussianBlur(max(1,h*.01))))
    canvas.alpha_composite(actor,(x,y))
    face_y=y+subject.height*(sum((b[1]+b[3])/2 for b in rig['eyes'])/len(rig['eyes']) if rig else .4)
    if prop:
        draw_prop(canvas,plan,t,(cx,face_y),travel)
    if not camera:
        return canvas
    # Keep the entire frame during the action, then push toward the reacting face.
    zoom=1+(.25 if rig else .10)*state['reaction']
    crop_w,crop_h=w/zoom,h/zoom
    target_y=face_y if rig else h*.5
    left=max(0,min(w-crop_w,cx-crop_w/2))
    top=max(0,min(h-crop_h,target_y-crop_h/2))
    return canvas.crop((round(left),round(top),round(left+crop_w),round(top+crop_h))).resize((w,h),Image.Resampling.BICUBIC).convert('RGB')


def actor_parts(foreground):
    """Separate disjoint substantial silhouettes so friends react independently."""
    from scipy import ndimage
    alpha=np.asarray(foreground)[:,:,3]
    labels,count=ndimage.label(alpha>64)
    areas=np.bincount(labels.ravel());areas[0]=0
    if not count:
        return []
    parts=[]
    for number in np.flatnonzero(areas>=max(areas.max()*.12,20)):
        mask=ndimage.binary_dilation(labels==number,iterations=2)
        item=foreground.copy()
        item.putalpha(Image.fromarray(np.where(mask,alpha,0).astype('uint8')))
        bbox=item.getbbox()
        if bbox:
            subject=item.crop(bbox)
            parts.append((subject,bbox,detect_face(subject)))
    return parts


def compose_scene(bg, parts, plan, t):
    if len(parts)==1:
        subject,bbox,rig=parts[0]
        return compose_frame(bg,subject,bbox,plan,t,rig)
    # Disjoint children/animals keep their own face and feet. Small staggered
    # reactions make the companions notice the same incoming object in turn.
    canvas=bg.copy()
    left=min(p[1][0] for p in parts); top=min(p[1][1] for p in parts)
    right=max(p[1][2] for p in parts); bottom=max(p[1][3] for p in parts)
    for i,(subject,bbox,rig) in enumerate(parts):
        friend_plan=dict(plan,action='settle' if plan['action']=='settle' else 'sway')
        canvas=compose_frame(canvas,subject,bbox,friend_plan,max(0,t-i*.12),rig,camera=False,prop=False)
    w,h=bg.size
    draw_prop(canvas,plan,t,((left+right)/2,top+(bottom-top)*.35),w*.10)
    reaction=state_at(plan,t)['reaction']
    zoom=1+.10*reaction
    cw,ch=w/zoom,h/zoom
    x=max(0,min(w-cw,(left+right)/2-cw/2));y=max(0,min(h-ch,(top+bottom)/2-ch/2))
    return canvas.crop((round(x),round(y),round(x+cw),round(y+ch))).resize((w,h),Image.Resampling.BICUBIC).convert('RGB')


def motion_prompt(scene):
    # The episode palette may mention night/rain; choose actions from the current
    # lyric and literal scene, before the shared world/style suffix.
    return scene.get('lyric','')+' '+scene.get('prompt','').split('. Clear complete main character',1)[0]
