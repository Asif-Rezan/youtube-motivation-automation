"""Composite the existing jungle art, trainer renders and coaching audio."""
from pathlib import Path
import math
import subprocess
import sys
import tempfile
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

HERE=Path(__file__).resolve().parent
W,H,FPS,SECONDS=1280,720,24,30
ACTOR=(191,88)
GREEN="#e7f58b"
CREAM="#fff9e9"
FONT=Path("/System/Library/Fonts/Supplemental")
FONTS={n:ImageFont.truetype(str(FONT/"Arial Bold.ttf"),n) for n in (18,21,31,47,65)}
BODY=ImageFont.truetype(str(FONT/"Arial.ttf"),21)


def make_audio(path):
    sr=44100
    time=np.arange(sr*SECONDS)/sr
    beat=60/110
    phase=time%beat
    kick=.09*np.sin(2*np.pi*(48*phase+3.6*(1-np.exp(-21*phase))))*np.exp(-23*phase)
    hi=.011*np.random.default_rng(712).normal(size=len(time))*np.exp(-61*(time%(beat*.5)))
    roots=np.array([130.81,116.54,103.83,110.])[np.floor(time/(beat*4)).astype(int)%4]
    pluck=.046*np.sin(2*np.pi*roots*(time%(beat*.5)))*np.exp(-6*(time%(beat*.5)))
    bed=(kick+hi+pluck)*np.minimum(time/.4,1)*np.minimum((SECONDS-time)/1.2,1)
    voice=np.zeros_like(time)
    with tempfile.TemporaryDirectory() as tmp:
        lines=[(0,HERE.parent/"trainer-3d/trainer-speaking.wav")]
        for i,(offset,text) in enumerate(((6., "Here we go. Sit back, then stand tall."),
                                 (13.5,"Keep a steady pace. Breathe on the way up."),
                                 (21., "Finish strong. One more controlled rep."),
                                 (26.1,"And relax. Great work."))):
            file=Path(tmp)/f"cue-{i}.aiff"
            subprocess.run(["say","-v","Samantha","-r","167","-o",str(file),text],check=True)
            lines.append((offset,file))
        for offset,file in lines:
            pcm=subprocess.check_output(["ffmpeg","-v","error","-i",str(file),"-f","f32le","-ar",str(sr),"-ac","1","-"])
            window=np.frombuffer(pcm,dtype="<f4")
            start=round(sr*offset)
            n=min(len(window),len(voice)-start)
            voice[start:start+n]+=window[:n]
            bed[start:start+n]*=.44
    with wave.open(str(path),"wb") as output:
        output.setparams((1,2,sr,0,"NONE","not compressed"))
        output.writeframes((32767*np.clip(voice*1.18+bed,-.94,.94)).astype("<i2").tobytes())


def background(with_shadow=True):
    jungle=Image.open(HERE.parent/"jungle.png").convert("RGB")
    out=ImageOps.fit(jungle,(W,H),centering=(.5,.55)).convert("RGBA")
    shadow=Image.new("RGBA",out.size)
    d=ImageDraw.Draw(shadow)
    d.ellipse((331,594,530,626),fill=(10,22,13,111))
    d.ellipse((355,599,491,616),fill=(10,18,13,60))
    if with_shadow:
        out.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(9)))
    header=Image.new("RGBA",out.size)
    d=ImageDraw.Draw(header)
    d.rounded_rectangle((45,44,392,128),radius=20,fill=(11,35,26,205))
    d.text((64,54),"JUNGLE WORKOUT",font=FONTS[31],fill=CREAM)
    d.text((65,98),"LOW IMPACT  /  NO EQUIPMENT",font=FONTS[18],fill=GREEN)
    out.alpha_composite(header)
    return out


def overlay(t):
    panel=Image.new("RGBA",(409,362))
    d=ImageDraw.Draw(panel)
    d.rounded_rectangle((0,0,408,361),radius=26,fill=(11,35,27,232),outline=(225,238,207,103),width=2)
    if t<6:
        label,title,cue="GET READY","Find Your Stance","Up next  ·  Bodyweight squat"
    elif t<25.5:
        rep=min(5,1+int((t-6)//3.9))
        label,title=f"REP  {rep} / 5","Bodyweight Squat"
        cue="Hips back  ·  Stand tall"
    else:
        label,title,cue="COOL DOWN","Nice Work","Relax your shoulders  ·  Breathe"
    d.text((27,25),label,font=FONTS[21],fill=GREEN)
    d.text((27,80),title,font=FONTS[31],fill=CREAM)
    d.text((24,128),f"0:{max(1,math.ceil(SECONDS-t)):02}",font=FONTS[65],fill=GREEN)
    d.text((28,224),cue,font=BODY,fill=CREAM)
    d.rounded_rectangle((28,283,379,294),radius=5,fill="#3f5750")
    progress=max(1,int(351*t/SECONDS))
    d.rounded_rectangle((28,283,28+progress,294),radius=5,fill=GREEN)
    d.text((28,311),"SESSION TIME",font=FONTS[18],fill="#c1d7c8")
    return panel


def composite(base, actor_path,t):
    frame=base.copy()
    actor=Image.open(actor_path).convert("RGBA")
    if t<6:
        actor=actor.resize((627,762),Image.Resampling.LANCZOS)
        frame.alpha_composite(actor,(126,-42))
    else:
        frame.alpha_composite(actor,ACTOR)
    frame.alpha_composite(overlay(t),(811,177))
    return frame.convert("RGB")


def main():
    frames=Path(sys.argv[1])
    base=background()
    intro=background(with_shadow=False)
    if len(sys.argv)>2 and sys.argv[2]=="--still":
        frame=next(iter(sorted(frames.glob("*.png"))))
        composite(base,frame,int(frame.stem)/FPS).save(HERE/"maya-jungle-short-poster.jpg",quality=94)
        return
    output=HERE/"maya-jungle-workout-refined-30s.mp4"
    motion_dir=Path(sys.argv[2]) if len(sys.argv)>2 else frames
    with tempfile.TemporaryDirectory() as tmp:
        audio=Path(tmp)/"coaching.wav"
        make_audio(audio)
        args=["ffmpeg","-v","error","-y","-f","rawvideo","-pix_fmt","rgb24",
              "-s",f"{W}x{H}","-r",str(FPS),"-i","-","-i",str(audio),
              "-c:v","libx264","-preset","veryfast","-crf","18","-pix_fmt","yuv420p",
              "-c:a","aac","-b:a","160k","-movflags","+faststart",str(output)]
        with subprocess.Popen(args,stdin=subprocess.PIPE) as stream:
            for index in range(SECONDS*FPS):
                t=index/FPS
                if 6<=t<25.5:
                    pose_index=144+round(((t-6)%3.9)*FPS)
                    actor_path=motion_dir/f"{pose_index:04}.png"
                else:
                    actor_path=frames/f"{index:04}.png"
                frame=composite(intro if t<6 else base,actor_path,t)
                if index==185:
                    frame.save(HERE/"maya-jungle-refined-poster.jpg",quality=94)
                stream.stdin.write(frame.tobytes())
            stream.stdin.close()
            if stream.wait():
                raise RuntimeError("Could not encode jungle workout")


if __name__=="__main__":
    main()
