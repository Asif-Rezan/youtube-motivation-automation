"""Render a public sample topic through production CPU image and thumbnail helpers."""
import argparse
import hashlib
import json
import os
from pathlib import Path

from PIL import Image, ImageOps
from image_cpu import metadata_path
from long_video import render_safe_scene, render_safe_thumbnail
from thumbnail_style import add_caption
import workflow

TITLE = 'What Ancient Humans Did When Their Fire Went Out'
CHARACTER = 'Ari, cream oval head, dot eyes, black line limbs, short curly dark hair, ochre tunic, blue wrist tie'
SAMPLES = {
    'background-01': {
        'seed': 1700,
        'prompt': 'Ari kneels worried beside cold hearth ashes outside a rock shelter, dry twigs nearby, grassy prehistoric camp at dawn.',
    },
    'background-02': {
        'seed': 1701,
        'prompt': 'Ari crouches blowing gently on a glowing ember inside dry grass, kindling nearby, sheltered prehistoric woodland camp in daylight.',
    },
    'thumbnail': {
        'seed': 9931,
        'prompt': 'Worried Ari beside a large cold stone hearth, tiny red ember, dark rock shelter and blue evening sky; clear silhouettes, top quarter empty.',
    },
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--asset', choices=SAMPLES, required=True)
    parser.add_argument('--output', type=Path, default=Path('preview-human-history'))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    sample = SAMPLES[args.asset]
    os.environ['IMAGE_SEED'] = str(sample['seed'])
    prompt = sample['prompt'] + '. Character: ' + CHARACTER
    path = args.output / f'{args.asset}.png'
    if args.asset == 'thumbnail':
        source = args.output / 'thumbnail-source.png'
        render_safe_thumbnail(prompt, source)
        with Image.open(source) as original:
            picture = ImageOps.fit(original.convert('RGB'), (1280, 720))
        add_caption(picture, 'FIRE GONE?')
        picture.save(path)
        picture.save(args.output / 'thumbnail.jpg', quality=92)
        metadata = json.loads(metadata_path(source).read_text())
        expected = (1280, 720)
    else:
        render_safe_scene({'index': args.asset, 'seed': sample['seed'],
            'prompt': prompt, 'visual_action': sample['prompt']}, path, metadata_path(path))
        metadata = json.loads(metadata_path(path).read_text())
        expected = (1024, 576)
    with Image.open(path) as picture:
        if picture.size != expected or picture.convert('L').getextrema()[0] == picture.convert('L').getextrema()[1]:
            raise RuntimeError('Preview dimensions or nonblank validation failed')
        picture.resize((384, 216)).save(args.output / f'{args.asset}-mobile.jpg')
    if metadata['model'] != 'segmind/SSD-1B' or metadata['steps'] != 16 or metadata['reference_mode'] != 'none':
        raise RuntimeError('Preview differs from production model/style settings')
    report = {'title': TITLE, 'asset': args.asset, 'prompt': prompt,
        'style': workflow.VISUAL_STYLE, 'caption': 'FIRE GONE?' if args.asset == 'thumbnail' else None,
        'production_image_metadata': metadata,
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    (args.output / f'{args.asset}-review.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({'asset': args.asset, 'validated': True, 'path': str(path)}), flush=True)


if __name__ == '__main__':
    main()
