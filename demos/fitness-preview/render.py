"""Render short fitness previews using a reusable projected joint rig."""
from pathlib import Path
import math
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent
W, H, FPS = 1280, 720, 24
DURATION = 72
SKIN = (174, 105, 68)
TEAL = (19, 116, 119)
DARK = (18, 69, 79)
HAIR = (51, 31, 30)
SHOE = (232, 221, 192)
WHITE = '#fff9e9'

CLASSES = {
    'workout': {
        'title': 'Jungle Cardio', 'subtitle': 'LOW IMPACT  /  NO EQUIPMENT',
        'accent': '#eaff8b', 'mat': '#344b47', 'bpm': 116,
        'moves': ['March in Place', 'Bodyweight Squat', 'Side Step + Reach'],
        'cues': ['Stand tall · alternate knees', 'Hips back · stand tall', 'Step wide · reach up'],
        'voice': [(0, 'Welcome to jungle cardio. Three low impact moves. Let’s get started.'), (10, 'March in place. Stand tall and swing your arms gently.'), (22, 'Ten seconds left. Keep your own pace.'), (29, 'Next up, bodyweight squats.'), (32, 'Send your hips back, then stand tall. Keep your heels down.'), (47, 'Five seconds. Finish your last rep.'), (52, 'Next, side step and reach.'), (54, 'Step to one side and reach up. Bring it back and switch sides.'), (67, 'And relax. Nice work.')],
    },
    'yoga': {
        'title': 'Jungle Yoga', 'subtitle': 'GENTLE FLOW  /  STANDING',
        'accent': '#ffd1ad', 'mat': '#735159', 'bpm': 82,
        'moves': ['Mountain to Upward Reach', 'Warrior II', 'Standing Side Bend'],
        'cues': ['Inhale to reach · exhale to lower', 'Reach both ways · switch halfway', 'Reach up and over · alternate sides'],
        'voice': [(0, 'Welcome to jungle yoga. Find a steady stance, and take an easy breath.'), (10, 'Mountain pose. Inhale as your arms rise. Exhale as they lower.'), (27, 'Coming up, warrior two.'), (32, 'Step wide and bend your front knee. Extend both arms and look over your front hand.'), (42, 'Come through center. Switch sides.'), (51, 'Next, a standing side bend.'), (54, 'Reach one arm up and over. Return to center, then switch.'), (67, 'Lower your arms. Take one last easy breath.')],
    },
}


def color(rgb, value):
    return tuple(max(0, min(255, int(channel * value))) for channel in rgb)


def font(size, bold=False):
    path = '/System/Library/Fonts/Supplemental/Arial'
    return ImageFont.truetype(path + (' Bold.ttf' if bold else '.ttf'), size)


FONTS = {s: font(s, s != 25) for s in (18, 25, 30, 42, 52, 69)}


def smooth(x):
    x = min(1, max(0, x))
    return x * x * (3 - 2 * x)


