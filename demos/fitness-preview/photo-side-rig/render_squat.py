"""CPU animation from the original coral trainer's side-view pixels.

The arm is a separate layer. A continuous image mesh blends thigh, calf, torso,
and head transforms, keeping skin and the leggings seam intact at each joint.
"""
from pathlib import Path
import math
import subprocess

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT=Path(__file__).resolve().parent
W,H,FPS,SECONDS=1280,720,24,12
SIZE=(560,960)
X_ORIGIN=530
CROP_LEFT,CROP_RIGHT=663,889
# Fallback is in OpenCV BGR order.
COLORED_CLOTH=(152,160,23) # BGR, used behind the arm where the source hides the cloth
SHOULDER=np.float32((778,200))
ELBOW=np.float32((768,331))
WRIST=np.float32((794,449))
HIP=np.float32((775,443))
KNEE=np.float32((779,642))
ANKLE=np.float32((761,864))
NECK=np.float32((791,157))
FONT_PATH=next(path for path in (
    Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
) if path.is_file())
FONTS={size:ImageFont.truetype(str(FONT_PATH),size) for size in (20,24,61)}

# Keep the edges of the original face, ponytail, sneakers and fingers.
SILHOUETTE=np.int32([
    (786,9),(820,11),(850,28),(856,51),(854,75),(862,89),(866,96),(853,103),
    (856,115),(851,129),(831,134),(817,138),(809,161),(810,175),(831,196),
    (861,223),(874,246),(875,259),(864,277),(860,301),(859,334),(855,367),
    (854,398),(848,429),(840,453),(846,478),(847,519),(843,552),(836,582),
    (828,608),(815,642),(805,670),(792,699),(790,741),(785,778),(780,815),
    (780,856),(795,868),(813,890),(848,908),(875,922),(877,936),(864,945),
    (754,947),(728,941),(718,930),(721,906),(732,885),(740,864),(739,830),
    (730,789),(720,750),(721,723),(735,689),(742,663),(742,632),(733,601),
    (730,566),(733,530),(736,507),(723,487),(713,463),(713,446),(719,424),
    (729,406),(743,389),(754,365),(756,341),(752,320),(744,285),(735,260),
    (731,235),(732,207),(736,185),(744,169),(757,145),(758,128),(751,113),
    (743,129),(746,149),(742,172),(734,201),(722,227),(707,248),(696,246),
    (690,224),(694,200),(691,180),(684,156),(676,138),(678,113),(687,91),
    (683,65),(687,48),(701,30),(714,22),(731,20),(742,33),(755,23),(772,14),
])
ARM=np.int32([
    (758,173),(777,166),(796,177),(806,200),(805,222),(798,242),(796,268),
    (790,287),(785,315),(787,343),(794,367),(800,404),(808,432),(813,449),
    (824,466),(831,485),(834,508),(828,516),(823,503),(817,491),(815,523),
    (810,536),(803,536),(798,532),(794,528),(787,523),(785,511),(779,499),
    (778,475),(777,454),(772,426),(766,394),(754,363),(747,333),(746,302),
    (743,272),(742,241),(735,220),(738,200),(744,185),
])

def matte(photo,outline,outer_margin=12):
    canvas=np.zeros(photo.shape[:2],np.uint8)
    cv2.fillPoly(canvas,[outline-np.int32((CROP_LEFT,0))],1)
    brush=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(outer_margin,outer_margin))
    labels=np.where(canvas,cv2.GC_PR_FGD,cv2.GC_PR_BGD).astype(np.uint8)
    labels[cv2.erode(canvas,brush)>0]=cv2.GC_FGD
    labels[cv2.dilate(canvas,brush)==0]=cv2.GC_BGD
    cv2.grabCut(photo,labels,None,np.zeros((1,65)),np.zeros((1,65)),3,cv2.GC_INIT_WITH_MASK)
    return cv2.GaussianBlur(((labels%2)*255).astype(np.uint8),(5,5),.85)


