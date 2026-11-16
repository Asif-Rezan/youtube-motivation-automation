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
        result['previous_population'] = beats[max(0,index-1)].population
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


def smoothstep(value):
    value = max(0, min(1, value))
    return value * value * (3 - 2 * value)


def visibility(elapsed, duration):
    return min(smoothstep(elapsed/.32), smoothstep((duration-elapsed)/.25))


def paint_cue(frame, edit, seconds, before=None):
    if not edit:
        return
    width, height = frame.size
    scale = width / 1920
    elapsed = seconds - edit.get('at', 0)
    active = 'at' in edit and 0 <= elapsed < edit['duration']
    quiz_elapsed = seconds - edit.get('quiz_at', 0)
    in_quiz = 'quiz' in edit and 0 <= quiz_elapsed < 4.5

    def px(value):
        return round(value*scale)

    def card(text, x, y, *, opacity=1, box_width=0, compact=False, accent=None):
        if opacity <= 0:
            return
        font_size = 42 if compact else 62
        font = overlay_font(max(10,px(font_size)),bold=True)
        measure = ImageDraw.Draw(frame)
        limit = box_width or px(1550)
        while measure.textlength(text,font=font) > limit - px(54) and font_size > 22:
            font_size -= 2
            font = overlay_font(max(10,px(font_size)),bold=True)
        w = max(box_width,round(measure.textlength(text,font=font))+px(56))
        h = px(82 if compact else 108)
        gutter = px(16)
        layer = Image.new('RGBA',(w+gutter*2,h+gutter*2))
        ink = ImageDraw.Draw(layer)
        left, top, right, bottom = gutter,gutter,gutter+w,gutter+h
        ink.rounded_rectangle((left,top+px(7),right,bottom+px(7)),radius=px(22),fill=(0,15,20,95))
        ink.rounded_rectangle((left,top,right,bottom),radius=px(22),fill=(12,36,43,237),
                              outline='#6a9697',width=max(1,px(2)))
        if accent:
            ink.rounded_rectangle((left+px(12),top+px(20),left+px(17),bottom-px(20)),
                                  radius=max(1,px(3)),fill=accent)
        ink.text((layer.width//2,gutter+h//2),text,fill='#fff4d9',font=font,anchor='mm')
        if opacity < 1:
            layer.putalpha(layer.getchannel('A').point(lambda alpha: round(alpha*opacity)))
        lift = px(16*(1-opacity))
        frame.paste(layer,(round(x-layer.width/2),round(y-layer.height/2)+lift),layer)

    if in_quiz:
        strength = visibility(quiz_elapsed, 4.5)
        background = frame.resize((480,270), Image.Resampling.BILINEAR).filter(ImageFilter.GaussianBlur(4))
        background = ImageEnhance.Brightness(background.resize(frame.size, Image.Resampling.BILINEAR)).enhance(.57)
        frame.paste(Image.blend(frame,background,strength) if strength < 1 else background)
        question, choices = edit['quiz']
        card(question,width//2,height*.37,opacity=strength,accent='#ffd46b')
        for index, choice in enumerate(choices):
            reveal = smoothstep((quiz_elapsed-index*.26-.22)/.35)
            card(f'{chr(65+index)}   {choice}',width*(.224+index*.276),height*.56,
                 box_width=px(460),compact=True,opacity=strength*reveal)
        return

    if active and before is not None:
        opacity = visibility(elapsed,edit['duration'])
        original = frame.copy() if opacity < 1 else None
        crop = (width//4,0,width*3//4,height)
        after = frame.crop(crop)
        frame.paste(before.crop(crop),(0,0))
        frame.paste(after,(width//2,0))
        ImageDraw.Draw(frame).line((width//2,0,width//2,height),fill='#fff4d9',width=max(2,px(5)))
        card('AT THE START' if edit['compare_to'] == 0 else 'EARLIER',width//4,height*.77,
             compact=True,accent='#7cd6ca')
        card('NOW',width*3//4,height*.77,compact=True,accent='#ffd46b')
        for index, value in enumerate(edit.get('comparison_values',())):
            card(value,width*(2*index+1)//4,height*.88,compact=True)
        if original is not None:
            frame.paste(Image.blend(original,frame,opacity))
        return

    if active and edit.get('text'):
        card(edit['text'],width//2,height*.79,opacity=visibility(elapsed,edit['duration']),accent='#ffd46b')

    draw = ImageDraw.Draw(frame)
    margin = px(56)

    def hud(text, x, y, size, anchor='lt', fill='#fff5d9'):
        font = overlay_font(max(10,px(size)),bold=True)
        draw.text((x,px(y)),text,anchor=anchor,font=font,fill=fill,
                  stroke_width=max(1,px(2.2)),stroke_fill='#203238')

    if edit.get('time'):
        cx, cy, radius = margin+px(26), px(63), px(24)
        draw.ellipse((cx-radius,cy-radius,cx+radius,cy+radius),fill='#233c43',outline='#ffcf62',
                     width=max(1,px(4)))
        draw.line((cx,cy,cx+radius*.48,cy-radius*.45),fill='#fff5d9',width=max(1,px(3)))
        hud(edit['time'],margin+px(65),42,48)

    if edit.get('chapter') and seconds < 4.5:
        number, title = edit['chapter']
        opacity = visibility(seconds,4.5)
        slide = px(22*(1-opacity))
        title_size = 52
        font = overlay_font(max(10,px(title_size)),bold=True)
        while draw.textlength(title,font=font) > px(1205) and title_size > 28:
            title_size -= 2
            font = overlay_font(max(10,px(title_size)),bold=True)
        box_width = min(px(1280),max(px(360),round(draw.textlength(title,font=font))+px(75)))
        layer = Image.new('RGBA',(box_width,px(130)))
        layer_draw = ImageDraw.Draw(layer)
        layer_draw.rounded_rectangle((0,0,box_width-1,layer.height-1),radius=px(23),fill=(12,36,43,220))
        layer_draw.text((px(26),px(15)),f'CHAPTER {number}',fill='#ffda7b',
                        font=overlay_font(max(10,px(24)),bold=True))
        layer_draw.text((px(26),px(47)),title,fill='#fff5d9',font=font)
        layer.putalpha(layer.getchannel('A').point(lambda alpha: round(alpha*opacity)))
        frame.paste(layer,(margin-slide,px(128)),layer)

    if edit.get('counter'):
        number, subject = edit['counter']
        previous = edit.get('previous_population',number)
        shown = round(previous+(number-previous)*smoothstep(seconds/.65))
        hud(f'{shown:,}',width-margin,42,62,anchor='rt')
        hud(f'Simulated {subject.lower()}',width-margin,112,24,anchor='rt')