def pose(mode, move, t):
    cycle = math.tau * t
    hip = np.array([0., 1.01, 0.])
    lean = reach = stride = bend = spread = step_out = 0.
    if mode == 'workout':
        if move == 0:
            stride = math.sin(cycle / 1.15)
            hip[1] += .038 * abs(stride)
        elif move == 1:
            bend = (1 - math.cos(cycle / 3.2)) * .5
            hip += [0, -.32 * bend, -.33 * bend]
        elif move == 2:
            reach = math.sin(cycle / 3.4)
            hip[0] = .29 * reach
            step_out = .44 * abs(reach)
    elif move == 0:
        lift = (1 - math.cos(cycle / 7.3)) * .5
        reach = lift
        hip[1] += .025 * lift
    elif move == 1:
        side = -1 if t < 11 else 1
        strength = smooth((t % 11) / 2) * smooth((11 - t % 11) / 1.4)
        spread = .49 * strength
        bend = .55 * strength
        hip += [side * .20 * strength, -.25 * strength, 0]
        reach = side * strength
    elif move == 2:
        reach = math.sin(cycle / 8.2)
        lean = -.22 * reach
    else:
        hip[1] += .012 * math.sin(cycle / 2.4)
    neck = hip + [lean, .57 - .08 * bend, .42 * bend if mode == 'workout' else 0]
    head = neck + [.03 * reach, .18, .012]
    limbs = []
    for side in (-1, 1):
        lift = max(0., side * stride)
        leading = max(0., side * reach)
        step = step_out if leading else 0.
        step_lift = .11 * math.sin(math.pi * leading) if step else 0.
        foot = np.array([side * (.16 + spread + step), .065 + .22 * lift + step_lift, .31 * lift])
        thigh = hip + [side * .116, 0, 0]
        knee = (foot + thigh) * .5 + [0, .08 * lift, .27 * bend + .26 * lift + .015]
        shoulder = neck + [side * .208, -.064, 0]
        elbow = shoulder + [side * .075, -.27, -.14 * side * stride]
        hand = elbow + [side * .035, -.245, -.17 * side * stride + .045]
        if mode == 'workout' and move == 1:
            elbow += [side * .034 * bend, .14 * bend, .25 * bend]
            hand += [-side * .14 * bend, .44 * bend, .47 * bend]
        if (mode == 'workout' and move == 2) or (mode == 'yoga' and move == 2):
            up = max(0, side * reach)
            elbow = shoulder + [side * (.075 + .17 * up), -.27 + .49 * up, .04 * up]
            hand = elbow + [side * (.035 - .10 * up), -.245 + .53 * up, .04]
        if mode == 'yoga' and move == 0:
            a = math.pi * .94 * reach
            elbow = shoulder + [side * (.07 + .265 * math.sin(a)), -.278 * math.cos(a), .018]
            hand = elbow + [side * (.02 + .245 * math.sin(a + .2)), -.251 * math.cos(a + .2), .025]
        if mode == 'yoga' and move == 1:
            a = abs(reach)
            elbow = shoulder + [side * (.075 + .21 * a), -.27 * (1 - a), 0]
            hand = elbow + [side * (.035 + .245 * a), -.245 * (1 - a), 0]
            knee[0] += side * .12 * bend if side * reach > 0 else 0
        limbs.append((thigh, knee, foot, shoulder, elbow, hand))
    return hip, neck, head, limbs


def trainer(frame, mode, move, t):
    hip, neck, head, limbs = pose(mode, move, t)
    yaw = (.29 if mode == 'workout' else -.20)
    if mode == 'workout' and move == 1:
        yaw = -.62
    scale = 225
    cx = 531 if mode == 'workout' else 555
    floor = 601

    def pt(p):
        x, y, z = p
        return np.array([cx + scale * (math.cos(yaw)*x + math.sin(yaw)*z),
                         floor - scale * (y + .13 * z)])

    draw = ImageDraw.Draw(frame)

    def oval(p, rx, ry, rgb):
        x, y = pt(p)
        rx, ry = scale * rx, scale * ry
        for i in range(9):
            a = 1 - i * .082
            dx = -rx * i * .035
            dy = -ry * i * .045
            draw.ellipse((x-rx*a+dx,y-ry*a+dy,x+rx*a+dx,y+ry*a+dy),
                         fill=color(rgb, .76 + i*.056))

    def segment(a, b, ra, rb, rgb):
        pa, pb = pt(a), pt(b)
        vector = pb - pa
        normal = np.array([-vector[1], vector[0]]) / max(.01, np.linalg.norm(vector))
        ea, eb = normal * ra * scale, normal * rb * scale
        for i in range(10):
            left, right = i / 5 - 1, (i + 1) / 5 - 1
            points = [pa+ea*left, pa+ea*right, pb+eb*right, pb+eb*left]
            draw.polygon([tuple(p) for p in points], fill=color(rgb, .75 + .35 * math.sin(math.pi * (i+.5) / 10)))

    for thigh, knee, foot, shoulder, elbow, hand in sorted(limbs, key=lambda l: l[0][0] * math.sin(yaw)):
        oval(knee, .069, .070, DARK)
        segment(thigh, knee, .109, .068, TEAL)
        segment(knee, foot+[0, .035,0], .068, .037, DARK)
        oval(foot + [0,-.019,.055], .080, .041, color(SHOE,.86))
        oval(foot + [0,.004,.06], .071, .037, SHOE)
    oval(hip+[0,.045,0], .222, .145, DARK)
    waist = hip * .62 + neck * .38
    chest = neck*.78 + hip*.22
    segment(hip+[0,.04,0], waist, .201,.161,TEAL)
    segment(waist, chest, .161,.225,TEAL)
    oval(chest, .225, .104, TEAL)
    segment(chest+[0,.052,0], neck+[0,.055,0], .071,.061,SKIN)
    for _, _, _, shoulder, elbow, hand in limbs:
        oval(shoulder, .073,.078,SKIN)
        segment(shoulder, elbow,.069,.043,SKIN)
        oval(elbow,.043,.046,SKIN)
        segment(elbow,hand,.043,.029,SKIN)
        oval(hand,.038,.045,SKIN)

    sway = .024 * math.sin(t * 4)
    oval(head+[-.13+sway,-.06,-.10], .076,.145,HAIR)
    oval(head+[0,.03,-.022],.140,.163,HAIR)
    oval(head+[0,-.015,.035],.110,.133,SKIN)
    oval(head+[-.025,.098,.037],.113,.060,HAIR)
    oval(head+[-.075,.15,-.03],.065,.049,HAIR)
    for side in (-1,1):
        eye = pt(head+[side*.047,.015,.113])
        x,y = eye
        draw.ellipse((x-4,y-2,x+4,y+2), fill='#fff1d9')
        draw.ellipse((x-1,y-2,x+3,y+2), fill='#332522')
        draw.arc((x-5,y-8,x+5,y-2), 186, 342, fill='#493029', width=2)
    x,y = pt(head+[.005,-.054,.13])
    draw.arc((x-8,y-4,x+8,y+6), 8,169, fill='#662e29',width=2)


