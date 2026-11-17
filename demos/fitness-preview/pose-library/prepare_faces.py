"""Extract the actor's facial expression assets and alignment anchors."""
from pathlib import Path
import json
import sys

import cv2
import mediapipe as mp
import numpy as np

ROOT=Path(__file__).resolve().parent
ANCHORS=np.int32((33,263,1))
DEST=np.float32(((83,97),(171,97),(128,137)))
OPTIONS=("rest","open","round","smile")

def detect(detector,bgr):
    rgb=cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)
    result=detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB,data=rgb))
    if not result.face_landmarks:
        return None
    h,w=bgr.shape[:2]
    points=np.float32([(l.x*w,l.y*h) for l in result.face_landmarks[0]])
    return points


def patch(image,points,part):
    warp=cv2.getAffineTransform(points[ANCHORS],DEST)
    rect=cv2.warpAffine(image,warp,(256,256),flags=cv2.INTER_CUBIC)
    xy=points@warp[:,:2].T+warp[:,2]
    matte=np.zeros((256,256),np.uint8)
    if part=="mouth":
        cx,cy=map(int,(xy[13]+xy[14])*.5)
        radius=max(22,int(abs(xy[61,0]-xy[291,0])*.54)+7)
        height=max(13,round(abs(xy[13,1]-xy[14,1])*.68)+13)
        cv2.ellipse(matte,(cx,cy),(radius,height),0,0,360,255,-1)
        cv2.GaussianBlur(matte,(29,29),6.2,dst=matte)
    else:
        for a,b in ((33,133),(362,263)):
            center=np.rint((xy[a]+xy[b])*.5).astype(int)
            radius=max(13,round(abs(xy[a,0]-xy[b,0])*.52)+4)
            cv2.ellipse(matte,tuple(center),(radius,12),0,0,360,255,-1)
        cv2.GaussianBlur(matte,(19,19),4,dst=matte)
    return np.dstack((rect,matte))


def main():
    cv2.setNumThreads(2)
    opts=mp.tasks.vision.FaceLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=sys.argv[1]),
        min_face_detection_confidence=.24,min_face_presence_confidence=.26,
    )
    sheet=cv2.imread(str(ROOT/"sheets/face.png"))
    if sheet is None:
        raise FileNotFoundError("sheets/face.png")
    catalog=json.loads((ROOT/"pose_catalog.json").read_text())
    faces=ROOT/"faces"
    faces.mkdir(exist_ok=True)
    anchors={}
    with mp.tasks.vision.FaceLandmarker.create_from_options(opts) as detector:
        for i,name in enumerate(OPTIONS):
            w=sheet.shape[1]
            bounds=round(i*w/4),round((i+1)*w/4)
            pane=sheet[:,bounds[0]:bounds[1]]
            landmarks=detect(detector,pane)
            if landmarks is None:
                raise ValueError(f"Face not detected in {name}")
            cv2.imwrite(str(faces/(name+".png")),patch(pane,landmarks,"mouth"))
            if name=="smile":
                cv2.imwrite(str(faces/"blink.png"),patch(pane,landmarks,"eyes"))
        for name in ("front","reach","dance","jack","stretch"):
            if name not in catalog:
                continue
            anchors[name]=[]
            for entry in catalog[name]:
                image=cv2.imread(str(ROOT/entry["image"]))
                x,y=(round(p) for p in entry["points"][0][:2])
                left,top=max(0,x-74),max(0,y-92)
                right,bottom=min(image.shape[1],x+74),min(image.shape[0],y+68)
                crop=image[top:bottom,left:right]
                up=cv2.resize(crop,None,fx=3,fy=3,interpolation=cv2.INTER_CUBIC)
                points=detect(detector,up)
                if points is not None:
                    points=points/3+np.float32((left,top))
                anchors[name].append(None if points is None else points[ANCHORS].round(3).tolist())
    (ROOT/"face_anchors.json").write_text(json.dumps(anchors,separators=(",",":"))+"\n")
    print("Face poses extracted:",{k:sum(v is not None for v in a) for k,a in anchors.items()})


if __name__=="__main__":
    main()
