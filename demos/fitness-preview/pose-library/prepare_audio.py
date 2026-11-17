"""Record the demo cues and align the generated audio to phonemes."""
import json
from pathlib import Path
import re
import subprocess
import tempfile

import numpy as np
from pocketsphinx import Decoder

ROOT=Path(__file__).resolve().parent
DURATION=22.5
CUES=((.27,"Ready? Bend your knees, then stand tall."),
      (13.7,"Reach up and breathe."),
      (18.25,"Now step to the beat. Nice work!"))

def align(pcm,text,offset):
    d=Decoder(samprate=16000,loglevel="ERROR")
    d.set_align_text(" ".join(re.findall(r"[a-z]+",text.lower())))
    for i in range(2):
        if i:
            d.set_alignment()
        d.start_utt()
        d.process_raw(pcm,full_utt=True)
        d.end_utt()
    return [[p.name,round(offset+p.start/100,3),round(offset+(p.start+p.duration)/100,3)]
            for p in d.get_alignment().phones() if p.name!="SIL" and p.duration>0]


def main():
    sr=44100
    t=np.arange(round(DURATION*sr))/sr
    phase=t%(60/108)
    eighth=t%(30/108)
    kick=.09*np.sin(2*np.pi*(49*phase+3.9*(1-np.exp(-23*phase))))*np.exp(-24*phase)
    hats=.012*np.random.default_rng(431).normal(size=len(t))*np.exp(-70*eighth)
    roots=np.array([146.83,130.81,110.,123.47])[np.floor(t/(240/108)).astype(int)%4]
    riff=.040*np.sin(2*np.pi*roots*eighth)*np.exp(-7*eighth)
    music=(kick+hats+riff)*np.minimum(1.,t/.28)*np.minimum(1.,(DURATION-t)/.95)
    voice=np.zeros_like(t)
    phones=[]
    with tempfile.TemporaryDirectory() as directory:
        for index,(offset,text) in enumerate(CUES):
            file=Path(directory)/f"cue-{index}.aiff"
            subprocess.run(["say","-v","Samantha","-r","156","-o",str(file),text],check=True)
            def decode(fmt,hz):
                return subprocess.check_output(["ffmpeg","-v","error","-i",str(file),"-f",fmt,"-ar",str(hz),"-ac","1","-"])
            phones.extend(align(decode("s16le",16000),text,offset))
            clip=np.frombuffer(decode("f32le",sr),dtype="<f4")
            point=round(offset*sr)
            clip=clip[:len(voice)-point]
            voice[point:point+len(clip)]+=clip
            music[point:point+len(clip)]*=.43
    if len(phones)<23:
        raise RuntimeError("Expected phoneme timing for all three cues")
    (ROOT/"demo_phones.json").write_text(json.dumps(phones,separators=(",",":"))+"\n")
    output=ROOT/"demo_audio.m4a"
    subprocess.run(["ffmpeg","-v","error","-y","-f","s16le","-ar",str(sr),"-ac","1","-i","-",
                    "-c:a","aac","-b:a","160k",str(output)],
                   input=(32767*np.clip(1.17*voice+music,-.96,.96)).astype("<i2").tobytes(),check=True)
    print(f"Aligned {len(phones)} phones")


if __name__=="__main__":
    main()