def background(mode):
    photo = Image.open(ROOT / ('bamboo.png' if mode == 'yoga' else 'jungle.png')).convert('RGB')
    out = ImageOps.fit(photo, (W,H), centering=(.5,.61)).convert('RGBA')
    shade = Image.new('RGBA', (W,H))
    draw = ImageDraw.Draw(shade)
    for y in range(H):
        alpha = int(95 * max(0, (215-y)/215) + 72 * max(0,(y-530)/190))
        draw.line((0,y,W,y),fill=(6,25,21,alpha))
    out.alpha_composite(shade)
    props = [('fern', -25, 552, 235), ('flowers', 1033, 594, 245), ('rock', 141, 624, 103), ('palm', -119, 245, 209)]
    if mode == 'yoga':
        props = [('orchid', 4, 571, 205), ('monstera', 1010, 542, 280), ('rock', 200, 630, 115)]
    for name,x,y,w in props:
        file = ROOT/f'{name}.png'
        if file.exists():
            tile = Image.open(file).convert('RGBA')
            tile = tile.resize((w, round(tile.height*w/tile.width)),Image.Resampling.LANCZOS)
            out.alpha_composite(tile,(x,y))
    return out.convert('RGB')


def frame_at(base, mode, i, photo=False, speech=0.):
    c = CLASSES[mode]
    t = i / FPS
    move = -1 if t < 10 or t >= 67 else 0 if t < 32 else 1 if t < 54 else 2
    starts = (10,32,54)
    ends = (32,54,67)
    left = (ends[move] if move >= 0 else 10 if t < 10 else 72) - t
    start = starts[move] if move >= 0 else 0 if t < 10 else 67
    elapsed = t-start
    frame = base.copy()
    d = ImageDraw.Draw(frame, 'RGBA')
    d.ellipse((315,576,747,643), fill=(8,21,16,68))
    d.polygon([(335,602),(693,602),(757,638),(277,638)], fill=c['mat'])
    d.line([(277,637),(757,637)], fill=(245,240,203,100), width=2)
    d.ellipse((426,587,634,610), fill=(10,32,30,117))
    if photo:
        from photo_trainer import trainer as animate_photo
        animate_photo(frame, mode, move, elapsed, t, speech)
    else:
        trainer(frame,mode,move,elapsed)
    d = ImageDraw.Draw(frame,'RGBA')
    d.text((48,40), c['title'], font=FONTS[52],fill=WHITE,stroke_width=2,stroke_fill='#193125')
    d.text((51,107), c['subtitle'], font=FONTS[18],fill=c['accent'],stroke_width=1,stroke_fill='#193125')
    d.rounded_rectangle((844,198,1232,564),radius=30,fill=(8,29,28,235),outline=(245,245,225,100),width=2)
    label = f'MOVE  {move+1} / 3' if move >= 0 else 'GET READY' if t<10 else 'SESSION COMPLETE'
    d.text((876,224),label,font=FONTS[18],fill=c['accent'])
    title = c['moves'][move] if move >= 0 else 'Find Your Space' if t < 10 else 'Nice Work'
    words = title.split()
    lines = ['']
    for word in words:
        trial = (lines[-1]+' '+word).strip()
        if d.textlength(trial,font=FONTS[42]) > 322 and lines[-1]:
            lines.append(word)
        else:
            lines[-1] = trial
    for j,line in enumerate(lines):
        d.text((875,258+j*43),line,font=FONTS[42],fill=WHITE)
    seconds = math.ceil(left)
    d.text((873,355),f'0:{seconds:02d}',font=FONTS[69],fill=c['accent'])
    d.rounded_rectangle((878,438,1197,448),radius=5,fill='#35524b')
    d.rounded_rectangle((878,438,878+max(1,round(319*t/72)),448),radius=5,fill=c['accent'])
    cue = c['cues'][move] if move >= 0 else 'Follow the trainer' if t < 10 else 'Bring your breathing down'
    d.text((877,466),cue,font=FONTS[18],fill=WHITE)
    if move < 2 and t < 67:
        d.text((877,514),'UP NEXT   '+c['moves'][move+1],font=FONTS[18],fill=c['accent'])
    elif move == 2:
        d.text((877,514),'UP NEXT   Cool down',font=FONTS[18],fill=c['accent'])
    return frame


