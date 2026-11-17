"""Render different movements and authored views from a reusable pose catalog.

Runtime: NumPy, OpenCV, Pillow and FFmpeg. No neural inference or GPU needed.
"""
import argparse
import json
import math
from pathlib import Path
import subprocess

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from face_motion import FaceMotion
from workout_plan import DEFAULT_PLAN, validate_plan

ROOT=Path(__file__).resolve().parent
W,H=520,620
FPS=48
FRAME_SIZE=(1280,720)
SHOT_SECONDS=4.5
PARTS=(
    (11,12,28),(11,13,22),(12,14,22),(13,15,19),(14,16,19),
    (23,24,32),(11,23,65),(12,24,65),
    (23,25,33),(24,26,33),(25,27,28),(26,28,28),
)
POINTS=(0,2,5,7,8,9,10,11,12,13,14,15,16,19,20,23,24,25,26,27,28,29,30,31,32)
FONT_PATH=next((p for p in (
    Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
) if p.is_file()),None)
FONTS={s:ImageFont.truetype(str(FONT_PATH),s) if FONT_PATH else ImageFont.load_default(size=s)
       for s in (17,20,30,62)}
SIZE=(W,H)
GRID=np.stack(np.meshgrid(np.linspace(0,W-1,68,dtype=np.float32),
                          np.linspace(0,H-1,81,dtype=np.float32)),axis=-1)
PIXEL_GRID=np.stack(np.meshgrid(np.arange(W,dtype=np.float32),np.arange(H,dtype=np.float32)),axis=-1)


def ray_edge(alpha,p,axis,limit):
    start=np.round(p).astype(int)
    if not (0<=start[0]<W and 0<=start[1]<H) or alpha[start[1],start[0]]<.43:
        return p+axis*(limit*.48)
    end=p
    for length in range(2,limit+1,2):
        candidate=p+length*axis
        x,y=np.round(candidate).astype(int)
        if not (0<=x<W and 0<=y<H) or alpha[y,x]<.49:
            break
        end=candidate
    return end


def guides(image,points):
    alpha=image[...,3]/255.
    points=points[:,:2]
    result=[points[k] for k in POINTS]
    for a,b,max_radius in PARTS:
        start,end=points[a],points[b]
        vec=end-start
        length=max(1.,np.linalg.norm(vec))
        perp=np.array((-vec[1],vec[0]))/length
        for fraction in (.22,.66):
            center=start+fraction*vec
            result.extend((center,ray_edge(alpha,center,perp,max_radius),
                           ray_edge(alpha,center,-perp,max_radius)))
    # Image boundaries stabilize pixels outside the performer.
    result.extend(((1,1),(W-2,1),(W-2,H-2),(1,H-2)))
    return np.asarray(result,np.float32)


def load_catalog(extra=None):
    catalog=json.loads((ROOT/"pose_catalog.json").read_text())
    locations={name:ROOT for name in catalog}
    if extra:
        new=json.loads(extra.read_text())
        catalog.update(new)
        locations.update({name:extra.parent for name in new})
    out={}
    for name,entries in catalog.items():
        if len(entries)<3:
            raise ValueError(f"{name} needs at least three authored poses")
        images=[]
        anchors=[]
        points=[np.asarray(entry["points"],np.float32) for entry in entries]
        for i,entry in enumerate(entries):
            image=cv2.imread(str(locations[name]/entry["image"]),cv2.IMREAD_UNCHANGED)
            if image is None or image.shape!=(H,W,4):
                raise ValueError(f"Invalid pose image {entry['image']}")
            images.append(image)
            anchors.append(guides(image,points[i]))
        out[name]=(images,np.stack(anchors))
    return out


def kernel(query,controls):
    square=((query[...,None,:]-controls)**2).sum(axis=-1)
    return square*np.log(np.maximum(square,1e-9))


