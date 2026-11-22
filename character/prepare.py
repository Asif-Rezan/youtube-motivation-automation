"""Prepare portable local copies of the original character scripts and scene files."""
import argparse
from pathlib import Path
import shutil

parser = argparse.ArgumentParser()
parser.add_argument('--daz-library', default='/Users/Shared/My DAZ 3D Library')
parser.add_argument('--scripts-only', action='store_true', help='Prepare portable scripts without copying large assets')
args = parser.parse_args()
base = Path(__file__).resolve().parent
runtime = base / 'runtime'
runtime.mkdir(exist_ok=True)
for source in (base / 'scripts').iterdir():
    if source.suffix not in ('.py', '.dsa'):
        continue
    text = source.read_text()
    text = text.replace('/Users/asif/Documents/Projects/youtube-motivation-backup',base.parent.as_posix())
    for name in ('fitness-rigify-review','fitness-motion-library','fitness-rokoko-review','fitness-walk-review','fitness-pilates-review','fitness-garden-demo','fitness-mocap-sample'):
        text=text.replace('/Users/asif/Documents/'+name,(runtime/name).as_posix())
    text = text.replace('/Users/asif/Documents/DAZ 3D', runtime.as_posix())
    text = text.replace('/Users/Shared/My DAZ 3D Library', Path(args.daz_library).expanduser().as_posix())
    (runtime / source.name).write_text(text)
if args.scripts_only:
    print(f'Prepared portable scripts in {runtime}')
    raise SystemExit(0)
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
for name,asset in [('fitness-rigify-review','kat-rigify-walk-v1.blend'),('fitness-rokoko-review','kat-rokoko-walk-v1.blend'),('fitness-walk-review','kat-rokoko-walk-v1.blend'),('fitness-pilates-review','kat-heel-raise-v1.blend')]:
    source=base/'blender'/asset
    if source.stat().st_size<200:
        raise SystemExit(f'{asset} is still a Git LFS pointer; run git lfs pull first.')
    folder=runtime/name;folder.mkdir(exist_ok=True)
    filename=('kat-rigify-final.blend' if name=='fitness-rigify-review' else
              'kat-heel-raise-final.blend' if name=='fitness-pilates-review' else 'kat-continuous-walk-final.blend')
    shutil.copy2(source,folder/filename)
sources=runtime/'fitness-walk-review/sources';sources.mkdir(exist_ok=True)
shutil.copy2(base/'motion/sources/36_02.bvh',sources/'36_02.bvh')
print(f'Prepared local scripts and working copies in {runtime}')
