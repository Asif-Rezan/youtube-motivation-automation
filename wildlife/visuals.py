"""Low-poly island scenes projected from 3D coordinates and composited with animated goats."""
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


FONT = Path(__file__).resolve().parents[1] / 'assets' / 'artwork' / 'Oswald.ttf'
TAU = 2 * math.pi


def polygon(draw, points, colour):
    draw.polygon([(round(x), round(y)) for x, y in points], fill=colour)


def radius(angle):
    return 1 + .08 * math.sin(angle * 3 + .9) + .07 * math.cos(angle * 5)


def height(x, y):
    return (.10 + 1.37 * math.exp(-((x+1.8)**2/6.5 + (y-.5)**2/3.0))
            + .48 * math.exp(-((x-2.6)**2/4.1 + (y-1.1)**2/2.3)))


class Island:
    def __init__(self, size, camera, forage, seed, habitat):
        self.width, self.screen_height = size
        self.camera = camera
        self.foraging = forage
        self.habitat = habitat
        angles = {'aerial': (.88, .05, 0.75), 'shore': (.29, -.23, 1.32),
                  'pasture': (.48, .22, 1.14)}
        self.tilt, self.turn, scale = angles[camera]
        self.scale = self.width / 11 * scale
        self.baseline = self.screen_height * (.59 if camera == 'aerial' else .67)
        self.base = self.landscape(seed)

    def project(self, x, y, z):
        horizontal = x*math.cos(self.turn) - y*math.sin(self.turn)
        depth = x*math.sin(self.turn) + y*math.cos(self.turn)
        return (self.width*.5 + horizontal*self.scale,
                self.baseline - (depth*self.tilt + z*.91)*self.scale)

    def landscape(self, seed):
        rng = random.Random(seed)
        width, screen_height = self.width, self.screen_height
        image = Image.new('RGB', (width, screen_height))
        draw = ImageDraw.Draw(image)
        horizon = int(screen_height * (.24 if self.camera != 'aerial' else 0))
        for y in range(screen_height):
            if y < horizon:
                blend = y / max(1, horizon)
                colour = (int(37+79*blend), int(146+55*blend), int(211+31*blend))
            else:
                blend = (y-horizon) / max(1, screen_height-horizon)
                colour = (int(20+10*blend), int(140+67*blend), int(182+23*blend))
            draw.line((0,y,width,y), fill=colour)
        for _ in range(330):
            x = rng.randrange(width)
            y = rng.randrange(max(horizon, 1), screen_height)
            length = rng.randrange(3, max(4, width//27))
            polygon(draw, [(x,y),(x+length,y-2),(x+length*.84,y+1),(x+2,y+3)],
                    rng.choice(['#46b6d4','#38a9cb','#51c1d7','#2799c7']))
        for multiplier, colour in [(1.15, '#4bc6ce'), (1.07, '#79d7c7'), (1.025, '#b1e4c7')]:
            polygon(draw, [self.project(5.9*radius(a)*math.cos(a)*multiplier,
                                        3.3*radius(a)*math.sin(a)*multiplier, -.03)
                           for a in [j*TAU/72 for j in range(72)]], colour)
        rings = []
        for ring in range(10):
            fraction = ring / 9
            points = []
            for n in range(48):
                angle = (n + (ring%2)*.34)*TAU/48
                r = fraction*radius(angle)
                x, y = 5.9*r*math.cos(angle), 3.3*r*math.sin(angle)
                z = height(x,y)*(1-min(1, max(0,(fraction-.79)/.21))) + .08
                points.append((x,y,z))
            rings.append(points)
        base = ['#d9b76e','#e6c37e','#d6b16a','#cba767']
        green = {
            'wooded island': ['#345e36','#487747','#58844a','#6e914c','#57793e'],
            'marsh island': ['#568874','#638f76','#7b9b6c','#77a072','#629568'],
            'coastal dunes': ['#839477','#a4a675','#a9a96d','#c3b885','#8f9e72'],
            'rocky island': ['#5d6451','#747d63','#848775','#92967c','#798267'],
        }.get(self.habitat,['#769343','#849f48','#94a64e','#a5ab55','#6e873d'])
        if self.habitat == 'rocky island':
            base = ['#9c9884','#afab99','#89877c','#b8ad95']
        triangles = []
        for ring, (inner, outer) in enumerate(zip(rings,rings[1:])):
            for i in range(48):
                j = (i+1)%48
                for tri in [(inner[i], outer[i], outer[j]), (inner[i],outer[j],inner[j])]:
                    colour = rng.choice(green if ring < 8 and rng.random() < self.foraging else base)
                    triangles.append((sum(p[1] for p in tri), tri, colour))
        for _, tri, colour in sorted(triangles, key=lambda t: -t[0]):
            polygon(draw, [self.project(*p) for p in tri], colour)
        for _ in range(230):
            x, y = rng.uniform(-5,5), rng.uniform(-2.7,2.7)
            if (x/5.25)**2+(y/2.75)**2>.83 or rng.random() > self.foraging:
                continue
            px, py = self.project(x,y,height(x,y)+.04)
            s = self.scale * rng.uniform(.043,.096)
            polygon(draw, [(px-s,py),(px-s*.35,py-s*.85),(px+s*.40,py-s),
                           (px+s,py-s*.35),(px+s*.6,py+s*.2)], '#4e7438')
            polygon(draw, [(px-s,py),(px-s*.35,py-s*.85),(px+s*.40,py-s),(px,py-s*.35)],
                    '#6d9149')
        return image

    def actors(self, count, seed):
        rng = random.Random(seed)
        result = []
        for i in range(min(count, 112)):
            while True:
                x = rng.uniform(-4.3, 4.3)
                y = rng.uniform(-2.2, 2.2 if self.camera == 'aerial' else -.35)
                if (x/5)**2+(y/2.55)**2 < .72:
                    break
            if self.camera != 'aerial' and i < 2:
                x, y = -1.65 + i*1.75, -2.12+i*.13
            result.append((x,y,rng.random()*TAU,rng.uniform(.75,1.16),i%2))
        return result


def animal_sprite(colour, frame, grazing, species):
    """Faceted body, muzzle, horns, and individually animated legs."""
    coat, light, shadow = (('#eee2bf','#fff5da','#b4a488') if colour == 0
                            else ('#746456','#a79277','#443c36'))
    sprite = Image.new('RGBA', (120,100))
    draw = ImageDraw.Draw(sprite)
    swing = 9 * math.sin(frame * TAU / 12)
    for x, phase, dark in ((32,1,True),(74,-1,True),(38,-1,False),(80,1,False)):
        foot = x+phase*swing
        polygon(draw, [(x-4,57),(x+4,57),(x+phase*swing*.5+3,76),(foot+3,92),
                       (foot-3,92),(x+phase*swing*.5-4,77)], shadow if dark else coat)
        polygon(draw, [(foot-3,89),(foot+4,89),(foot+5,94),(foot-4,94)], '#423a31')
    polygon(draw, [(22,44),(30,35),(44,31),(69,32),(83,39),(87,49),(76,62),(38,64),(24,56)],coat)
    polygon(draw, [(22,44),(30,35),(44,31),(69,32),(83,39),(68,45),(37,46)],light)
    polygon(draw, [(24,56),(40,53),(75,53),(87,49),(76,62),(38,64)],shadow)
    polygon(draw, [(26,43),(13,31),(10,34),(20,48)],coat)
    n = 19 if grazing else 0
    if species == "rabbit":
        n += 12
    polygon(draw, [(72,45),(82,28+n),(96,26+n),(93,48+n),(81,55)],coat)
    polygon(draw, [(82,28+n),(91,18+n),(104,21+n),(112,31+n),(109,39+n),
                   (94,40+n),(86,35+n)],light)
    polygon(draw, [(101,28+n),(112,31+n),(109,39+n),(102,39+n)],shadow)
    polygon(draw, [(89,24+n),(77,20+n),(78,26+n),(87,30+n)],shadow)
    if species == 'rabbit':
        for x, y in [(91,20+n),(99,21+n)]:
            polygon(draw, [(x-4,y+4),(x-9,y-20),(x-5,y-25),(x,y-21),(x+4,y+4)], light)
            polygon(draw, [(x-3,y),(x-6,y-18),(x-4,y-20),(x+1,y)], '#c78a86')
    elif species == 'deer':
        for x, y in [(91,18+n),(100,19+n)]:
            draw.line((x,y,x-3,y-18,x-9,y-24),fill='#62513c',width=3)
            draw.line((x-3,y-14,x+4,y-22),fill='#62513c',width=2)
        for x,y in [(37,42),(47,40),(57,41),(67,44)]:
            draw.ellipse((x,y,x+3,y+3),fill='#fff2ce')
    else:
        for x, y in [(92,20+n),(99,21+n)]:
            polygon(draw, [(x-3,y+2),(x-5,y-7),(x-12,y-15),(x-5,y-13),(x+1,y-5),(x+3,y+1)],
                    '#73634f')
    draw.ellipse((97,25+n,100,28+n),fill='#241c13')
    return sprite


def frames(size, beat, duration, fps, *, species='goats', habitat='grassland island'):
    world = Island(size, beat.camera, beat.forage, seed=177, habitat=habitat)
    kind = {'goats':'goat','deer':'deer','rabbits':'rabbit'}[species]
    figures = world.actors(beat.population, seed=903)
    sprites = {(coat, phase, grazing): animal_sprite(coat, phase, grazing, kind)
               for coat in range(2) for phase in range(12) for grazing in (False, True)}
    w, h = size
    title_font = ImageFont.truetype(str(FONT), round(w*.043))
    small = ImageFont.truetype(str(FONT), round(w*.017))
    for index in range(round(duration*fps)):
        t = index/fps
        image = world.base.copy()
        draw = ImageDraw.Draw(image)
        placed = []
        for x, y, angle, scale, coat in figures:
            walking = beat.action == 'walk'
            sway = .51 * math.sin(t*.72+angle) if walking else .10 * math.sin(t*.77+angle)
            px, py = world.project(x+sway, y, height(x+sway,y))
            proportion = (.47 if beat.camera == 'aerial' else .91) * world.scale / 110 * scale
            if kind == "rabbit":
                proportion *= .68
            phase = int((t*10 + angle*2) % 12) if walking else 0
            graze = not walking and math.sin(t*.91+angle) > -.16
            placed.append((py, px, proportion, coat, phase, graze, math.cos(t*.72+angle) < 0 and walking))
        for py, px, scale, coat, phase, graze, flip in sorted(placed):
            sprite = sprites[coat, phase, graze]
            if flip:
                sprite = sprite.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            sprite = sprite.resize((max(1,round(120*scale)),max(1,round(100*scale))),Image.Resampling.BILINEAR)
            shadow = max(2, round(34*scale))
            draw.ellipse((px-shadow, py-3, px+shadow, py+3),fill='#756a45')
            image.paste(sprite, (round(px-sprite.width/2), round(py-sprite.height*.94)),sprite)
        # Slow push-in across each shot keeps the island motion distinct from the HUD.
        margin = round(w*.025*min(1,t/max(duration,1)))
        if margin:
            vertical = round(margin*h/w)
            image = image.resize(size, Image.Resampling.BILINEAR,
                                 box=(margin,vertical,w-margin,h-vertical))
            draw = ImageDraw.Draw(image)
        x, y = round(w*.035), round(h*.055)
        label = beat.label.upper()
        draw.text((x,y),label,font=title_font,fill='#fff4d9',stroke_width=max(2,w//390),stroke_fill='#252422')
        draw.text((x,y+round(w*.059)), 'ILLUSTRATIVE SIMULATION', font=small, fill='#ffffff',
                  stroke_width=1,stroke_fill='#28352d')
        counter = f'{beat.population:,} {species.upper()}'
        draw.text((round(w*.963), y),counter,anchor='rt',font=title_font,fill='#fff4d9',
                  stroke_width=max(2,w//390),stroke_fill='#252422')
        yield image