def warp_pair(first,second,source_a,source_b,target):
    loc=target/max(W,H)
    affine=np.column_stack((np.ones(len(loc),np.float32),loc))
    rbf=kernel(loc,loc)
    rbf.flat[::len(loc)+1]+=.00042
    matrix=np.block([[rbf,affine],[affine.T,np.zeros((3,3),np.float32)]])
    values=np.column_stack((source_a,source_b))/max(W,H)
    w=np.linalg.solve(matrix,np.vstack((values,np.zeros((3,4),np.float32))))
    grid=GRID/max(W,H)
    mapping=(kernel(grid,loc)@w[:-3]+w[-3]+grid@w[-2:])*max(W,H)
    out=[]
    for image,choice in ((first,0),(second,2)):
        displacement=mapping[...,choice:choice+2]-GRID
        remap=PIXEL_GRID+cv2.resize(displacement,SIZE,interpolation=cv2.INTER_CUBIC)
        out.append(cv2.remap(image,remap,None,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT))
    return out


def trajectory(poses,progress,lock_feet=True):
    changes=np.diff(poses,axis=0)
    i=min(len(poses)-2,int(progress))
    t=progress-i
    slopes=np.zeros_like(poses)
    slopes[0],slopes[-1]=changes[0],changes[-1]
    for j,(previous,next_change) in enumerate(zip(changes[:-1],changes[1:]),1):
        same_direction=previous*next_change>0
        slopes[j,same_direction]=2*previous[same_direction]*next_change[same_direction]/(
            previous[same_direction]+next_change[same_direction])
    p=((2*t**3-3*t*t+1)*poses[i]+(-2*t**3+3*t*t)*poses[i+1]
       +(t**3-2*t*t+t)*slopes[i]+(t**3-t*t)*slopes[i+1])
    if lock_feet:
        for landmark in (27,28,29,30,31,32):
            p[POINTS.index(landmark)]=poses[0,POINTS.index(landmark)]
    return i,t,p


def merge(a,b,t,kind):
    # The two poses may still reveal different parts of a swinging limb.
    # Use one opaque silhouette so a second hand or a doubled sleeve cannot
    # appear in mid-air; blend color only where both warps cover the pixel.
    primary,other=(a,b) if t<.5 else (b,a)
    ma=primary[...,3:4].astype(np.float32)/255
    mb=other[...,3:4].astype(np.float32)/255
    mix=min(t,1-t)*.56*mb
    rgb=primary[...,:3]*(1-mix)+other[...,:3]*mix
    intersection=np.count_nonzero((ma>.55)&(mb>.55))
    union=np.count_nonzero((ma>.55)|(mb>.55))
    if kind=="lunge":
        transition=ease((t-.22)/.56)
        matte=(a[...,3:4]*(1-transition)+b[...,3:4]*transition)/255.
        left=(a[...,3:4]/255.)*(1-transition)
        right=(b[...,3:4]/255.)*transition
        rgb=(a[...,:3]*left+b[...,:3]*right)/np.maximum(left+right,1e-5)
    elif union and intersection/union>.895:
        matte=(a[...,3:4]*(1-t)+b[...,3:4]*t)/255.
    else:
        matte=ma
    alpha=np.clip((matte-.18)/.68,0,1)
    return np.concatenate((rgb*alpha,255*alpha),axis=2).clip(0,255).astype(np.uint8)


def ease(x):
    x=max(0.,min(1.,x))
    return x**3*(10+x*(-15+6*x))


def motion_time(seconds):
    return ease((seconds-.23)/1.52)*(1-ease((seconds-2.04)/1.85))


def actor_at(entry,seconds,name,face=None,now=0.):
    images,poses=entry
    if name=="dance":
        section=min(1,int(seconds/(SHOT_SECONDS*.5)))
        local=seconds-section*SHOT_SECONDS*.5
        progress=ease((local-.07)/.83)*(1-ease((local-1.13)/1.02))
        half=(len(poses)-1)//2
        indices=[0,*range(1+section*half,1+(section+1)*half)]
        i,t,target=trajectory(poses[indices],half*progress,lock_feet=False)
        i,k=indices[i],indices[i+1]
    else:
        rooted=name in {"front","side","back","reach","lunge","stretch"}
        i,t,target=trajectory(poses,(len(poses)-1)*motion_time(seconds),lock_feet=rooted)
        k=i+1
    a,b=warp_pair(images[i],images[k],poses[i],poses[k],target)
    actor=merge(a,b,t,name)
    return face.apply(actor,name,i,k,t,now,seconds) if face else actor


