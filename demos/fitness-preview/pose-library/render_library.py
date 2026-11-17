"""Render different movements and authored views from a reusable pose catalog.

Runtime: NumPy, OpenCV, Pillow and FFmpeg. No neural inference or GPU needed.
"""
import argparse
import importlib.util
import json
import math
from pathlib import Path
import subprocess

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from face_motion import FaceMotion

ROOT=Path(__file__).resolve().parent
W,H=520,620
FPS=24
FRAME_SIZE=(1280,720)
SHOT_SECONDS=4.5
SHOTS=(
    ("front","Bodyweight Squat","FRONT VIEW"),
    ("side","Bodyweight Squat","SIDE VIEW"),
    ("back","Bodyweight Squat","BACK VIEW"),
    ("reach","Overhead Reach","FRONT VIEW"),
    ("dance","Dance Step-Touch","FRONT VIEW"),
)
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


def load_catalog():
    catalog=json.loads((ROOT/"pose_catalog.json").read_text())
    out={}
    for name,entries in catalog.items():
        if len(entries)!=3:
            raise ValueError(f"{name} needs start, middle, and end poses")
        images=[]
        anchors=[]
        points=[np.asarray(entry["points"],np.float32) for entry in entries]
        for i,entry in enumerate(entries):
            image=cv2.imread(str(ROOT/entry["image"]),cv2.IMREAD_UNCHANGED)
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
    i=min(1,int(progress))
    t=progress-i
    first=poses[1]-poses[0]
    second=poses[2]-poses[1]
    middle=np.zeros_like(first)
    signed=first*second>0
    middle[signed]=2*first[signed]*second[signed]/(first[signed]+second[signed])
    slopes=(first,middle,second)
    p=((2*t**3-3*t*t+1)*poses[i]+(-2*t**3+3*t*t)*poses[i+1]
       +(t**3-2*t*t+t)*slopes[i]+(t**3-t*t)*slopes[i+1])
    # Pin the ankle/heel/toe landmarks to the first pose for these
    # stationary sequences. Standing and floor heights stay consistent.
    if lock_feet:
        for landmark in (27,28,29,30,31,32):
            p[POINTS.index(landmark)]=poses[0,POINTS.index(landmark)]
    return i,t,p


def merge(a,b,t):
    # The two poses may still reveal different parts of a swinging limb.
    # Use one opaque silhouette so a second hand or a doubled sleeve cannot
    # appear in mid-air; blend color only where both warps cover the pixel.
    primary,other=(a,b) if t<.5 else (b,a)
    ma=primary[...,3:4].astype(np.float32)/255
    mb=other[...,3:4].astype(np.float32)/255
    mix=min(t,1-t)*.56*mb
    rgb=primary[...,:3]*(1-mix)+other[...,:3]*mix
    alpha=np.clip((ma-.18)/.68,0,1)
    return np.concatenate((rgb*alpha,255*alpha),axis=2).clip(0,255).astype(np.uint8)


class SideSquat:
    def __init__(self):
        file=ROOT.parent/"cpu-motion/morph.py"
        spec=importlib.util.spec_from_file_location("side_squat_warp",file)
        self.warp=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.warp)
        self.images,self.anchors=self.warp.load_poses()
        self.head=self.warp.feather_rows(self.images[0],98,121)

    def frame(self,seconds):
        progress=motion_time(seconds)
        section,t,points=self.warp.curve_poses(self.anchors,progress)
        a,b=self.warp.warp_pair(self.images[section],self.images[section+1],
                                self.anchors[section],self.anchors[section+1],points)
        image=cv2.addWeighted(a,1-t,b,t,0)
        image=self.warp.preserve_head(image,self.head,self.anchors[0],points)
        resized=cv2.resize(image,(415,578),interpolation=cv2.INTER_AREA)
        output=np.zeros((H,W,4),np.uint8)
        output[46:620,94:509]=resized[:574]
        return output


def ease(x):
    x=max(0.,min(1.,x))
    return x**3*(10+x*(-15+6*x))


def motion_time(seconds):
    return 2*ease((seconds-.23)/1.52)*(1-ease((seconds-2.04)/1.85))


def actor_at(entry,seconds,name,face=None,now=0.,side=None):
    if name=="side" and side:
        return side.frame(seconds)
    images,poses=entry
    if name=="dance":
        # Return through a neutral stance before stepping to the other side.
        # This keeps the wrists from crossing through the opposite arm.
        section=min(1,int(seconds/(SHOT_SECONDS*.5)))
        local=seconds-section*SHOT_SECONDS*.5
        progress=ease((local-.07)/.83)*(1-ease((local-1.13)/1.02))
        i,k,t=0,section+1,progress
        target=poses[i]*(1-t)+poses[k]*t
    else:
        i,t,target=trajectory(poses,motion_time(seconds),lock_feet=True)
        k=i+1
    a,b=warp_pair(images[i],images[k],poses[i],poses[k],target)
    actor=merge(a,b,t)
    return face.apply(actor,name,i,k,t,now,seconds) if face else actor


def background():
    base=ImageOps.fit(Image.open(ROOT.parent/"jungle.png").convert("RGB"),FRAME_SIZE).convert("RGBA")
    shadow=Image.new("RGBA",FRAME_SIZE)
    draw=ImageDraw.Draw(shadow)
    draw.ellipse((331,610,570,640),fill=(14,26,16,125))
    base.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(8)))
    return np.asarray(base.convert("RGB"))


def show(base,actor,title,view,shot):
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
    cue="STEP TO THE BEAT" if shot==4 else "MOVE WITH CONTROL"
    draw.text((24,130),cue,font=FONTS[17],fill="#eaff9b")
    image.alpha_composite(card,(819,196))
    return image.convert("RGB")


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    cv2.setNumThreads(2)
    catalog=load_catalog()
    base=background()
    face=FaceMotion(ROOT)
    side=SideSquat()
    if args.check:
        for i,(name,title,view) in enumerate(SHOTS):
            for second in (0.,1.20,1.85,2.88):
                show(base,actor_at(catalog[name],second,name,face,i*SHOT_SECONDS+second,side),title,view,i).save(
                    f"/tmp/coral-library-{name}-{second:.2f}.jpg",quality=93)
        return
    file=ROOT/"coral-multi-angle-workout.mp4"
    cmd=["ffmpeg","-v","error","-y","-f","rawvideo","-pix_fmt","rgb24","-s","1280x720","-r",str(FPS),
         "-i","-","-i",str(ROOT/"demo_audio.m4a"),"-map","0:v","-map","1:a","-c:v","libx264","-threads","2","-preset","fast","-crf","18","-pix_fmt","yuv420p",
         "-c:a","aac","-b:a","160k","-movflags","+faststart",str(file)]
    with subprocess.Popen(cmd,stdin=subprocess.PIPE) as encoder:
        for i,(name,title,view) in enumerate(SHOTS):
            for frame in range(round(FPS*SHOT_SECONDS)):
                image=show(base,actor_at(catalog[name],frame/FPS,name,face,i*SHOT_SECONDS+frame/FPS,side),title,view,i)
                encoder.stdin.write(image.tobytes())
        encoder.stdin.close()
        if encoder.wait():
            raise RuntimeError("Could not encode motion preview")


if __name__=="__main__":
    main()
