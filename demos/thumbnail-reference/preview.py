"""Render one reference-guided thumbnail through the production image planner."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from PIL import Image, ImageOps
from kids_rhymes import scene_prompt
from song_images import image_plan
from image_cpu import generate

root=Path('output/thumbnail-reference-preview')
root.mkdir(parents=True,exist_ok=True)
outline={'characters':'Happy toddlers in colorful rompers with fluffy yellow baby chicks.',
         'visual_world':'A dreamy flower meadow with pink blossom trees and soft golden light.'}
prompt=scene_prompt({'visual':'Happy children dance beside fluffy yellow chicks.'},outline,True)
song={'vocal_gender':'female','duration':5,'lyrics':'Happy friends dance and play together',
      'scenes':[{'index':0,'start':0,'end':5,'lyric':'Happy friends dance and play together','prompt':prompt}]}
plan=next(p for p in image_plan(song) if p['kind']=='thumbnail')
(root/'settings.json').write_text(json.dumps(plan,indent=2))
reference=Path(plan['reference_image'])
if not reference.is_absolute():
    reference=Path(__file__).resolve().parents[2]/reference
generate(plan['prompt'],root/'thumbnail-source.png',seed=plan['seed'],
         width=plan['width'],height=plan['height'],steps=plan['steps'],
         reference_image=reference,strength=plan['strength'])
with Image.open(root/'thumbnail-source.png') as image:
    ImageOps.fit(image.convert('RGB'),(1280,720),method=Image.Resampling.LANCZOS).save(root/'thumbnail.jpg',quality=92,optimize=True)
print('Thumbnail preview ready',flush=True)
