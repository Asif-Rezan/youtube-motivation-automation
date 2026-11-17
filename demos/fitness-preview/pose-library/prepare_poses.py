"""One-time CPU matte and pose landmark extraction for authored image sheets."""
from pathlib import Path
import json
import sys

import cv2
import mediapipe as mp
import numpy as np

ROOT=Path(__file__).resolve().parent
W,H=520,620
FOOT=603
SHEETS={
    "front":((.06,.33),(.34,.65),(.65,.93)),
    "side":((.021,.365),(.365,.683),(.660,1.)),
    "back":((.068,.286),(.385,.604),(.708,.945)),
    "dance":((.055,.332),(.337,.629),(.671,.963)),
    "reach":((.033,.263),(.267,.720),(.686,.979)),
}


def largest(binary):
    count, labels, stats, _=cv2.connectedComponentsWithStats(binary.astype(np.uint8))
    if count<=1:
        raise ValueError("No figure in the image")
    return labels==1+int(np.argmax(stats[1:,cv2.CC_STAT_AREA]))


def grab(photo, probable):
    likely=largest(probable>.24)
    labels=np.full(photo.shape[:2],cv2.GC_BGD,np.uint8)
    near=cv2.dilate(likely.astype(np.uint8),np.ones((31,31),np.uint8))>0
    labels[near]=cv2.GC_PR_BGD
    labels[likely]=cv2.GC_PR_FGD
    sure=cv2.erode((probable>.72).astype(np.uint8),np.ones((5,5),np.uint8))>0
    labels[likely&sure]=cv2.GC_FGD
    cv2.grabCut(photo,labels,None,np.zeros((1,65)),np.zeros((1,65)),3,cv2.GC_INIT_WITH_MASK)
    mask=largest(labels%2)*255
    return cv2.GaussianBlur(mask.astype(np.uint8),(5,5),.9)


def extract(detector,sheet,name,index,span,scale):
    h,w=sheet.shape[:2]
    left,right=(round(p*w) for p in span)
    photo=sheet[:,left:right].copy()
    # The middle reach pose shares its rectangular bounding box with the raised
    # fingers of the next pose. Remove those disconnected columns at the top.
    if name=="reach":
        y=round(h*.18)
        if index==1:
            cut=round(w*.671)-left
            photo[:y,cut:]=photo[:y,:1]
        if index==2:
            cut=round(w*.716)-left
            photo[y:, :cut]=photo[y:,cut:cut+1]
    photo=cv2.copyMakeBorder(photo,26,26,54,54,cv2.BORDER_REPLICATE)
    rgb=cv2.cvtColor(photo,cv2.COLOR_BGR2RGB)
    image=mp.Image(image_format=mp.ImageFormat.SRGB,data=rgb)
    found=detector.detect(image)
    if len(found.pose_landmarks)!=1:
        raise ValueError(f"Could not identify one figure in {name} pose {index}")
    mask=grab(photo,found.segmentation_masks[0].numpy_view().copy())
    ys,xs=np.where(mask>160)
    bottom=float(np.percentile(ys,99.8))
    top=float(np.min(ys))
    if scale is None:
        scale=(FOOT-44)/(bottom-top)
    # Foot anchor comes from the segmented shoe pixels, independent of which
    # legs the pose detector calls left/right in front and rear views.
    toes=xs[ys>bottom-20/scale]
    center=(float(np.percentile(toes,5))+float(np.percentile(toes,95)))*.5
    matrix=np.float32([[scale,0,W/2-center*scale],[0,scale,FOOT-bottom*scale]])
    rgba=np.dstack((photo,mask))
    normalized=cv2.warpAffine(rgba,matrix,(W,H),flags=cv2.INTER_CUBIC)
    anchors=np.float32([(p.x*photo.shape[1],p.y*photo.shape[0],p.visibility)
                        for p in found.pose_landmarks[0]])
    anchors[:,:2]=anchors[:,:2]*scale+matrix[:,2]
    return normalized,anchors,scale


def main():
    cv2.setNumThreads(2)
    opts=mp.tasks.vision.PoseLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=sys.argv[1]),
        output_segmentation_masks=True,min_pose_detection_confidence=.22,
        min_pose_presence_confidence=.25,
    )
    catalog={}
    with mp.tasks.vision.PoseLandmarker.create_from_options(opts) as detector:
        for name,spans in SHEETS.items():
            sheet=cv2.imread(str(ROOT/"sheets"/(name+".png")))
            if sheet is None:
                raise FileNotFoundError(name)
            scale=None
            catalog[name]=[]
            for index,span in enumerate(spans):
                image,points,scale=extract(detector,sheet,name,index,span,scale)
                path=f"poses/{name}-{index}.png"
                cv2.imwrite(str(ROOT/path),image)
                catalog[name].append({"image":path,"points":points.round(3).tolist()})
                print(name,index,round(scale,3),flush=True)
    (ROOT/"pose_catalog.json").write_text(json.dumps(catalog,separators=(",",":"))+"\n")


if __name__=="__main__":
    main()