def background():
    base=ImageOps.fit(Image.open(ROOT.parent/"jungle.png").convert("RGB"),FRAME_SIZE).convert("RGBA")
    shadow=Image.new("RGBA",FRAME_SIZE)
    draw=ImageDraw.Draw(shadow)
    draw.ellipse((331,610,570,640),fill=(14,26,16,125))
    base.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(8)))
    return np.asarray(base.convert("RGB"))


def show(base,actor,title,view):
    rgba=cv2.cvtColor(actor,cv2.COLOR_BGRA2RGBA)
    frame=base.copy()
    x,y=190,19
    region=frame[y:y+H,x:x+W]
    a=rgba[...,3:4].astype(np.float32)/255.
    region[:]=np.clip(np.rint(region*(1-a)+rgba[...,:3]),0,255).astype(np.uint8)
    image=Image.fromarray(frame).convert("RGBA")
    card=Image.new("RGBA",(382,197))
    draw=ImageDraw.Draw(card)
    draw.rounded_rectangle((0,0,381,196),radius=23,fill=(10,33,25,231))
    draw.text((24,21),view,font=FONTS[20],fill="#eaff9b")
    draw.text((24,64),title,font=FONTS[30],fill="#fff9ee")
    cue="STEP TO THE BEAT" if title=="Dance Step-Touch" else "MOVE WITH CONTROL"
    draw.text((24,130),cue,font=FONTS[17],fill="#eaff9b")
    image.alpha_composite(card,(819,196))
    return image.convert("RGB")


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--check",action="store_true")
    parser.add_argument("--plan",type=Path)
    parser.add_argument("--pose-catalog",type=Path)
    parser.add_argument("--audio",type=Path)
    parser.add_argument("--phone-timing",type=Path)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    plan=json.loads(args.plan.read_text()) if args.plan else DEFAULT_PLAN
    if bool(args.audio)!=bool(args.phone_timing):
        parser.error("--audio and --phone-timing must be supplied together")
    cv2.setNumThreads(2)
    catalog=load_catalog(args.pose_catalog)
    shots=validate_plan(plan,catalog)
    base=background()
    face=FaceMotion(ROOT)
    audio=args.audio if args.plan else args.audio or ROOT/"demo_audio.m4a"
    if args.phone_timing:
        face.phones=json.loads(args.phone_timing.read_text())
    elif args.plan:
        face.phones=[]
    if args.check:
        for i,(name,title,view) in enumerate(shots):
            for second in (0.,1.20,1.85,2.88):
                show(base,actor_at(catalog[name],second,name,face,i*SHOT_SECONDS+second),title,view).save(
                    f"/tmp/coral-library-{name}-{second:.2f}.jpg",quality=93)
        return
    file=args.output or ROOT/("coral-custom-workout.mp4" if args.plan else "coral-multi-angle-smooth-48fps.mp4")
    cmd=["ffmpeg","-v","error","-y","-f","rawvideo","-pix_fmt","rgb24","-s","1280x720","-r",str(FPS),
         "-i","-"]
    if audio:
        cmd+=["-i",str(audio),"-map","0:v","-map","1:a","-af","apad","-c:a","aac","-b:a","160k"]
    cmd+=["-c:v","libx264","-threads","2","-preset","fast","-crf","18","-pix_fmt","yuv420p",
          "-t",str(len(shots)*SHOT_SECONDS),"-metadata","title="+plan["title"],
          "-movflags","+faststart",str(file)]
    with subprocess.Popen(cmd,stdin=subprocess.PIPE) as encoder:
        for i,(name,title,view) in enumerate(shots):
            for frame in range(round(FPS*SHOT_SECONDS)):
                image=show(base,actor_at(catalog[name],frame/FPS,name,face,i*SHOT_SECONDS+frame/FPS),title,view)
                encoder.stdin.write(image.tobytes())
        encoder.stdin.close()
        if encoder.wait():
            raise RuntimeError("Could not encode motion preview")


if __name__=="__main__":
    main()
