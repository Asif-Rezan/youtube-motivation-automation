"""Scan successive decoded subject frames, excluding authored camera cuts."""
import argparse
from pathlib import Path

import cv2
import numpy as np


def scan(path,shot_seconds):
    cap=cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError(f"Cannot read {path}")
    width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps=cap.get(cv2.CAP_PROP_FPS)
    shot_frames=round(fps*shot_seconds)
    if shot_frames<2:
        raise ValueError("Clip is too short for a temporal check")
    previous=None
    count=0
    scores={}
    try:
        while True:
            ok,frame=cap.read()
            if not ok:
                break
            if frame.shape[:2]!=(height,width):
                raise ValueError(f"Unexpected size at frame {count}")
            gray=cv2.cvtColor(frame[15:645,187:710],cv2.COLOR_BGR2GRAY)
            sample=cv2.resize(gray,(130,158),interpolation=cv2.INTER_AREA)
            if previous is not None and count%shot_frames:
                changed=cv2.absdiff(sample,previous)>24
                scores.setdefault(count//shot_frames,[]).append(float(changed.mean()))
            previous=sample
            count+=1
    finally:
        cap.release()
    if count==0:
        raise ValueError("No decoded frames")
    print(f"Scanned {count} frames at {fps:.3g} fps")
    for shot,values in scores.items():
        print(f"Shot {shot+1}: p95 changed area {np.quantile(values,.95):.1%}, peak {max(values):.1%}")
    return count


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("video",type=Path)
    parser.add_argument("--shot-seconds",type=float,default=4.5)
    parser.add_argument("--expected-frames",type=int)
    args=parser.parse_args()
    count=scan(args.video,args.shot_seconds)
    if args.expected_frames and count!=args.expected_frames:
        raise SystemExit(f"Expected {args.expected_frames} frames, decoded {count}")


if __name__=="__main__":
    main()