def soundtrack(mode):
    sr = 44100
    c = CLASSES[mode]
    t = np.arange(DURATION*sr) / sr
    beat = 60 / c['bpm']
    step = t % beat
    bar = (t / (beat*4)).astype(int)
    roots = np.array([130.81,110,87.31,98])[bar % 4]
    kick = .18 * np.sin(2*np.pi*(47*step+4*(1-np.exp(-22*step)))) * np.exp(-22*step)
    hats = .025 * np.random.default_rng(241).normal(size=len(t)) * np.exp(-60*(t % (beat*.5)))
    pluck = .07 * np.sin(2*np.pi*roots*(t%(beat*.5))) * np.exp(-6*(t%(beat*.5)))
    chord = sum(np.sin(2*np.pi*m*roots*(t%(beat*4))) for m in (2,2.52,3))
    music = (kick+hats+pluck + .014 * chord) * np.minimum(1,t/.7)*np.minimum(1,(DURATION-t)/1.1)
    if mode == 'yoga':
        music *= .58
    for mark in (10, 32, 54, 67):
        length = int(.36 * sr)
        bell_t = np.arange(length) / sr
        bell = np.sin(math.tau * 784 * bell_t) * np.exp(-12 * bell_t)
        music[mark*sr:mark*sr+length] += .055 * bell
    voice = np.zeros_like(t)
    tmp = ROOT/f'{mode}-line.aiff'
    try:
        for offset,line in c['voice']:
            subprocess.run(['say','-v','Samantha','-r','174' if mode=='workout' else '158','-o',str(tmp),line],check=True)
            pcm = subprocess.check_output(['ffmpeg','-v','error','-i',str(tmp),'-f','f32le','-ar',str(sr),'-ac','1','-'])
            samples = np.frombuffer(pcm,dtype='<f4')
            at = int(sr*offset)
            samples = samples[:len(voice)-at]
            voice[at:at+len(samples)] += samples
            music[at:at+len(samples)] *= .42
    finally:
        tmp.unlink(missing_ok=True)
    path = ROOT/f'{mode}-audio.wav'
    with wave.open(str(path),'wb') as wav:
        wav.setparams((1,2,sr,0,'NONE','not compressed'))
        wav.writeframes((32767*np.clip(music+voice*1.20,-.95,.95)).astype('<i2').tobytes())
    blocks = voice.reshape(DURATION * FPS, -1) if sr % FPS == 0 else None
    if blocks is None:
        edges = np.rint(np.arange(DURATION*FPS+1) * sr/FPS).astype(int)
        rms = np.array([np.sqrt(np.mean(voice[a:b]**2)) for a,b in zip(edges[:-1],edges[1:])])
    else:
        rms = np.sqrt(np.mean(blocks**2,axis=1))
    envelope = np.clip(np.convolve(rms,[.17,.67,.16],mode='same')*8.5,0,1)
    return path, envelope


if __name__ == '__main__':
    mode = sys.argv[1]
    b = background(mode)
    photo = '--photo' in sys.argv
    stem = f'{mode}-photo' if photo else mode
    frame_at(b,mode,17*FPS,photo).save(ROOT/f'{stem}-preview.jpg',quality=92)
    if '--still' in sys.argv:
        sys.exit()
    audio, envelope = soundtrack(mode)
    output = ROOT / f'jungle-{stem}-sample.mp4'
    enc = subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pixel_format','rgb24',
                            '-video_size',f'{W}x{H}','-framerate',str(FPS),'-i','-','-i',str(audio),
                            '-c:v','libx264','-preset','veryfast','-crf','18','-pix_fmt','yuv420p',
                            '-c:a','aac','-b:a','160k','-movflags','+faststart',str(output)],stdin=subprocess.PIPE)
    with enc.stdin:
        for i in range(DURATION*FPS):
            enc.stdin.write(frame_at(b,mode,i,photo,envelope[i]).tobytes())
    if enc.wait():
        raise SystemExit('ffmpeg failed')
    audio.unlink()
