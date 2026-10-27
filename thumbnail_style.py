"""Readable thumbnail typography added after image generation, never drawn by diffusion."""
from pathlib import Path
from PIL import ImageDraw, ImageFont


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
        words = text.split()
        split = min(range(1, len(words)), key=lambda i: max(len(' '.join(words[:i])), len(' '.join(words[i:]))))
        lines = [' '.join(words[:split]), ' '.join(words[split:])]
        maximum_width = image.width*.33
        fonts, boxes = [], []
        for line, maximum in zip(lines, (76, 104)):
            for size in range(maximum, 29, -2):
                font = ImageFont.truetype(font_path, size)
                box = draw.textbbox((0, 0), line, font=font, stroke_width=2)
                if box[2]-box[0] <= maximum_width:
                    break
            else:
                raise ValueError('Thumbnail caption does not fit left column')
            fonts.append(font)
            boxes.append(box)
        gap = 12
        height = sum(box[3]-box[1] for box in boxes)+gap
        y = image.height*.48-height/2
        for line, font, box, color in zip(lines, fonts, boxes, ('#FFFFFF', '#FFD45A')):
            draw.text((54-box[0], y-box[1]), line, font=font, fill=color,
                      stroke_width=2, stroke_fill='#17120D')
            y += box[3]-box[1]+gap
        return image
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
