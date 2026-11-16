"""Select and render short editorial cues from the episode's own narration and state."""
from functools import lru_cache
import re

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from .visuals import FONT


TIME_CARD = re.compile(
    r'\b(?:day|week|month|year) (?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b'
    r'|\b(?:first|second|third) (?:dry season|rainy season|winter|summer)\b'
    r'|\b(?:in (?:the )?)?(?:17|18|19|20)\d{2}\b|^today\b', re.I
)


def scene_edit(beats, index, seconds, *, science=False):
    beat = beats[index]
    if len(beats) < 4:
        return {}
    if index == len(beats) - 1:
        return {'compare_to': 0, 'at': round(seconds * .62, 2), 'duration': 4}
    if index == len(beats) * 3 // 4:
        earlier = max(0, index - 4)
        if abs(beat.forage - beats[earlier].forage) >= .15 or beat.population != beats[earlier].population:
            return {'compare_to': earlier, 'at': round(seconds * .48, 2), 'duration': 4}
    previous = beats[max(0, index - 1)]
    intro = ' '.join(beat.narration.split()[:22])
    time = TIME_CARD.search(intro)
    if time and time.group().casefold() not in previous.narration.casefold() and (science or index % 2):
        return {'text': time.group().upper(), 'at': 3, 'duration': 2.8}
    if science or index == len(beats) // 2 or (
        index % 3 == 1 and abs(beat.forage - previous.forage) >= .15
    ):
        label = ' '.join(beat.label.split()[:4]).upper()
        return {'text': label, 'at': round(seconds * .36, 2), 'duration': 2.8}
    return {}


