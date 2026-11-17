"""Resolve workout movements to existing or newly authored pose sequences."""
import re

CLIPS={
    "squat_front":("front","Bodyweight Squat","FRONT VIEW"),
    "squat_side":("side","Bodyweight Squat","SIDE VIEW"),
    "squat_back":("back","Bodyweight Squat","BACK VIEW"),
    "reach_front":("reach","Overhead Reach","FRONT VIEW"),
    "step_touch_front":("dance","Dance Step-Touch","FRONT VIEW"),
    "split_squat_side":("lunge","Split Squat","SIDE VIEW"),
    "step_jack_front":("jack","Low-Impact Step Jack","FRONT VIEW"),
    "side_stretch_front":("stretch","Standing Side Stretch","FRONT VIEW"),
}
DEFAULT_PLAN={"title":"Jungle Workout: Squat, Overhead Reach and Step-Touch",
              "description":"Bodyweight squats from three views, an overhead reach and a step-touch.",
              "clips":["squat_front","squat_side","squat_back","reach_front","step_touch_front"]}


def validate_plan(plan,catalog=None):
    if not isinstance(plan,dict) or not {"title","description","clips"}<=set(plan):
        raise ValueError("The workout plan requires a title, description and clips")
    title,description,clips=plan["title"],plan["description"],plan["clips"]
    if not isinstance(title,str) or not title.strip():
        raise ValueError("The plan needs a title")
    if not isinstance(description,str) or not description.strip():
        raise ValueError("The plan needs a description")
    if not isinstance(clips,list) or not clips:
        raise ValueError("The workout plan needs at least one movement")
    definitions=plan.get("motions",{})
    shots=[]
    pending=[]
    for key in clips:
        if not isinstance(key,str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,79}",key):
            raise ValueError("Invalid motion identifier")
        if key in CLIPS:
            name,label,view=CLIPS[key]
        else:
            motion=definitions.get(key)
            if not motion:
                raise ValueError(f"Missing motion definition: {key}")
            name,label,view=key,motion["movement"],motion["camera"].upper()
        if catalog is not None and name not in catalog:
            pending.append(name)
        shots.append((name,label,view))
    if pending:
        raise ValueError("Prepare pose images for: "+", ".join(dict.fromkeys(pending)))
    return shots
