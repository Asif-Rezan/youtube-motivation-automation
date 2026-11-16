"""Draw a native 1920×1080 low-poly cover from the actual episode."""
from datetime import date
from functools import lru_cache
from pathlib import Path
from random import Random

from PIL import Image, ImageColor, ImageDraw, ImageEnhance, ImageFont

from .metadata import thumbnail_hook
from .visuals import FONT, Island, animal_sprite, height

SIZE = (1920,1080)
THUMBNAIL_MAX_BYTES = 2 * 1024**2


CUES = ('arrow', 'question', 'spotlight', 'trail')
AMBER = '#ffcf34'
ARROW_RED = '#f52d40'
INK = '#301b12'
CREAM = '#fff6dd'


def cover_font(size):
    font = ImageFont.truetype(str(FONT), size)
    font.set_variation_by_axes([700])
    return font


def episode_cue(episode):
    if episode.startswith('auto-'):
        return CUES[date.fromisoformat(episode[5:15]).toordinal() % len(CUES)]
    return 'arrow'


def draw_cue(image, cue, *, arrow_offset=(0,0)):
    draw = ImageDraw.Draw(image)
    if cue == 'arrow':
        points = [(1772,244),(1792,300),(1649,371),(1674,410),
                  (1501,453),(1540,291),(1578,328)]
        dx,dy = arrow_offset
        points = [(x+dx,y+dy) for x,y in points]
        draw.polygon(points,fill=ARROW_RED)
        draw.line([*points,points[0]],fill='#fff6e8',width=22,joint='curve')
        draw.line([*points,points[0]],fill='#43131d',width=8,joint='curve')
    elif cue == 'question':
        symbol = cover_font(330)
        draw.text((1460,440),'?',anchor='mm',font=symbol,fill=CREAM,stroke_width=17,stroke_fill=INK)
    elif cue == 'spotlight':
        box = (1465,369,1815,639)
        draw.ellipse(box,outline=INK,width=23)
        draw.ellipse(box,outline=AMBER,width=12)
    elif cue == 'trail':
        points = [(1800,278),(1754,336),(1702,388),(1646,434),(1583,468)]
        for x,y in points:
            draw.ellipse((x-13,y-13,x+13,y+13),fill=AMBER,outline=INK,width=5)
        end = [(1562,439),(1493,502),(1586,515)]
        draw.polygon(end,fill=AMBER)
        draw.line([*end,end[0]],fill=INK,width=8,joint='curve')
    else:
        raise ValueError('Unknown thumbnail cue')


def render_thumbnail(beats, target: Path, *, label='AFTER THE BOOM', species='goats',
                     habitat='grassland island', cue='arrow'):
    before = beats[0]
    # Use the strongest change depicted in the episode, including a population decline.
    after = max(beats, key=lambda beat: (
        abs(beat.forage-before.forage) + abs(beat.population-before.population)/max(1, beat.population+before.population)
    ))
    kind = {'goats':'goat','deer':'deer','rabbits':'rabbit'}[species]
    overview = Island(SIZE,'aerial',after.forage,177,habitat,cover=True)
    cover = overview.base
    actors = []
    for x,y,_,scale,coat in overview.actors(after.population,seed=903,limit=240):
        px,py = overview.project(x,y,height(x,y))
        size = (.40 if kind == 'rabbit' else .50) * scale * (1+(py-480)/700)
        actors.append((py,px,size,coat))
    for py,px,scale,coat in sorted(actors):
        if kind == 'rabbit':
            pixels = max(12,round(scale*99))
            sprite = small_rabbit(coat,pixels)
        else:
            sprite = animal_sprite(coat,0,False,kind,scale)
        cover.paste(sprite,(round(px-sprite.width/2),round(py-sprite.height*.94)),sprite)

    near = Island(SIZE,'shore',before.forage,177,habitat,cover=True).base
    if before.population >= 2:
        paste_subject(near,kind,1,520,891,495,flip=True)
    if before.population:
        paste_subject(near,kind,0,252,942,565)
    save_thumbnail(compose_thumbnail(near,cover,label,cue),target)


def paste_subject(image, kind, coat, x, ground, size, *, flip=False):
    if kind == 'rabbit':
        sprite = rabbit_portrait(coat)
        sprite = sprite.resize((round(size*.76),size),Image.Resampling.LANCZOS)
    else:
        sprite = animal_sprite(coat,0,False,kind,size/97)
        sprite = sprite.crop(sprite.getbbox())
        sprite.thumbnail((430,size),Image.Resampling.LANCZOS)
    if flip:
        sprite = sprite.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    ImageDraw.Draw(image).ellipse((x-sprite.width*.46,ground-21,x+sprite.width*.47,ground+14),
                                  fill='#52623b')
    image.paste(sprite,(round(x-sprite.width/2),ground-sprite.height),sprite)


