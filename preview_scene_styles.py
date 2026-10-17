"""Render public, contrasting narration samples through the production image path."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from PIL import Image
import image_cpu
import workflow

SCENES = {
    'office': {'narration': 'Elias left the office as his manager watched from the doorway.',
               'prompt': 'Elias, a young man with short dark hair and a teal jacket, leaves the office carrying a shoulder bag; his manager watches from the doorway.',
               'seed': 1700},
    'budget': {'narration': 'At home, he counted his remaining coins beside the household bills.',
               'prompt': 'Close-up of hands counting coins beside household bills on a modest kitchen table, overhead view, no faces, no office.',
               'seed': 1701},
    'repair': {'narration': 'The next morning, Elias repaired a bicycle outside a small garage.',
               'prompt': 'Elias, a young man with short dark hair and a teal jacket, kneels beside a bicycle repairing its chain outside a small garage.',
               'seed': 1702},
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scene', choices=SCENES, required=True)
    parser.add_argument('--output', type=Path, default=Path('preview'))
    args = parser.parse_args()
    scene = SCENES[args.scene]
    args.output.mkdir(parents=True, exist_ok=True)
    os.environ['IMAGE_SEED'] = str(scene['seed'])
    output = args.output/f'{args.scene}.png'
    workflow.make_image(scene['prompt'], output)
    with Image.open(output) as picture:
        if picture.size != (1024, 576):
            raise RuntimeError('Preview resolution differs from production')
        picture.resize((384, 216)).save(args.output/f'{args.scene}-mobile.jpg')
    metadata = json.loads(image_cpu.metadata_path(output).read_text())
    if metadata['reference_mode'] != 'style-only-v1' or metadata['steps'] != 16:
        raise RuntimeError('Preview did not use current production style mode')
    (args.output/f'{args.scene}-review.json').write_text(json.dumps({**scene,
        'reference_mode': metadata['reference_mode'], 'style_guidance': metadata['reference_style'],
        'image_sha256': hashlib.sha256(output.read_bytes()).hexdigest()}, indent=2))


if __name__ == '__main__':
    main()
