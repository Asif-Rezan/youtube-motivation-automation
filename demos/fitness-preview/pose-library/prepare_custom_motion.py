"""Produce image briefs or register authored sheets for new Qwen motions."""
import argparse
import json
from pathlib import Path

import cv2
import mediapipe as mp

from prepare_poses import extract
from workout_plan import CLIPS

IDENTITY=(
    "Same fair-skinned adult fitness trainer as the coral-red reference image. "
    "Chestnut ponytail, coral-red short sleeve sports top, teal leggings and ivory sneakers. "
    "Photorealistic full body, camera and scale locked, floor and gray backdrop consistent."
)


def brief(motion):
    cues=" ".join(f"Column {i}: {pose}." for i,pose in enumerate(motion["poses"],1))
    return (f"Five equal full-body columns. {IDENTITY} Camera: {motion['camera']}. "
            f"Movement: {motion['movement']}. {cues} Empty gutters, zero overlap, no text.")


def prepare(name,sheet_path,detector,output,spans=None):
    image=cv2.imread(str(sheet_path))
    if image is None:
        raise ValueError(f"Could not load {sheet_path}")
    poses=[]
    scale=None
    windows=spans if spans is not None else [(i/5,(i+1)/5) for i in range(5)]
    for index,window in enumerate(windows):
        frame,points,scale=extract(detector,image,name,index,window,scale)
        filename=f"{name}-{index}.png"
        cv2.imwrite(str(output/filename),frame)
        poses.append({"image":filename,"points":points.round(3).tolist()})
    return poses


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("plan",type=Path)
    parser.add_argument("--sheets",type=Path)
    parser.add_argument("--pose-model",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    plan=json.loads(args.plan.read_text())
    pending={k:plan["motions"][k] for k in plan["clips"] if k not in CLIPS}
    if not args.sheets:
        args.output.write_text(json.dumps({k:brief(v) for k,v in pending.items()},indent=2)+"\n")
        return
    if not args.pose_model:
        parser.error("--pose-model is needed to prepare the supplied sheets")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    opts=mp.tasks.vision.PoseLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(args.pose_model)),
        output_segmentation_masks=True,min_pose_detection_confidence=.2,min_pose_presence_confidence=.23,
    )
    catalog={}
    with mp.tasks.vision.PoseLandmarker.create_from_options(opts) as detector:
        for key in pending:
            catalog[key]=prepare(key,args.sheets/(key+".png"),detector,args.output.parent)
    args.output.write_text(json.dumps(catalog,separators=(",",":"))+"\n")


if __name__=="__main__":
    main()
