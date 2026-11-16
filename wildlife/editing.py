"""Select and render short editorial cues from the episode's own narration and state."""
from functools import lru_cache
import re

from PIL import Image, ImageDraw, ImageFont

from .visuals import FONT


TIME_CARD = re.compile(
    r'\b(?:day|week|month|year) (?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b'
    r'|\b(?:first|second|third) (?:dry season|rainy season|winter|summer)\b', re.I
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
    label = 'HIGH TIDE' if level >= .7 else 'MID TIDE' if level >= .35 else 'LOW TIDE'
    draw.text(((left+right)//2,top+round(29*scale)),label,
              font=font,anchor='mm',fill='#fff6df')
    x0, x1 = left + round(22*scale), right - round(22*scale)
    y0, y1 = top + round(57*scale), bottom - round(13*scale)
    draw.rectangle((x0,y0,x1,y1), fill='#36575e')
    draw.rectangle((x0,y0,round(x0 + (x1-x0)*level),y1),fill='#96ded9')


def paint_cue(frame, edit, seconds, before=None):
    if not edit or not edit['at'] <= seconds < edit['at'] + edit['duration']:
        return
    width, height = frame.size
    scale = width / 1920

    def card(draw, text, x, y, *, small=False):
        font = overlay_font(max(12, round(scale * (34 if small else 62))), bold=True)
        pad = max(6, round(16 * scale))
        x0, y0, x1, y1 = draw.textbbox((x, y), text, font=font, anchor='mm')
        draw.rounded_rectangle((x0-pad,y0-pad,x1+pad,y1+pad),radius=pad,
                               fill='#173137',outline='#ffd46b',width=max(1,round(3*scale)))
        draw.text((x,y),text,fill='#fff6df',font=font,anchor='mm')

    if before is not None:
        crop = (width//4, 0, width*3//4, height)
        after = frame.crop(crop)
        frame.paste(before.crop(crop), (0, 0))
        frame.paste(after, (width//2, 0))
        draw = ImageDraw.Draw(frame)
        draw.line((width//2,0,width//2,height),fill='#fff6df',width=max(2,round(5*scale)))
        card(draw,'AT THE START' if edit['compare_to'] == 0 else 'EARLIER',width//4,round(height*.81),small=True)
        card(draw,'NOW',width*3//4,round(height*.81),small=True)
    elif edit.get('text'):
        card(ImageDraw.Draw(frame),edit['text'],width//2,round(height*.79))
