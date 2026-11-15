"""Draw a native 1920×1080 low-poly cover from the actual episode."""
from dataclasses import replace
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from .visuals import FONT, Island, animal_sprite, frames

SIZE = (1920,1080)
THUMBNAIL_MAX_BYTES = 2 * 1024**2


CUES = ('arrow', 'question', 'spotlight', 'trail')
AMBER = '#ffcf34'
ARROW_RED = '#f52d40'
INK = '#182027'


def episode_cue(episode):
    if episode.startswith('auto-'):
        return CUES[date.fromisoformat(episode.removeprefix('auto-')).toordinal() % len(CUES)]
    return 'arrow'


def draw_cue(image, cue):
    draw = ImageDraw.Draw(image)
    if cue == 'arrow':
        points = [(1772,244),(1792,300),(1649,371),(1674,410),
                  (1501,453),(1540,291),(1578,328)]
        draw.polygon(points,fill=ARROW_RED)
        draw.line([*points,points[0]],fill='#fff6e8',width=22,joint='curve')
        draw.line([*points,points[0]],fill='#43131d',width=8,joint='curve')
    elif cue == 'question':
        symbol = ImageFont.truetype(str(FONT),190)
        draw.text((1661,280),'?',anchor='mt',font=symbol,fill=AMBER,stroke_width=13,stroke_fill=INK)
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
                     habitat='grassland island', cue='arrow', varied_layout=False):
    width, frame_height = SIZE
    peak = max(beats,key=lambda beat:beat.population)
    overview = replace(peak,camera='aerial')
    cover = next(frames(SIZE,overview,1,1,species=species,habitat=habitat,overlay=False))
    near = Island(SIZE,'shore',beats[0].forage,177,habitat).base
    kind = {'goats':'goat','deer':'deer','rabbits':'rabbit'}[species]
    # Draw polygon silhouettes directly at their final close-up size.
    for coat, x, y, scale, flip in [(1,294,310,5.05,True),(0,30,350,5.35,False)]:
        sprite = animal_sprite(coat,0,False,kind,scale)
        if flip:
            sprite = sprite.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        ImageDraw.Draw(near).ellipse((x+100,y+sprite.height-54,x+sprite.width-45,y+sprite.height-20),
                                      fill='#53623a')
        near.paste(sprite,(x,y),sprite)
    mask = Image.new('L',SIZE)
    seam = ((955,0),(748,frame_height))
    cover_draw = ImageDraw.Draw(cover)
    if varied_layout and cue == 'question':
        inset = (35,285,820,950)
        ImageDraw.Draw(mask).ellipse(inset,fill=255)
        cover.paste(near,(0,0),mask)
        ImageDraw.Draw(cover).ellipse(inset,outline='#fff1d4',width=12)
    elif varied_layout and cue == 'spotlight':
        inset = (49,289,850,950)
        ImageDraw.Draw(mask).rounded_rectangle(inset,radius=70,fill=255)
        cover.paste(near,(0,0),mask)
        ImageDraw.Draw(cover).rounded_rectangle(inset,radius=70,outline='#fff1d4',width=10)
    elif varied_layout and cue == 'trail':
        cover_draw.rectangle((0,0,806,1080),fill='#10426a')
        cover.paste(near.crop((0,235,810,1080)),(0,235))
        ImageDraw.Draw(cover).line(((810,235),(810,1080)),fill='#fff1d4',width=10)
    else:
        ImageDraw.Draw(mask).polygon([(0,0),*seam,(0,frame_height)],fill=255)
        cover.paste(near,(0,0),mask)
        ImageDraw.Draw(cover).line(seam,fill='#fff1d4',width=11)
    cover = ImageEnhance.Color(cover).enhance(1.32)
    cover = ImageEnhance.Contrast(cover).enhance(1.13)
    cover = ImageEnhance.Brightness(cover).enhance(1.10)
    gradient = Image.new('L',(1,236))
    gradient.putdata([round(205 * (1-y/236)**.8) for y in range(236)])
    cover.paste('#132b3f',(0,0,width,236),gradient.resize((width,236)))
    draw_cue(cover,cue)
    draw = ImageDraw.Draw(cover)
    label = label.upper()
    for font_size in range(186,54,-2):
        font = ImageFont.truetype(str(FONT),font_size)
        if draw.textlength(label,font=font) <= 1730:
            break
    draw.text((width//2,46),label,font=font,anchor='mt',fill='#fff5d9',
              stroke_width=11,stroke_fill=INK)
    badge = ImageFont.truetype(str(FONT),57)
    opening_count = f'{beats[0].population:,} {species.upper()}'
    outcome = f'{peak.population:,} {species.upper()}'
    if cue in ('question','trail'):
        outcome = 'HOW MANY?'
    for text, x, anchor in [(opening_count,48,'lt'),(outcome,width-48,'rt')]:
        box = draw.textbbox((x,972),text,font=badge,anchor=anchor)
        draw.rounded_rectangle((box[0]-16,box[1]-11,box[2]+16,box[3]+11),radius=16,
                               fill='#163337',outline='#eee6bd',width=3)
        draw.text((x,972),text,font=badge,anchor=anchor,fill='#fff1ce')
    save_thumbnail(cover,target)


def render_science_thumbnail(beats, target, idea, cue):
    from .science_visuals import science_frame

    domain,topic = idea['domain'],idea['topic']
    index = max(range(len(beats)),key=lambda i:abs(beats[i].forage-beats[0].forage))
    frame = science_frame(SIZE,domain,topic,beats[index].forage,beats[index].camera)
    cover = ImageEnhance.Color(frame).enhance(1.31)
    cover = ImageEnhance.Contrast(cover).enhance(1.12)
    cover = ImageEnhance.Brightness(cover).enhance(1.08)
    draw = ImageDraw.Draw(cover)
    label = idea['thumbnail_text'].upper()
    # Leave the featured object visible and vary where the headline sits.
    band, anchor, position = {
        'space': ((0,0,1920,236),'lt',(80,38)),
        'ocean': ((0,841,1920,1080),'mt',(960,889)),
        'earth': ((0,0,1920,242),'mt',(960,40)),
        'technology': ((0,0,1920,230),'rt',(1810,40)),
    }[domain]
    draw.rectangle(band, fill={'space':'#152242','ocean':'#0c4361',
                              'earth':'#244752','technology':'#2d2244'}[domain])
    for font_size in range(158,54,-2):
        font = ImageFont.truetype(str(FONT),font_size)
        if draw.textlength(label,font=font) <= 1710:
            break
    draw.text(position,label,font=font,anchor=anchor,fill='#fff6e1',stroke_width=9,stroke_fill=INK)
    draw_cue(cover,cue)
    save_thumbnail(cover,target)


def save_thumbnail(cover,target):
    for quality in (94,88,80):
        cover.save(target,quality=quality,optimize=True)
        if target.stat().st_size < THUMBNAIL_MAX_BYTES:
            return
    raise RuntimeError('Thumbnail is larger than 2 MiB')
