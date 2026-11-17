"""Photo-based visemes and eye blinks driven by audio phone timing."""
import json

import cv2
import numpy as np

ANCHORS=np.float32(((83,97),(171,97),(128,137)))
ROUND={"OW","UW","UH","W","OY"}
OPEN={"AA","AE","AH","AO","AW","AY","EH","ER"}
CLOSED={"P","B","M","F","V"}
WIDE={"IY","IH","EY","Y","S","Z","SH","CH","JH"}

def vowel(label):
    if label in ROUND:
        return "round"
    if label in OPEN:
        return "open"
    if label in CLOSED:
        return "rest"
    if label in WIDE:
        return "smile"
    return "rest"


class FaceMotion:
    def __init__(self,root):
        self.face_pts=json.loads((root/"face_anchors.json").read_text())
        self.phones=json.loads((root/"demo_phones.json").read_text())
        self.patches={}
        for label in ("rest","open","round","smile","blink"):
            patch=cv2.imread(str(root/"faces"/(label+".png")),cv2.IMREAD_UNCHANGED)
            if patch is None or patch.shape!=(256,256,4):
                raise ValueError(f"Missing face asset: {label}")
            f=patch.astype(np.float32)/255.
            f[...,:3]*=f[...,3:4]
            self.patches[label]=f

    def mix(self,t):
        values={}
        for label,start,end in self.phones:
            distance=max(0.,start-t,t-end)
            if distance<.047:
                k=vowel(label)
                values[k]=values.get(k,0.)+(1-distance/.047)**2
        if not values:
            return self.patches["rest"],.18
        total=sum(values.values())
        mouth=sum((self.patches[k]*(weight/total) for k,weight in values.items()))
        return mouth,.90*min(1.,total)

    @staticmethod
    def composite(actor,patch,affine,weight):
        warped=cv2.warpAffine(patch,affine,(actor.shape[1],actor.shape[0]),
                              flags=cv2.INTER_LINEAR)
        alpha=warped[...,3:4]*weight
        if not np.any(alpha>.01):
            return actor
        # Remain inside the actor silhouette and use a feathered patch.
        allowed=(actor[...,3:4]>.18)*weight
        actor[...,:3]=np.clip(actor[...,:3]*(1-warped[...,3:4]*allowed)+
                              warped[...,:3]*allowed,0,1)
        return actor

    def apply(self,actor,name,index,next_index,progress,now,local_time):
        points=self.face_pts.get(name)
        if not points or points[index] is None or points[next_index] is None:
            return actor
        target=(1-progress)*np.asarray(points[index])+progress*np.asarray(points[next_index])
        affine=cv2.getAffineTransform(ANCHORS,target.astype(np.float32))
        result=actor.astype(np.float32)/255
        mouth,strength=self.mix(now)
        if strength<.2 and 2.35<local_time<3.2:
            mouth=self.patches["smile"]
            strength=.65
        self.composite(result,mouth,affine,strength)
        blink=max(max(0.,1-abs(local_time-mark)/.107) for mark in (.72,3.38))
        if blink>.05:
            self.composite(result,self.patches["blink"],affine,blink*.88)
        return np.rint(result*255).astype(np.uint8)