def documentary_overlay(beats, index, seconds, *, science, subject, topic):
    beat = beats[index]
    edit = scene_edit(beats, index, seconds, science=science)
    time = None
    for earlier in reversed(beats[:index+1]):
        marker = TIME_CARD.search(' '.join(earlier.narration.split()[:22]))
        if marker:
            time = re.sub(r'^in (?:the )?', '', marker.group(), flags=re.I).title()
            break
    chapter_width = max(1, (len(beats)+3)//4)
    chapter = index//chapter_width + 1
    result = dict(edit)
    result['chapter'] = (chapter, beat.label) if index % chapter_width == 0 else None
    result['time'] = time or ('At the start' if index == 0 else None)
    if not science:
        result['counter'] = (beat.population, subject)
    if 'compare_to' in result:
        before = beats[result['compare_to']]
        if not science:
            result['comparison_values'] = (f'{before.population:,} {subject.lower()}',
                                           f'{beat.population:,} {subject.lower()}')
        elif topic == 'tides':
            result['comparison_values'] = (tide_label(before.forage), tide_label(beat.forage))
    if index == 1:
        if not science:
            question = ('How will the population change?', ('Fewer', 'About the same', 'More'))
        elif topic == 'tides':
            question = ('Where will the birds feed?', ('On the same flats', 'Farther inland', 'Elsewhere'))
        else:
            question = ('How much will the habitat change?', ('Very little', 'Somewhat', 'Dramatically'))
        result['quiz'] = question
        result['quiz_at'] = min(6, seconds*.2)
    return result


def tide_label(level):
    return 'High tide' if level >= .7 else 'Mid tide' if level >= .35 else 'Low tide'


def zoom_frame(frame, progress):
    width, height = frame.size
    # Three deliberately different shot sizes within a narrated scene.
    crop = .11 if .39 <= progress < .70 else .045 if progress >= .70 else 0
    if not crop:
        return frame
    dx, dy = round(width * crop), round(height * crop)
    return frame.resize(frame.size, Image.Resampling.BILINEAR,
                        box=(dx, dy, width-dx, height-dy))


@lru_cache(maxsize=16)
def overlay_font(size, bold=False):
    font = ImageFont.truetype(str(FONT), size)
    if bold:
        font.set_variation_by_axes([700])
    return font


def paint_tide_indicator(frame, level):
    """Show the scenario's water level without presenting it as a measurement."""
    width, height = frame.size
    scale = width / 1920
    draw = ImageDraw.Draw(frame)
    right = round(width * .965)
    top = round(height * .055)
    left, bottom = right - round(278 * scale), top + round(86 * scale)
    draw.rounded_rectangle((left,top,right,bottom), radius=round(16*scale),
                           fill='#173137',outline='#a4d7d1',width=max(1,round(2*scale)))
    font = overlay_font(max(10,round(30*scale)))
    label = tide_label(level).upper()
    draw.text(((left+right)//2,top+round(29*scale)),label,
              font=font,anchor='mm',fill='#fff6df')
    x0, x1 = left + round(22*scale), right - round(22*scale)
    y0, y1 = top + round(57*scale), bottom - round(13*scale)
    draw.rectangle((x0,y0,x1,y1), fill='#36575e')
    draw.rectangle((x0,y0,round(x0 + (x1-x0)*level),y1),fill='#96ded9')


def paint_cue(frame, edit, seconds, before=None):
    if not edit:
        return
    width, height = frame.size
    scale = width / 1920
    active = 'at' in edit and edit['at'] <= seconds < edit['at'] + edit['duration']
    quiz_elapsed = seconds - edit.get('quiz_at', 0)
    in_quiz = 'quiz' in edit and 0 <= quiz_elapsed < 4.5

    def card(draw, text, x, y, *, small=False):
        font = overlay_font(max(12, round(scale * (34 if small else 62))), bold=True)
        pad = max(6, round(16 * scale))
        x0, y0, x1, y1 = draw.textbbox((x, y), text, font=font, anchor='mm')
        draw.rounded_rectangle((x0-pad,y0-pad,x1+pad,y1+pad),radius=pad,
                               fill='#173137',outline='#ffd46b',width=max(1,round(3*scale)))
        draw.text((x,y),text,fill='#fff6df',font=font,anchor='mm')

    if in_quiz:
        background = frame.resize((480,270), Image.Resampling.BILINEAR).filter(ImageFilter.GaussianBlur(3))
        background = ImageEnhance.Brightness(background.resize(frame.size, Image.Resampling.BILINEAR)).enhance(.66)
        frame.paste(background)
        quiz_draw = ImageDraw.Draw(frame)
        question, choices = edit['quiz']
        card(quiz_draw, question, width//2, round(height*.38))
        for index, choice in enumerate(choices):
            if quiz_elapsed >= index*.35:
                card(quiz_draw, choice, round(width*(.23+index*.27)), round(height*.55),small=True)
    elif active and before is not None:
        crop = (width//4, 0, width*3//4, height)
        after = frame.crop(crop)
        frame.paste(before.crop(crop), (0, 0))
        frame.paste(after, (width//2, 0))
        draw = ImageDraw.Draw(frame)
        draw.line((width//2,0,width//2,height),fill='#fff6df',width=max(2,round(5*scale)))
        card(draw,'AT THE START' if edit['compare_to'] == 0 else 'EARLIER',width//4,round(height*.81),small=True)
        card(draw,'NOW',width*3//4,round(height*.81),small=True)
        if 'comparison_values' in edit:
            for index, value in enumerate(edit['comparison_values']):
                card(draw, value, width*(2*index+1)//4, round(height*.88),small=True)
    elif active and edit.get('text'):
        card(ImageDraw.Draw(frame),edit['text'],width//2,round(height*.79))

    draw = ImageDraw.Draw(frame)
    margin = round(56 * scale)
    def hud(text, x, y, size, anchor='lt', fill='#fff5d9'):
        font = overlay_font(max(10,round(size*scale)),bold=True)
        draw.text((x,round(y*scale)),text,anchor=anchor,font=font,fill=fill,
                  stroke_width=max(1,round(2.2*scale)),stroke_fill='#203238')

    if edit.get('time'):
        center = (margin+round(26*scale), round(63*scale))
        r = round(24*scale)
        cx,cy = center
        draw.ellipse((cx-r,cy-r,cx+r,cy+r),fill='#233c43',outline='#ffcf62',
                     width=max(1,round(4*scale)))
        draw.line((cx,cy,cx+r*.48,cy-r*.45),fill='#fff5d9',width=max(1,round(3*scale)))
        hud(edit['time'],margin+round(65*scale),42,48)

    if edit.get('chapter') and seconds < 4.5:
        number, title = edit['chapter']
        hud(f'CHAPTER {number}',margin,137,27,fill='#ffe199')
        hud(title,margin,176,53)

    if edit.get('counter'):
        number, subject = edit['counter']
        hud(f'{number:,}',width-margin,42,62,anchor='rt')
        hud(f'Simulated {subject.lower()}',width-margin,112,24,anchor='rt')
