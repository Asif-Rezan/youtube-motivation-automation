"""Render Blender storybook shots through a separate headless process."""
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from PIL import Image, ImageDraw, ImageOps

from .thumbnail import SIZE, cover_font, draw_headline, save_thumbnail

MARSH_SCRIPT = Path(__file__).with_name('blender_marsh.py')


def render_marsh(output, **shot):
    output.mkdir(parents=True, exist_ok=True)
    settings = json.dumps(dict(shot, output=str(output.resolve())))
    subprocess.run(
        [os.environ['WILDLIFE_BLENDER'], '-b', '-t', '4', '--python-exit-code', '1',
         '--python', str(MARSH_SCRIPT)],
        env=dict(os.environ, WILDLIFE_BLENDER_SHOT=settings), check=True,
        stdout=subprocess.DEVNULL, timeout=1200,
    )


def render_marsh_thumbnail(beats, target, headline):
    with TemporaryDirectory(prefix='wildlife-cover-') as directory:
        plates = []
        for kind, level in (('close', min(b.forage for b in beats)), ('wide', max(b.forage for b in beats))):
            panel = Path(directory)/kind
            render_marsh(panel, thumbnail=kind, start=level, end=level, frames=42)
            with Image.open(panel/'plate.png') as image:
                plates.append(ImageOps.fit(image.convert('RGB'), (1095, SIZE[1])))
    cover = Image.new('RGB', SIZE)
    cover.paste(plates[1], (825,0))
    foreground = Image.new('RGB', SIZE)
    foreground.paste(plates[0], (0,0))
    split = ((930,0),(825,1080))
    mask = Image.new('L', SIZE)
    ImageDraw.Draw(mask).polygon([(0,0),*split,(0,1080)], fill=255)
    cover.paste(foreground, mask=mask)
    draw = ImageDraw.Draw(cover)
    draw.line(split, fill='#fff7df', width=7)
    draw.text((1360,590),'?',font=cover_font(345),anchor='mm',fill='#fff5dc',
              stroke_width=15,stroke_fill='#342216')
    draw_headline(cover, headline)
    save_thumbnail(cover, target)
