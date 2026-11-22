"""Compile the AI workout prescription into an exact, continuous native-rig timeline.

Exercise keys refer to verified motion assets, never arbitrary AI bone rotations.
The source includes its own easing, stance, balance and foot roll. Retiming changes
pace without replacing that articulation with linear pose interpolation.
"""
from .timeline import FPS,TOTAL_FRAMES

def compile_sequence(plan):
    cycles=plan['cycles']
    if len(cycles)!=5:raise ValueError('Preview requires five prescribed repetitions')
    rows=[];start=0
    for rep,c in enumerate(cycles,1):
        if c.get('movement')!='heel_raise':raise ValueError('Movement has no verified rig motion: '+str(c.get('movement')))
        duration=c.get('duration')
        if type(duration) is not int or duration not in (10,12,14):raise ValueError('Unsafe or unsupported repetition timing')
        count=duration*FPS
        rows.append(dict(rep=rep,movement=c['movement'],start_frame=start,frames=count,
                         source_first=1,source_last=288,source_asset='kat-heel-raise-v1'))
        start+=count
    if start!=TOTAL_FRAMES:raise ValueError('AI workout durations must sum to exactly 60 seconds')
    return rows

def source_frame(sequence,frame):
    if type(frame) is not int or not 0<=frame<TOTAL_FRAMES:raise ValueError('Output frame outside workout')
    row=next((r for r in sequence if r['start_frame']<=frame<r['start_frame']+r['frames']),None)
    if row is None:raise ValueError('Gap in workout timeline')
    # Endpoints preserve the original grounded reset between repetitions.
    return row['source_first']+(row['source_last']-row['source_first'])*(frame-row['start_frame'])/(row['frames']-1)

def narration(plan,timing):
    rows=compile_sequence(plan);cues=[]
    for row,c in zip(rows,plan['cycles']):
        scale=row['frames']/(12*FPS)
        for phase,offset,window in timing:
            cues.append(dict(start=round(row['start_frame']/FPS+offset*scale,6),
                window=round(window*scale,6),text=c[phase],phase=phase,rep=row['rep']))
    return cues
