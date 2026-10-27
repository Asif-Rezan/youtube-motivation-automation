"""Render a public sample topic through production CPU image and thumbnail helpers."""
import argparse
import hashlib
import json
import os
from pathlib import Path

from PIL import Image, ImageOps
from image_cpu import metadata_path, image_config
from long_video import render_safe_scene, render_safe_thumbnail
from thumbnail_style import add_caption
from human_history import visual_prompt, image_negative
import workflow

TITLE = 'What Ancient Humans Did When Their Fire Went Out'
SAMPLES = {
    'background-01': {
        'seed': 1700,
        'prompt': 'Cold gray hearth ashes beside flint tools and dry kindling at an empty limestone rock shelter, pale dawn light.',
    },
    'background-02': {
        'seed': 1701,
        'prompt': 'A glowing red ember rests in dry tinder beside split firewood on rough stone inside a prehistoric shelter.',
    },
    'thumbnail': {
        'seed': 9931,
        'prompt': 'A worried prehistoric adult in hide clothing cups one glowing coal in dry grass near their face inside a cave.',
    },
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--asset', choices=SAMPLES, required=True)
    parser.add_argument('--output', type=Path, default=Path('preview-human-history'))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    sample = SAMPLES[args.asset]
    config = image_config()
    os.environ['IMAGE_SEED'] = str(sample['seed'])
    people = args.asset == 'thumbnail'
    prompt = visual_prompt(sample['prompt'], people=people, thumbnail=args.asset == 'thumbnail')
    os.environ['IMAGE_NEGATIVE_PROMPT'] = image_negative(sample['prompt'], people=people)
    path = args.output / f'{args.asset}.png'
    if args.asset == 'thumbnail':
        source = args.output / 'thumbnail-source.png'
        render_safe_thumbnail(prompt, source)
        with Image.open(source) as original:
            picture = ImageOps.fit(original.convert('RGB'), (1280, 720))
        add_caption(picture, 'LAST EMBER', placement='upper-left')
        picture.save(path)
        picture.save(args.output / 'thumbnail.jpg', quality=92)
        metadata = json.loads(metadata_path(source).read_text())
        expected = (1280, 720)
    else:
        render_safe_scene({'index': args.asset, 'seed': sample['seed'],
            'prompt': prompt, 'visual_action': sample['prompt']}, path, metadata_path(path))
        metadata = json.loads(metadata_path(path).read_text())
        expected = (config.width, config.height)
    with Image.open(path) as picture:
        if picture.size != expected or picture.convert('L').getextrema()[0] == picture.convert('L').getextrema()[1]:
            raise RuntimeError('Preview dimensions or nonblank validation failed')
        picture.resize((384, 216)).save(args.output / f'{args.asset}-mobile.jpg')
    if metadata['model'] != config.model or metadata['steps'] != config.steps or metadata['reference_mode'] != 'none':
        raise RuntimeError('Preview differs from selected model/style settings')
    report = {'title': TITLE, 'asset': args.asset, 'prompt': prompt,
        'style': workflow.VISUAL_STYLE, 'caption': 'LAST EMBER' if args.asset == 'thumbnail' else None,
        'production_image_metadata': metadata,
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    (args.output / f'{args.asset}-review.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({'asset': args.asset, 'validated': True, 'path': str(path)}), flush=True)


if __name__ == '__main__':
    main()