def layers():
    sheet=cv2.imread(str(ROOT.parent/"trainer-concept-v2.png"))
    if sheet is None:
        raise FileNotFoundError("Original coral trainer concept image")
    photo=sheet[:960,CROP_LEFT:CROP_RIGHT].copy()
    alpha=matte(photo,SILHOUETTE,15)
    shape=np.zeros(photo.shape[:2],np.uint8)
    cv2.fillPoly(shape,[ARM-np.int32((CROP_LEFT,0))],255)
    skin=cv2.cvtColor(photo,cv2.COLOR_BGR2HSV)
    skin_mask=(((skin[:,:,0]<=31)|(skin[:,:,0]>=174)) & (skin[:,:,1]>=29)).astype(np.uint8)*255
    skin_mask[:241]=255
    skin_mask=cv2.GaussianBlur(cv2.dilate(skin_mask,np.ones((3,3),np.uint8)),(5,5),.85)
    arm_alpha=np.minimum(np.minimum(alpha,skin_mask),cv2.GaussianBlur(shape,(5,5),1.05))
    repair=cv2.dilate(shape,np.ones((13,13),np.uint8))
    filled=photo.copy()
    # Where the arm covers the torso, sample uncovered cloth on that same row.
    # Past the waist it covers only one side of the teal leggings.
    for y in range(167,543):
        idx=np.flatnonzero(repair[y]>0)
        if not len(idx):
            continue
        high=min(photo.shape[1]-2,int(idx[-1])+7)
        low=max(0,int(idx[0])-7)
        if y<396:
            near=np.median(photo[y,high:min(high+10,len(photo[y]))],axis=0)
            if not (near[2]>near[1]*1.24):
                near=(74,78,214)
        else:
            near=np.median(photo[y,low:min(low+8,len(photo[y]))],axis=0)
            if not (near[1]>near[2]*1.18):
                near=COLORED_CLOTH
        for x in idx:
            shade=.89+.16*((x-idx[0])/max(1,idx[-1]-idx[0]))
            filled[y,x]=np.clip(np.asarray(near)*shade,0,255)
    shoe_alpha=alpha.copy()
    shoe_alpha[:863]=0
    shoe_alpha[863:878]=(shoe_alpha[863:878]*(np.arange(15)/14)[:,None]).astype(np.uint8)
    body_alpha=alpha.copy()
    # The copied shoulder/hand should not determine the under-layer silhouette
    # outside the real torso; reconstruct the occluded shirt/leg contour.
    x=np.arange(CROP_LEFT,CROP_RIGHT)
    for y in range(167,543):
        start=float(np.interp(y,[167,209,260,300,340,360,392,425,465,510,542],
                                [744,732,737,752,755,756,742,720,717,734,734]))
        end=float(np.interp(y,[167,200,245,270,317,400,445,480,542],
                              [811,835,875,869,859,851,842,846,845]))
        active=repair[y]>0
        new_mask=np.clip(np.minimum(x-start,end-x)*128,0,255).astype(np.uint8)
        body_alpha[y]=np.maximum(body_alpha[y],new_mask)
        body_alpha[y,active]=new_mask[active]
        repair_missing=(alpha[y]<160)&(new_mask>0)&~active
        if np.any(repair_missing):
            valid=(alpha[y]>225)&(new_mask>210)&~active
            fallback=np.median(photo[y,valid],axis=0) if np.any(valid) else (COLORED_CLOTH if y>=396 else (75,80,210))
            filled[y,repair_missing]=fallback
    body_alpha[880:]=0
    body_alpha[863:880]=(body_alpha[863:880]*(1-np.arange(17)/16)[:,None]).astype(np.uint8)

    def pack(rgb,mask):
        output=np.zeros((SIZE[1],SIZE[0],4),np.uint8)
        start=CROP_LEFT-X_ORIGIN
        premul=(rgb.astype(np.float32)*(mask[...,None]/255.)).round().astype(np.uint8)
        output[:,start:start+photo.shape[1]]=np.dstack((premul,mask))
        return output

    return pack(filled,body_alpha),pack(photo,arm_alpha),pack(photo,shoe_alpha)


def direction(angle):
    return np.float32(((math.cos(angle),-math.sin(angle)),(math.sin(angle),math.cos(angle))))


def angle_of(bone):
    return math.atan2(float(bone[1]),float(bone[0]))


def map_bone(points,start,end,placed_start,placed_end):
    rotation=direction(angle_of(placed_end-placed_start)-angle_of(end-start))
    return (points-start)@rotation.T+placed_start


def ik_knee(hip):
    length1=np.linalg.norm(KNEE-HIP)
    length2=np.linalg.norm(ANKLE-KNEE)
    offset=ANKLE-hip
    distance=np.linalg.norm(offset)
    axis=offset/distance
    along=(length1**2-length2**2+distance**2)/(2*distance)
    radius=math.sqrt(max(0.,length1**2-along**2))
    outside=np.array((axis[1],-axis[0]),np.float32)
    return hip+axis*along+outside*radius


def smooth(x):
    x=np.clip(x,0.,1.)
    return x*x*(3-2*x)


