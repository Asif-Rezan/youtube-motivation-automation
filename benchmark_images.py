"""Small manual GitHub Actions CPU benchmark; never generates or uploads a video."""
import argparse
import json
import os
from pathlib import Path
import resource
import shutil
import time

from image_cpu import generate, image_config

SCENES = [
    ('bridge', 'Maya in a blue coat braces a broken wooden bridge beam while two workers pull a rope, anxious determined expression, storm-damaged river crossing'),
    ('letter', 'Maya in the same blue coat reads a handwritten letter at a kitchen table, surprised relieved expression, evening lamplight, rain on the window'),
]


def benchmark(root):
    root.mkdir(parents=True, exist_ok=True)
    config = image_config()
    disk = shutil.disk_usage(root)
    report = {'model': config.model, 'revision': config.revision,
              'runner': {'cpus': os.cpu_count(), 'disk_free_gb': round(disk.free/1e9, 2)},
              'samples': []}
    report_path = root/'benchmark.json'
    settings = [(config.width, config.height, config.steps, config.guidance_scale)]
    if config.model == 'segmind/SSD-1B':
        settings.append((config.width, config.height, 20, 9.0))
    else:
        settings.append((1024, 576, config.steps, config.guidance_scale))
    try:
        from huggingface_hub import HfApi
        info = HfApi().model_info(config.model, revision=config.revision, files_metadata=True)
        report['full_repository_size_gb'] = round(sum(f.size or 0 for f in info.siblings)/1e9, 2)
        # Diffusers downloads only the selected component files, not standalone checkpoints.
        chosen = [f for f in info.siblings if f.rfilename.endswith('model.safetensors')
                  or f.rfilename.endswith('diffusion_pytorch_model.safetensors')]
        report['float32_component_weights_gb'] = round(sum(f.size or 0 for f in chosen)/1e9, 2)
    except Exception as exc:
        report['repository_size_error'] = str(exc)
    report_path.write_text(json.dumps(report, indent=2))
    for width, height, steps, guidance in settings:
        for index, (name, prompt) in enumerate(SCENES):
            os.environ.update(CPU_IMAGE_WIDTH=str(width), CPU_IMAGE_HEIGHT=str(height),
                              CPU_IMAGE_STEPS=str(steps), CPU_IMAGE_GUIDANCE_SCALE=str(guidance),
                              IMAGE_SEED=str(1700+index), IMAGE_NEGATIVE_PROMPT='unrelated scenery, extra people')
            path = root/f'{name}-{width}x{height}-{steps}-{guidance}.png'
            started = time.monotonic()
            try:
                result = generate(prompt, path)
                sample = {'scene': name, 'file': path.name, **result,
                          'elapsed_with_load_seconds': round(time.monotonic()-started, 2),
                          'peak_process_rss_gb': round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1e6, 2),
                          'disk_free_gb': round(shutil.disk_usage(root).free/1e9, 2)}
            except Exception as exc:
                sample = {'scene': name, 'error': f'{type(exc).__name__}: {exc}',
                          'elapsed_seconds': round(time.monotonic()-started, 2)}
                report['samples'].append(sample)
                report_path.write_text(json.dumps(report, indent=2))
                raise
            report['samples'].append(sample)
            report_path.write_text(json.dumps(report, indent=2))
            print(json.dumps(sample), flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path('benchmark-output'))
    args = parser.parse_args()
    benchmark(args.output)