@lru_cache(maxsize=2)
def rabbit_portrait(coat):
    """Upright close-up with a distinct silhouette at phone size."""
    fur, light, shade, belly = (('#cbb293','#f5dfb4','#977450','#e5c9a1') if coat == 0
                                else ('#7d7167','#aa9c8a','#504745','#918277'))
    face = Image.new('RGBA',(240,315))
    draw = ImageDraw.Draw(face)
    for ear, inner in [
        ([(62,126),(33,62),(39,19),(53,4),(70,14),(88,54),(97,112)],
         [(63,100),(46,60),(48,27),(55,15),(68,31),(82,82)]),
        ([(126,103),(137,38),(161,4),(180,8),(187,34),(178,76),(158,121)],
         [(142,96),(149,46),(167,17),(175,20),(176,43),(165,75)]),
    ]:
        draw.polygon(ear,fill=light)
        draw.polygon(inner,fill='#d49a98' if coat == 0 else '#a77678')
    draw.ellipse((21,199,111,286),fill=shade)
    draw.ellipse((53,147,210,302),fill=shade)
    draw.ellipse((53,148,188,285),fill=fur)
    draw.ellipse((79,177,169,288),fill=belly)
    draw.ellipse((53,269,113,307),fill=light)
    draw.ellipse((138,268,210,305),fill=fur)
    draw.ellipse((43,86,198,213),fill=fur)
    draw.polygon([(45,151),(71,109),(131,91),(161,101),(177,128),(140,145),(88,161)],fill=light)
    draw.ellipse((93,150,173,194),fill=belly)
    draw.ellipse((53,134,75,157),fill='#231912')
    draw.ellipse((151,130,176,154),fill='#231912')
    draw.ellipse((59,137,66,144),fill='#fffbeb')
    draw.ellipse((155,133,162,141),fill='#fffbeb')
    draw.ellipse((110,154,133,168),fill='#a46864')
    draw.arc((97,159,122,180),0,99,fill=shade,width=2)
    draw.arc((121,159,145,180),79,173,fill=shade,width=2)
    pigments = {ImageColor.getrgb(color) for color in (fur,light,belly)}
    rng = Random(544)
    for _ in range(900):
        x,y = rng.randrange(26,210),rng.randrange(24,302)
        if face.getpixel((x,y))[:3] in pigments:
            pigment = face.getpixel((x,y))[:3]
            draw.line((x,y,x-1,y+2),fill=tuple(round(v*.90) for v in pigment),width=1)
    return face


@lru_cache(maxsize=128)
def small_rabbit(coat, height):
    return rabbit_portrait(coat).resize((round(height*.76),height),Image.Resampling.LANCZOS)


def compose_thumbnail(near,cover,label,cue,*,arrow_offset=(0,0)):
    width, frame_height = SIZE
    mask = Image.new('L',SIZE)
    seam = ((870,0),(685,frame_height))
    ImageDraw.Draw(mask).polygon([(0,0),*seam,(0,frame_height)],fill=255)
    cover.paste(near,(0,0),mask)
    ImageDraw.Draw(cover).line(seam,fill='#fff1d4',width=11)
    cover = ImageEnhance.Color(cover).enhance(1.32)
    cover = ImageEnhance.Contrast(cover).enhance(1.13)
    cover = ImageEnhance.Brightness(cover).enhance(1.10)
    draw_cue(cover,cue,arrow_offset=arrow_offset)
    draw_headline(cover, label)
    return cover


def draw_headline(cover, label):
    width = cover.width
    draw = ImageDraw.Draw(cover)
    label = label.upper()
    font = cover_font(200)
    box = draw.textbbox((0,0),label,font=font,stroke_width=15)
    ink_width, ink_height = box[2]-box[0], box[3]-box[1]
    lettering = Image.new('RGBA',(ink_width,ink_height))
    ImageDraw.Draw(lettering).text((-box[0],-box[1]),label,font=font,fill=CREAM,
                                  stroke_width=15,stroke_fill=INK)
    display_width = min(1780, round(ink_width*216/ink_height*1.12))
    lettering = lettering.resize((display_width,216),Image.Resampling.LANCZOS)
    cover.paste(lettering,((width-display_width)//2,20),lettering)


def render_science_thumbnail(beats, target, idea, cue):
    from .science_visuals import science_frame

    domain,topic = idea['domain'],idea['topic']
    if domain == 'ocean' and topic == 'tides':
        from .tidal_marsh import tidal_frame

        cover = tidal_frame(SIZE, .88, 'shore', portrait=True)
        draw_headline(cover, thumbnail_hook(idea))
        save_thumbnail(cover, target)
        return
    before = beats[0]
    after = max(beats,key=lambda beat:abs(beat.forage-before.forage))
    near = science_frame(SIZE,domain,topic,before.forage,'shore')
    cover = science_frame(SIZE,domain,topic,after.forage,'aerial')
    if domain == 'earth':
        # Frame the river and its former channel inside their respective panels.
        near = near.transform(SIZE,Image.Transform.AFFINE,(1,0,810,0,1,0))
        cover = cover.transform(SIZE,Image.Transform.AFFINE,(1,0,-245,0,1,0))
    offset = (0,196) if topic == 'rivers' else (0,0)
    cover = compose_thumbnail(near,cover,thumbnail_hook(idea),cue,arrow_offset=offset)
    save_thumbnail(cover,target)


def save_thumbnail(cover,target):
    for quality in (94,88,80):
        cover.save(target,quality=quality,optimize=True)
        if target.stat().st_size < THUMBNAIL_MAX_BYTES:
            return
    raise RuntimeError('Thumbnail is larger than 2 MiB')
