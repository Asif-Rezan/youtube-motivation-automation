"""Readable thumbnail typography added after image generation, never drawn by diffusion."""
from pathlib import Path
from PIL import ImageDraw, ImageFont


def add_caption(image, text):
    text = ' '.join(text.upper().split())
    if not 2 <= len(text.split()) <= 5 or len(text) > 45:
        raise ValueError('Thumbnail caption must have 2–5 words and at most 45 characters')
    candidates = ('/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf',
                  '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
                  '/System/Library/Fonts/Supplemental/Arial Bold.ttf')
    font_path = next((p for p in candidates if Path(p).is_file()), 'DejaVuSans-Bold.ttf')
    draw = ImageDraw.Draw(image)
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
