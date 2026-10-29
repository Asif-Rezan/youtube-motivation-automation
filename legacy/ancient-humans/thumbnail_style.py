"""Readable thumbnail typography added after image generation, never drawn by diffusion."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def add_caption(image, text, placement='top'):
    text = ' '.join(text.upper().split())
    if not 2 <= len(text.split()) <= 5 or len(text) > 45:
        raise ValueError('Thumbnail caption must have 2–5 words and at most 45 characters')
    candidates = ('/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf',
                  '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
                  '/System/Library/Fonts/Supplemental/Arial Bold.ttf')
    font_path = next((p for p in candidates if Path(p).is_file()), 'DejaVuSans-Bold.ttf')
    draw = ImageDraw.Draw(image)
    if placement == 'left-center':
        return stylish_caption(image, text)
    if placement == 'upper-left':
        words = text.split()
        # Two compact lines stay inside the negative space requested from the model.
        split = min(range(1, len(words)), key=lambda i: max(len(' '.join(words[:i])), len(' '.join(words[i:]))))
        lines = [' '.join(words[:split]), ' '.join(words[split:])]
        for size in range(118, 31, -2):
            font = ImageFont.truetype(font_path, size)
            boxes = [draw.textbbox((0, 0), line, font=font, stroke_width=6) for line in lines]
            if max(box[2]-box[0] for box in boxes) <= image.width*.42:
                break
        else:
            raise ValueError('Thumbnail caption does not fit reserved area')
        y = 38
        for line, box in zip(lines, boxes):
            draw.text((42-box[0], y-box[1]), line, font=font, fill='#FFF244', stroke_width=6, stroke_fill='black')
            y += box[3]-box[1]+12
        return image
    if placement != 'top':
        raise ValueError('Unknown thumbnail caption placement')
    for size in range(108, 31, -2):
        font = ImageFont.truetype(font_path, size)
        box = draw.textbbox((0, 0), text, font=font, stroke_width=5)
        if box[2]-box[0] <= image.width-80:
            break
    else:
        raise ValueError('Thumbnail caption does not fit')
    x = (image.width-(box[2]-box[0]))/2-box[0]
    draw.text((x, 28-box[1]), text, font=font, fill='#FFF244', stroke_width=5, stroke_fill='black')
    return image


def stylish_caption(image, text):
    """Italic poster lettering on a transparent layer; never dim the underlying art."""
    candidates = ('/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-BoldOblique.ttf',
                  '/System/Library/Fonts/Supplemental/Arial Narrow Bold Italic.ttf')
    font_path = next((p for p in candidates if Path(p).is_file()), 'DejaVuSans-BoldOblique.ttf')
    words = text.split()
    split = min(range(1, len(words)), key=lambda i: max(len(' '.join(words[:i])), len(' '.join(words[i:]))))
    lines = [' '.join(words[:split]), ' '.join(words[split:])]
    width = int(image.width*.34)
    probe = ImageDraw.Draw(Image.new('L', (1, 1)))
    fonts, boxes = [], []
    for line, maximum in zip(lines, (100, 138)):
        for size in range(maximum, 29, -2):
            font = ImageFont.truetype(font_path, size)
            box = probe.textbbox((0, 0), line, font=font, stroke_width=3)
            if box[2]-box[0] <= width:
                break
        else:
            raise ValueError('Caption does not fit')
        fonts.append(font)
        boxes.append(box)
    height = sum(b[3]-b[1] for b in boxes)+48
    layer = Image.new('RGBA', (width+32, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    y = 12
    for index, (line, font, box) in enumerate(zip(lines, fonts, boxes)):
        xy = (10-box[0], y-box[1])
        # A small dimensional edge and crisp contour belong to the lettering only.
        draw.text((xy[0]+3, xy[1]+4), line, font=font, fill='#3A210E', stroke_width=4, stroke_fill='#160E08')
        draw.text(xy, line, font=font, fill='white', stroke_width=3, stroke_fill='#21170F')
        if index == 1:
            mask = Image.new('L', layer.size, 0)
            ImageDraw.Draw(mask).text(xy, line, font=font, fill=255)
            gold = Image.new('RGBA', layer.size)
            palette = ImageDraw.Draw(gold)
            line_height = max(1, box[3]-box[1])
            for row in range(layer.height):
                t = max(0, min(1, (row-y)/line_height))
                color = tuple(round(a+(b-a)*t) for a,b in zip((255,244,188),(231,161,43)))+(255,)
                palette.line((0,row,layer.width,row), fill=color)
            layer.paste(gold, (0,0), mask)
        y += box[3]-box[1]+8
    draw.polygon([(12,y+2),(width-8,y-5),(width-18,y+2),(12,y+7)], fill='#F6BF48')
    layer = layer.rotate(3, resample=Image.Resampling.BICUBIC, expand=True)
    image.paste(layer, (40, int(image.height*.48-layer.height/2)), layer)
    return image
