"""Animated coastal marsh with wading birds and a moving tidal waterline."""

from functools import lru_cache
import math
from random import Random

from PIL import Image, ImageDraw


SIZE = (1920, 1080)


def bird(draw, x, y, scale, seconds=0, *, flying=False, feeding=False):
    """Draw a shorebird in profile, with the feet anchored at the given point."""
    def points(vertices):
        return [(x + left * scale, y + top * scale) for left, top in vertices]

    def shape(vertices, color):
        draw.polygon(points(vertices), fill=color)

    def oval(left, top, right, bottom, color):
        draw.ellipse(points(((left, top), (right, bottom))), fill=color)

    if flying:
        wing = math.sin(seconds * 9) * 75
        shape([(-55,-72), (-160,-138-wing), (-121,-60), (-41,-44),
               (54,-75), (104,-151+wing), (31,-88)], '#415b63')
        oval(-56,-82,31,-48,'#d6d9ca')
        oval(16,-91,48,-65,'#f3ead4')
        shape([(42,-83),(87,-76),(44,-73)], '#242f35')
        return

    oval(-68,-6,57,3,'#827353')
    for dx in (-22, 16):
        draw.line(points(((dx,-66),(dx-8,-34),(dx+2,-3),(dx+19,0))),
                  fill='#bd7951', width=max(1,round(5*scale)))
    oval(-83,-99,54,-51,'#f2e9d0')
    shape([(-101,-80),(-62,-112),(33,-100),(13,-69),(-47,-64)], '#5b6c68')
    shape([(-87,-86),(-39,-105),(18,-92),(-16,-72)], '#88968b')
    dip = 55 * (.5 + .5 * math.sin(seconds * 3.6)) if feeding else 0
    oval(23,-130+dip,70,-88+dip,'#f5ead3')
    shape([(62,-114+dip),(129,-105+dip*1.25),(65,-101+dip)], '#253239')
    oval(54,-118+dip,61,-111+dip,'#192b31')


@lru_cache(maxsize=12)
def landscape(camera, level):
    """Paint stable terrain once per shot and let the foreground move independently."""
    image = Image.new('RGB', SIZE)
    draw = ImageDraw.Draw(image)
    rng = Random(279)
    horizon = {'shore': 332, 'pasture': 280, 'aerial': 178}[camera]
    waterline = 430 + round(447 * level)
    for y in range(SIZE[1]):
        if y < horizon:
            t = y / horizon
            color = (round(52+123*t), round(115+89*t), round(153+53*t))
        else:
            t = (y-horizon)/(1080-horizon)
            color = (round(58-27*t), round(143-61*t), round(153-52*t))
        draw.line((0,y,1920,y), fill=color)
    draw.ellipse((1460,97,1540,177), fill='#fff0bc')
    for ridge, color in ((45,'#71968a'), (21,'#4e756a')):
        peaks = [(x,horizon-rng.randint(1,ridge)) for x in range(0,2000,45)]
        draw.polygon([*peaks,(1980,horizon+19),(0,horizon+19)], fill=color)
    # The exposed flat shrinks toward the foreground as the tide comes in.
    bend = {'shore': 1, 'pasture': -1, 'aerial': .5}[camera]
    edge = [(x,waterline + round(80*math.sin(x/370)*bend) + round(26*math.sin(x/127)))
            for x in range(0,1961,28)]
    draw.polygon([*edge,(1960,1080),(0,1080)], fill='#b59a72')
    draw.line(edge, fill='#dbca9e', width=8)
    for _ in range(1300):
        x = rng.randrange(1920)
        y = rng.randrange(1080)
        ground = edge[x//28][1]
        if y > ground+9:
            ink = rng.choice(('#907a5c','#9f8763','#c3ae86','#cdb98d'))
            draw.line((x,y,x+rng.randrange(4,34),y+2), fill=ink,width=2)
    for i in range(420):
        x = rng.randrange(1920)
        y = rng.randrange(horizon+8,1060)
        if y < edge[x//28][1] and (x < 350 or x > 1480 or y < horizon+55):
            height = rng.randrange(13,85) * (y/850)
        elif y > edge[x//28][1]+30 and (x < 195 or x > 1700):
            height = rng.randrange(45,125)
        else:
            continue
        lean = rng.randrange(-35,36)
        draw.polygon([(x-4,y),(x+lean,y-height),(x+5,y)],
                     fill=('#415d3c','#67824b','#9ba362')[i%3])
    return image, edge, horizon


def tidal_frame(size, intensity, camera, seconds=0, *, shot=0, portrait=False):
    level = round(max(0, min(1, intensity)) * 20) / 20
    base, edge, horizon = landscape(camera, level)
    image = base.copy()
    draw = ImageDraw.Draw(image)
    for i in range(90):
        y = horizon + 8 + (i * 53) % (1055-horizon)
        x = (i*163 + seconds*(12+y/37)) % 1920
        if y < edge[int(x)//28][1]-13:
            width = 15 + (i%8+1) * (y-horizon)/27
            draw.line((x,y,x+width,y), fill=('#81b1af' if i%3 else '#afc9ba'), width=2)
    if portrait:
        bird(draw, 465, 1010, 4.1, feeding=False)
        bird(draw, 1230, 630, 1.75, flying=True)
        bird(draw, 1540, 540, 1.3, seconds=1, flying=True)
    else:
        count = max(1,round(6*(1-level)))
        for i in range(count):
            x = 390 + (i*273+shot*97+23*math.sin(seconds*.7+i)) % 1170
            water_edge = edge[int(x)//28][1]
            y = min(1035,water_edge+54+(i*37)%120)
            scale = (1.02 if camera == 'aerial' else 1.65) * (.65 + y/1550)
            bird(draw,x,y,scale,seconds+i,feeding=True)
        for i in range(2+round(level*3)):
            x = (seconds*(55+i*7)+i*245+shot*173) % 2270 - 160
            y = horizon+82+i*30+12*math.sin(seconds+i)
            bird(draw,x,y,.65+i*.09,seconds+i*.3,flying=True)
    return image if size == SIZE else image.resize(size,Image.Resampling.BILINEAR)
