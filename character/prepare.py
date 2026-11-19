"""Prepare portable local copies of the original character scripts and scene files."""
import argparse
from pathlib import Path
import shutil

parser = argparse.ArgumentParser()
parser.add_argument('--daz-library', default='/Users/Shared/My DAZ 3D Library')
args = parser.parse_args()
base = Path(__file__).resolve().parent
runtime = base / 'runtime'
runtime.mkdir(exist_ok=True)
for source in (base / 'scripts').iterdir():
    if source.suffix not in ('.py', '.dsa'):
        continue
    text = source.read_text().replace('/Users/asif/Documents/DAZ 3D', runtime.as_posix())
    text = text.replace('/Users/Shared/My DAZ 3D Library', Path(args.daz_library).expanduser().as_posix())
    (runtime / source.name).write_text(text)
scenes = runtime / 'Studio/My Library/Scenes'
scenes.mkdir(parents=True, exist_ok=True)
for source in (base / 'daz').glob('*.duf'):
    shutil.copy2(source, scenes / source.name)
demo = runtime / 'kat-blender-short'
demo.mkdir(exist_ok=True)
for name in ('kat-animated.blend', 'eyes-composite.png'):
    source = base / 'blender' / name
    if source.stat().st_size < 200:
        raise SystemExit(f'{source.name} is still a Git LFS pointer; run git lfs pull first.')
    shutil.copy2(source, demo / name)
shutil.copy2(base / 'blender/kat-outfit-trainer.fbx', runtime / 'kat-outfit-trainer.fbx')
print(f'Prepared local scripts and working copies in {runtime}')
