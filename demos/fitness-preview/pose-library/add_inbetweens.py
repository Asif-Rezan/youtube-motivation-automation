"""Insert additional independently authored poses into each movement."""
import json
from pathlib import Path
import sys

import cv2
import mediapipe as mp
import numpy as np

from prepare_poses import extract, FOOT, H, W

ROOT=Path(__file__).resolve().parent
NAMES=("front","side","back","reach","dance")


def trunk(points):
    return float(np.linalg.norm((points[11,:2]+points[12,:2]-points[23,:2]-points[24,:2])*.5))


def fit_scale(image, points, original):
    old_length=max(1.,trunk(points))
    reference=np.asarray(original["points"],dtype=np.float32)
    ratio=float(np.clip(trunk(reference)/old_length,.84,1.20))
    transform=np.float32([[ratio,0,W/2*(1-ratio)],[0,ratio,FOOT*(1-ratio)]])
    image=cv2.warpAffine(image,transform,(W,H),flags=cv2.INTER_CUBIC)
    points[:,:2]=points[:,:2]*ratio+transform[:,2]
    return image,points


def match_quarter_height(image,points,before,after):
    desired=.25*(np.asarray(before["points"])[[11,12],1].sum()+
                 np.asarray(after["points"])[[11,12],1].sum())
    measured=float(points[[11,12],1].mean())
    delta=float(np.clip(desired-measured,-32.,32.))
    def amount(y):
        return delta*np.clip((FOOT-20-y)/max(1,FOOT-20-measured),0,1)
    yy,xx=np.indices((H,W),dtype=np.float32)
    image=cv2.remap(image,xx,yy-amount(yy),cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT)
    points[:,1]+=amount(points[:,1])
    return image,points


def main():
    cv2.setNumThreads(2)
    file=ROOT/"pose_catalog.json"
    catalog=json.loads(file.read_text())
    opts=mp.tasks.vision.PoseLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=sys.argv[1]),
        output_segmentation_masks=True,min_pose_detection_confidence=.2,
        min_pose_presence_confidence=.23,
    )
    with mp.tasks.vision.PoseLandmarker.create_from_options(opts) as model:
        for name in NAMES:
            original=[p for p in catalog[name] if "-between-" not in p["image"]]
            if len(original)!=3:
                raise ValueError(f"Expected the three original poses for {name}")
            sheet=cv2.imread(str(ROOT/"sheets"/(name+"-between.png")))
            if sheet is None:
                raise FileNotFoundError(f"{name}-between.png")
            extra=[]
            for i,span in enumerate(((.012,.495),(.505,.988))):
                image,points,_=extract(model,sheet,name+"-between",i,span,None)
                ref=original[0] if name=="dance" else original[min(i,1)]
                image,points=fit_scale(image,points,ref)
                if name in {"front","side","back"}:
                    image,points=match_quarter_height(image,points,original[i],original[i+1])
                path=f"poses/{name}-between-{i}.png"
                cv2.imwrite(str(ROOT/path),image)
                extra.append({"image":path,"points":points.round(3).tolist()})
            catalog[name]=[original[0],extra[0],original[1],extra[1],original[2]]
            print(f"{name}: {len(catalog[name])} authored poses",flush=True)
    file.write_text(json.dumps(catalog,separators=(",",":"))+"\n")


if __name__=="__main__":
    main()
