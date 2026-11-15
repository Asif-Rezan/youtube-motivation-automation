"""Low-poly island scenes projected from 3D coordinates and composited with animated wildlife."""
import math
import random
from pathlib import Path
from functools import lru_cache

from PIL import Image, ImageColor, ImageDraw, ImageFont


FONT = Path(__file__).resolve().parents[1] / 'assets' / 'artwork' / 'Oswald.ttf'
TAU = 2 * math.pi


def polygon(draw, points, colour):
    draw.polygon([(round(x), round(y)) for x, y in points], fill=colour)


def radius(angle):
    return 1 + .08 * math.sin(angle * 3 + .9) + .07 * math.cos(angle * 5)


def height(x, y):
    return (.10 + 1.37 * math.exp(-((x+1.8)**2/6.5 + (y-.5)**2/3.0))
            + .48 * math.exp(-((x-2.6)**2/4.1 + (y-1.1)**2/2.3)))


@lru_cache(maxsize=256)
def shaded(colour, strength):
    r,g,b = ImageColor.getrgb(colour)
    return tuple(min(255,round(channel*strength)) for channel in (r,g,b))


def terrain_light(x, y):
    dx = (height(x+.08,y)-height(x-.08,y))/.16
    dy = (height(x,y+.08)-height(x,y-.08))/.16
    light = (.88 + .41*dx + .29*dy) / math.sqrt(1+dx*dx+dy*dy)
    return min(1.15,max(.72,round(light,2)))