def depth_at(t):
    if t<1.4 or t>=10.4:
        return 0.
    phase=(t-1.4)%4.5
    return float(smooth(phase/1.75)*smooth((4.18-phase)/1.83))


def controls(t):
    d=depth_at(t)
    hip=HIP+np.float32((-100*d,148*d))
    knee=ik_knee(hip)
    torso=direction(.39*d)
    neck=(NECK-HIP)@torso.T+hip

    body,posed=[],[]
    rows=[
        (10,760,817),(40,705,853),(78,686,854),(107,697,855),(132,681,848),
        (158,687,811),(187,711,825),(225,734,869),(266,740,870),(310,752,858),
        (350,755,855),(389,742,852),(425,719,847),(465,716,842),(500,730,846),
        (542,733,844),(579,734,835),(614,739,824),(640,742,815),(668,740,804),
        (705,727,793),(739,721,789),(780,727,784),(821,735,780),(858,739,780),
        (874,733,802),(899,726,828),(945,744,860),
    ]
    for y,left,right in rows:
        source=np.float32([(left,y),((left+right)*.5,y),(right,y)])
        trunk=(source-HIP)@torso.T+hip
        skull=(source-NECK)@direction(.035*d).T+neck
        head=smooth((177-y)/47)
        trunk=trunk*(1-head)+skull*head
        upper=map_bone(source,HIP,KNEE,hip,knee)
        lower=map_bone(source,KNEE,ANKLE,knee,ANKLE)
        waist=smooth((y-410)/80)
        kneew=smooth((y-610)/72)
        leg=upper*(1-kneew)+lower*kneew
        foot=smooth((y-842)/33)
        target=(trunk*(1-waist)+leg*waist)*(1-foot)+source*foot
        body.extend(source)
        posed.extend(target)
    shoulder=(SHOULDER-HIP)@torso.T+hip
    upper_angle=angle_of(ELBOW-SHOULDER)-1.34*d
    elbow=shoulder+np.linalg.norm(ELBOW-SHOULDER)*np.float32((math.cos(upper_angle),math.sin(upper_angle)))
    fore_angle=angle_of(WRIST-ELBOW)-1.46*d
    wrist=elbow+np.linalg.norm(WRIST-ELBOW)*np.float32((math.cos(fore_angle),math.sin(fore_angle)))
    arm,arm_pose=[],[]
    for y,left,right in ((172,749,795),(195,740,804),(220,736,802),(243,742,799),(270,744,792),
                         (303,747,787),(330,746,788),(371,757,796),(410,765,803),
                         (448,775,813),(480,780,832),(513,785,829),(535,787,818)):
        source=np.float32([(left,y),((left+right)*.5,y),(right,y)])
        upper=map_bone(source,SHOULDER,ELBOW,shoulder,elbow)
        lower=map_bone(source,ELBOW,WRIST,elbow,wrist)
        mix=smooth((y-307)/48)
        target=upper*(1-mix)+lower*mix
        arm.extend(source)
        arm_pose.extend(target)
    for seq in (body,posed,arm,arm_pose):
        seq.extend([(531,1),(1088,1),(1088,958),(531,958)])
    offset=np.float32((X_ORIGIN,0))
    return tuple(np.asarray(seq,dtype=np.float32)-offset for seq in (body,posed,arm,arm_pose))


GRID_SIZE=(71,121)
GRID=np.stack(np.meshgrid(np.linspace(0,SIZE[0]-1,GRID_SIZE[0],dtype=np.float32),
                          np.linspace(0,SIZE[1]-1,GRID_SIZE[1],dtype=np.float32)),axis=-1)
PIXELS=np.stack(np.meshgrid(np.arange(SIZE[0],dtype=np.float32),np.arange(SIZE[1],dtype=np.float32)),axis=-1)
NORMAL=960.


def radial(query,anchors):
    square=np.sum((query[...,None,:]-anchors)**2,axis=-1)
    return square*np.log(np.maximum(1e-8,square))


def deform(layer,source,destination):
    anchors=destination/NORMAL
    affine=np.column_stack((np.ones(len(anchors),np.float32),anchors))
    kernel=radial(anchors,anchors)
    kernel.flat[::len(anchors)+1]+=.00022
    system=np.block([[kernel,affine],[affine.T,np.zeros((3,3),np.float32)]])
    weights=np.linalg.solve(system,np.vstack((source/NORMAL,np.zeros((3,2),np.float32))))
    grid=GRID/NORMAL
    mapping=(radial(grid,anchors)@weights[:-3]+weights[-3]+grid@weights[-2:])*NORMAL
    coords=PIXELS+cv2.resize(mapping-GRID,SIZE,interpolation=cv2.INTER_CUBIC)
    return cv2.remap(layer,coords,None,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)


