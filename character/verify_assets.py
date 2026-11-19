"""Verify saved character assets, including LFS pointers without downloading them."""
import hashlib,json
from pathlib import Path

def verify(root):
    manifest=json.loads((root/'character/motion/asset-manifest.json').read_text())
    checked=[]
    for entry in manifest['assets']:
        path=root/entry['path']
        if not path.is_file():raise ValueError(f'Missing asset: {entry["path"]}')
        with path.open('rb') as stream:header=stream.read(200)
        if header.startswith(b'version https://git-lfs.github.com/spec/v1\n'):
            lines=path.read_text().splitlines()
            oid=next(line.split('sha256:',1)[1] for line in lines if line.startswith('oid sha256:'))
            size=int(next(line.split()[1] for line in lines if line.startswith('size ')))
        else:
            digest=hashlib.sha256()
            with path.open('rb') as stream:
                for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
            oid=digest.hexdigest();size=path.stat().st_size
        if oid!=entry['sha256'] or size!=entry['bytes']:
            raise ValueError(f'Asset identity mismatch: {entry["path"]}')
        checked.append(entry['path'])
    return checked

if __name__=='__main__':
    root=Path(__file__).resolve().parent.parent
    print(json.dumps({'verified':verify(root)},indent=2))