def cloud(draw, x, y, width, height):
    polygon(draw, [(x,y),(x+.19*width,y-.4*height),(x+.38*width,y-.82*height),
                   (x+.63*width,y-height),(x+.83*width,y-.55*height),
                   (x+width,y),(x+.52*width,y+.12*height)], '#ecf8f5')
    polygon(draw, [(x,y),(x+.30*width,y-.18*height),(x+.78*width,y-.32*height),
                   (x+width,y),(x+.52*width,y+.12*height)], '#cbe8ec')


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
                colour = (int(16+9*blend), int(103+71*blend), int(153+36*blend))
            draw.line((0,y,width,y), fill=colour)
        if horizon:
            for x, y, w, h in ((.11,.13,.14,.031),(.62,.1,.17,.034),(.83,.18,.09,.018)):
                cloud(draw,x*width,y*screen_height,w*width,h*screen_height)
        for _ in range(330):
            x = rng.randrange(width)
            y = rng.randrange(max(horizon, 1), screen_height)
            length = rng.randrange(3, max(4, width//27))
            polygon(draw, [(x,y),(x+length,y-2),(x+length*.84,y+1),(x+2,y+3)],
                    rng.choice(['#47acc6','#379fbe','#54b4c7','#278fb0']))
        for multiplier, colour in [(1.15, '#45b8be'), (1.09, '#62c5c1'), (1.045, '#9cdbcc'),
                                   (1.014, '#dfebce')]:
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
                    x,y,_ = (sum(values)/3 for values in zip(*tri))
                    patch = .48 + .28*math.sin(x*1.7+y*.9) + .12*math.cos(y*2.9)
                    lush = ring < 8 and patch + rng.uniform(-.14,.14) < self.foraging
                    colour = shaded(rng.choice(green if lush else base),terrain_light(x,y))
                    depth = x*math.sin(self.turn) + y*math.cos(self.turn)
                    triangles.append((depth, tri, colour))
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
        for _ in range(34 if self.habitat == 'rocky island' else 17):
            x,y = rng.uniform(-5,5),rng.uniform(-2.5,2.5)
            if (x/5.15)**2+(y/2.55)**2>.91:
                continue
            px,py=self.project(x,y,height(x,y))
            s=self.scale*rng.uniform(.055,.16)
            draw.ellipse((px-s*.72,py-s*.10,px+s*1.42,py+s*.27),fill='#807553')
            polygon(draw,[(px-s,py),(px-s*.59,py-s*.79),(px+s*.24,py-s),
                          (px+s*.86,py-s*.49),(px+s,py),(px+s*.11,py+s*.15)],'#b9b39a')
            polygon(draw,[(px+s*.24,py-s),(px+s*.86,py-s*.49),(px+s,py),
                          (px+s*.11,py+s*.15),(px+s*.14,py-s*.30)],'#88846f')
        if self.habitat == 'wooded island':
            for _ in range(52):
                x,y = rng.uniform(-4.4,4.4),rng.uniform(-.4,2.1)
                if (x/4.9)**2+(y/2.55)**2>.8 or rng.random() > self.foraging:
                    continue
                px,py=self.project(x,y,height(x,y))
                s=self.scale*rng.uniform(.10,.19)
                draw.ellipse((px-s*.25,py-s*.13,px+s*.85,py+s*.23),fill='#526b37')
                draw.line((px,py,px,py-s*1.41),fill='#66543d',width=max(2,round(s*.14)))
                polygon(draw,[(px-s,py-s*.55),(px-s*.58,py-s*1.66),(px,py-s*2.39),
                              (px+s*.54,py-s*1.78),(px+s,py-s*.57)],'#31583b')
                polygon(draw,[(px-s,py-s*.55),(px-s*.58,py-s*1.66),(px,py-s*2.39),
                              (px+s*.22,py-s*.61)],'#557f49')
        return image

    def water_glints(self):
        rng = random.Random(81)
        pixels = self.base.load()
        for _ in range(100):
            x = rng.randrange(self.width)
            y = rng.randrange(self.screen_height//3,self.screen_height)
            r,g,b = pixels[x,y]
            if r < 60 and b > g and b-r > 95:
                yield x,y,rng.uniform(.55,1.15),rng.random()*TAU

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


def animal_sprite(colour, frame, grazing, species, scale=1):
    """Faceted body, muzzle, horns, and individually animated legs."""
    coat, light, shadow = (('#eee2bf','#fff5da','#b4a488') if colour == 0
                            else ('#746456','#a79277','#443c36'))
    sprite = Image.new('RGBA', (round(120*scale),round(100*scale)))
    draw = ImageDraw.Draw(sprite)
    def poly(points, pigment):
        polygon(draw, [(x*scale,y*scale) for x,y in points], pigment)

    def line(points, color, width):
        draw.line(tuple(v*scale for v in points),fill=color,width=max(1,round(width*scale)))

    def ellipse(box, color):
        draw.ellipse(tuple(v*scale for v in box),fill=color)

    swing = 9 * math.sin(frame * TAU / 12)
    for x, phase, dark in ((32,1,True),(74,-1,True),(38,-1,False),(80,1,False)):
        foot = x+phase*swing
        poly([(x-4,57),(x+4,57),(x+phase*swing*.5+3,76),(foot+3,92),
                       (foot-3,92),(x+phase*swing*.5-4,77)], shadow if dark else coat)
        poly([(foot-3,89),(foot+4,89),(foot+5,94),(foot-4,94)], '#423a31')
    poly([(22,44),(30,35),(44,31),(69,32),(83,39),(87,49),(76,62),(38,64),(24,56)],coat)
    poly([(22,44),(30,35),(44,31),(69,32),(83,39),(68,45),(37,46)],light)
    poly([(24,56),(40,53),(75,53),(87,49),(76,62),(38,64)],shadow)
    poly([(26,43),(13,31),(10,34),(20,48)],coat)
    n = round(19*grazing)
    if species == 'rabbit':
        n += 12
    poly([(72,45),(82,28+n),(96,26+n),(93,48+n),(81,55)],coat)
    poly([(82,28+n),(91,18+n),(104,21+n),(112,31+n),(109,39+n),
                   (94,40+n),(86,35+n)],light)
    poly([(101,28+n),(112,31+n),(109,39+n),(102,39+n)],shadow)
    poly([(89,24+n),(77,20+n),(78,26+n),(87,30+n)],shadow)
    if species == 'rabbit':
        for x, y in [(91,20+n),(99,21+n)]:
            poly([(x-4,y+4),(x-9,y-20),(x-5,y-25),(x,y-21),(x+4,y+4)], light)
            poly([(x-3,y),(x-6,y-18),(x-4,y-20),(x+1,y)], '#c78a86')
    elif species == 'deer':
        for x, y in [(91,18+n),(100,19+n)]:
            line((x,y,x-3,y-18,x-9,y-24),color='#62513c',width=3)
            line((x-3,y-14,x+4,y-22),color='#62513c',width=2)
        for x,y in [(37,42),(47,40),(57,41),(67,44)]:
            ellipse((x,y,x+3,y+3),color='#fff2ce')
    else:
        for x, y in [(92,20+n),(99,21+n)]:
            poly([(x-3,y+2),(x-5,y-7),(x-12,y-15),(x-5,y-13),(x+1,y-5),(x+3,y+1)],
                    '#73634f')
    ellipse((97,25+n,100,28+n),color='#241c13')
    return sprite


def frames(size, beat, duration, fps, *, species='goats', habitat='grassland island', overlay=True):
    world = Island(size, beat.camera, beat.forage, seed=177, habitat=habitat)
    kind = {'goats':'goat','deer':'deer','rabbits':'rabbit'}[species]
    figures = world.actors(beat.population, seed=903)
    glints = tuple(world.water_glints())

    @lru_cache(maxsize=768)
    def sprite_at(coat, phase, grazing, pixels, flip):
        sprite = animal_sprite(coat,phase,grazing,kind,pixels/120)
        return sprite.transpose(Image.Transpose.FLIP_LEFT_RIGHT) if flip else sprite
    w, h = size
    title_font = ImageFont.truetype(str(FONT), round(w*.034))
    small = ImageFont.truetype(str(FONT), round(w*.017))
    for index in range(round(duration*fps)):
        t = index/fps
        image = world.base.copy()
        draw = ImageDraw.Draw(image)
        for x,y,velocity,phase in glints:
            crest = max(0,math.sin(t*velocity*2.3+phase))
            if crest > .38:
                length = round(w*.018*crest)
                end = min(w-1,x+length)
                pixels = world.base.getpixel((end,y))
                if pixels[0] < 65 and pixels[2] > pixels[1]:
                    draw.line((x,y,end,y),fill=('#5db9cc' if crest>.72 else '#3ea0bd'),
                              width=max(1,w//1040))
        placed = []
        for x, y, angle, scale, coat in figures:
            walking = beat.action == 'walk'
            route = t*.47+angle
            sway = .54 * math.sin(route) if walking else .07 * math.sin(t*.77+angle)
            distance = .14 * math.cos(route) if walking else 0
            px, py = world.project(x+sway,y+distance,height(x+sway,y+distance))
            proportion = (.47 if beat.camera == 'aerial' else .91) * world.scale / 110 * scale
            if kind == "rabbit":
                proportion *= .68
            phase = int((t*10 + angle*2) % 12) if walking else 0
            graze = 0 if walking else round((.5+.5*math.sin(t*.91+angle))*4)/4
            lift = (max(0,math.sin((phase/12)*TAU))*9*proportion
                    if kind == 'rabbit' and walking else 0)
            placed.append((py,px,proportion,coat,phase,graze,math.cos(route)<0 and walking,lift))
        for py, px, scale, coat, phase, graze, flip, lift in sorted(placed):
            sprite = sprite_at(coat,phase,graze,max(12,round(120*scale)),flip)
            shadow = max(2, round(34*scale))
            px_safe, py_safe = min(w-1,max(0,round(px))), min(h-1,max(0,round(py)))
            ground = world.base.getpixel((px_safe,py_safe))
            shade = tuple(round(channel*.66) for channel in ground)
            depth = max(2,round(5*scale))
            draw.ellipse((px-shadow*.72,py-depth,px+shadow*1.28,py+depth),fill=shade)
            image.paste(sprite,(round(px-sprite.width/2),round(py-sprite.height*.94-lift)),sprite)
        # Ease the camera into each shot while keeping the overlay stationary.
        progress = min(1,t/max(duration,1))
        eased = progress*progress*(3-2*progress)
        margin = round(w*.031*eased)
        if margin:
            vertical = round(margin*h/w)
            pan = round(margin*{'aerial':0,'shore':.58,'pasture':-.48}[beat.camera])
            image = image.resize(size,Image.Resampling.BILINEAR,
                                 box=(margin+pan,vertical,w-margin+pan,h-vertical))
            draw = ImageDraw.Draw(image)
        if not overlay:
            yield image
            continue
        x, y = round(w*.035), round(h*.055)
        label = beat.label.upper()
        draw.text((x,y),label,font=title_font,fill='#fff4d9',stroke_width=max(2,w//390),stroke_fill='#252422')
        draw.text((x,y+round(w*.059)), 'ILLUSTRATIVE SIMULATION', font=small, fill='#ffffff',
                  stroke_width=1,stroke_fill='#28352d')
        counter = f'{beat.population:,} {species.upper()}'
        draw.text((round(w*.963), y),counter,anchor='rt',font=title_font,fill='#fff4d9',
                  stroke_width=max(2,w//390),stroke_fill='#252422')
        yield image