def overlay(destination,visible):
    a=visible[...,3:4].astype(np.float32)/255
    return np.clip(np.rint(visible[...,:destination.shape[2]]+destination*(1-a)),0,255).astype(np.uint8)


def close_garment_gaps(layer, t):
    # In a deep bend, the inverse image warp can fold behind the hip.
    # Only restore holes enclosed by the opaque torso/leggings silhouette;
    # leave the arm, neck, ponytail and sneaker alpha untouched.
    depth=depth_at(t)
    if depth<.04:
        return layer
    alpha=layer[...,3]
    binary=(alpha>119).astype(np.uint8)*255
    closed=cv2.morphologyEx(binary,cv2.MORPH_CLOSE,
                            cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(61,61)))
    contours,_=cv2.findContours(closed,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    filled=np.zeros_like(alpha)
    cv2.drawContours(filled,contours,-1,255,cv2.FILLED)
    x=int(HIP[0]-X_ORIGIN-100*depth)
    y=int(HIP[1]+148*depth)
    zone=np.zeros_like(alpha)
    zone[y-51:y+75,max(0,x-91):x+112]=255
    missing=np.minimum(np.minimum(filled,zone),(alpha<185).astype(np.uint8)*255)
    if not np.any(missing):
        return layer
    colors=layer[...,:3].copy()
    # Inpaint the worn cloth with the nearest source pixels along the seam.
    colors=cv2.inpaint(colors,missing,4,cv2.INPAINT_TELEA)
    layer[...,:3]=colors
    layer[...,3]=np.maximum(alpha,missing)
    return layer


def pose_frame(data,t):
    body,arm,shoes=data
    a,b,c,d=controls(t)
    composite=overlay(shoes,close_garment_gaps(deform(body,a,b),t))
    return overlay(composite,deform(arm,c,d))


def visual_base():
    image=ImageOps.fit(Image.open(ROOT.parent/"jungle.png").convert("RGB"),(W,H)).convert("RGBA")
    shadow=Image.new("RGBA",(W,H))
    draw=ImageDraw.Draw(shadow)
    draw.ellipse((391,608,484,629),fill=(16,25,12,126))
    image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(7)))
    return np.asarray(image.convert("RGB"))


def frame(data,base,t):
    person=pose_frame(data,t)
    sprite=cv2.resize(person,(324,555),interpolation=cv2.INTER_AREA)
    sprite=cv2.cvtColor(sprite,cv2.COLOR_BGRA2RGBA)
    x,y=292,72
    scene=base.copy()
    scene[y:y+555,x:x+324]=overlay(scene[y:y+555,x:x+324],sprite)[:,:,:3]
    im=Image.fromarray(scene).convert("RGBA")
    card=Image.new("RGBA",(342,204))
    draw=ImageDraw.Draw(card)
    draw.rounded_rectangle((0,0,341,203),radius=22,fill=(9,31,25,220))
    draw.text((24,22),"BODYWEIGHT SQUAT",fill="#eaff9b",font=FONTS[24])
    draw.text((23,65),f"0:{max(1,math.ceil(SECONDS-t)):02}",fill="#fff9ee",font=FONTS[61])
    rep="GET READY" if t<1.4 else "FINISHED" if t>=10.4 else f"REP {min(2,1+int((t-1.4)//4.5))} / 2"
    draw.text((25,149),rep,fill="#eaff9b",font=FONTS[20])
    im.alpha_composite(card,(845,186))
    return im.convert("RGB")


def main():
    import sys
    cv2.setNumThreads(2)
    data=layers()
    base=visual_base()
    if "--check" in sys.argv:
        for seconds in (0.,2.3,3.19,4.26):
            frame(data,base,seconds).save(f"/tmp/coral-photo-rig-{seconds:.2f}.jpg",quality=93)
        return
    path=ROOT/"coral-photo-side-squat.mp4"
    cmd=["ffmpeg","-v","error","-y","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}",
         "-r",str(FPS),"-i","-","-c:v","libx264","-threads","2","-preset","fast",
         "-crf","18","-pix_fmt","yuv420p","-movflags","+faststart",str(path)]
    with subprocess.Popen(cmd,stdin=subprocess.PIPE) as encoder:
        for i in range(SECONDS*FPS):
            encoder.stdin.write(frame(data,base,i/FPS).tobytes())
        encoder.stdin.close()
        if encoder.wait():
            raise RuntimeError("Video encoder failed")


if __name__=="__main__":
    main()
