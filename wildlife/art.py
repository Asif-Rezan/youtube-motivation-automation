"""Produce story-specific thumbnail artwork with SSD-1B."""
import argparse
import hashlib
import json
from pathlib import Path


def make_art(manifest, path):
    from image_cpu import generate
    idea = manifest['idea']
    prompt = (f"{idea['thumbnail_prompt']}. {idea['species']} in close-up beside a "
              f"dramatic view of the {idea['habitat']}, bright polished wildlife CGI, "
              'upper fifth clear for title, no lettering.')
    seed = int.from_bytes(hashlib.sha256(manifest['episode'].encode()).digest()[:4],'big')
    generate(prompt,path,seed,width=768,height=432,steps=12,wildlife=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    make_art(json.loads(args.manifest.read_text()),args.output)
