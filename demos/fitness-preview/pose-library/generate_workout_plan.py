"""Use the project's Qwen runtime to propose new or existing workout movements."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from workout_plan import CLIPS, validate_plan

sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
TEXT={"type":"string"}
SCHEMA={
    "type":"object",
    "properties":{
        "theme":TEXT,"description":TEXT,
        "movements":{"type":"array","minItems":2,"maxItems":8,"items":{
            "type":"object","properties":{
                "movement":TEXT,"camera":TEXT,
                "poses":{"type":"array","minItems":5,"maxItems":5,"items":TEXT},
            },"required":["movement","camera","poses"],"additionalProperties":False,
        }},
    },"required":["theme","description","movements"],"additionalProperties":False,
}


def words(value):
    return " ".join(re.findall(r"[a-z0-9]+",value.casefold()))


def lookup(movement,camera):
    value=words(movement)
    aliases={
        "bodyweight squat":{"bodyweight squat","squat","squats"},
        "split squat":{"split squat","split squats","stationary lunge","stationary lunges"},
        "overhead reach":{"overhead reach","overhead reaches"},
        "dance step touch":{"dance step touch","step touch","step touches"},
        "low impact step jack":{"low impact step jack","step jack","step jacks"},
        "standing side stretch":{"standing side stretch","side stretch"},
    }
    angle=words(camera)
    for key,(_,label,view) in CLIPS.items():
        if value in aliases[words(label)] and words(view).split()[0] in angle.split():
            return key
    slug=words(movement).replace(" ","-")[:46] or "movement"
    suffix=hashlib.sha256((value+"|"+angle).encode()).hexdigest()[:9]
    return f"{slug}-{suffix}"


def generate(theme,seed,ask):
    prompt=(
        "Invent a realistic adult fitness, yoga, or dance routine matching the theme. "
        "You may choose new movements and any useful camera angle. For each movement "
        "describe exactly five observable full-body key poses in order, with limb "
        "placement, foot contact, weight shift, and a clear final pose. Start and end "
        "with a comfortable stance or describe the endpoint so it can be held. "
        "Return a short creative theme without exercise names and a description. "
        "Do not promise medical or fitness outcomes.\n"
        f"Requested theme: {theme}"
    )
    idea=ask(prompt,SCHEMA,seed,1400)
    motions={}
    clips=[]
    moves=[]
    for motion in idea["movements"]:
        key=lookup(motion["movement"],motion["camera"])
        if key not in CLIPS and key in motions and motions[key]!=motion:
            detail=hashlib.sha256(json.dumps(motion,sort_keys=True).encode()).hexdigest()[:5]
            key=f"{key}-{detail}"
        motions[key]=motion
        clips.append(key)
        moves.append(CLIPS[key][1] if key in CLIPS else motion["movement"])
    names=" + ".join(dict.fromkeys(moves))
    plan={"title":f"{idea['theme'].strip()} | {names}","description":idea["description"],
          "clips":clips,"motions":motions}
    validate_plan(plan)
    return plan


def main():
    from wildlife.generate import ask

    parser=argparse.ArgumentParser()
    parser.add_argument("--theme",required=True)
    parser.add_argument("--seed",type=int,default=7)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    plan=generate(args.theme,args.seed,ask)
    args.output.write_text(json.dumps(plan,indent=2)+"\n")


if __name__=="__main__":
    main()
