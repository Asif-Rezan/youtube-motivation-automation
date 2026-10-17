"""Local, deterministic CPU painting generation using public model weights."""
import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import time

# Previous production image model (restore these defaults to switch back):
# MODEL = 'Lykon/dreamshaper-8'
# REVISION = 'a7e52b98680b1ba8ff7bce97c7f9f2e2e5337917'
SSD_MODEL = MODEL = 'segmind/SSD-1B'
SSD_REVISION = REVISION = '60987f37e94cd59c36b1cba832b9f97b57395a10'
DREAMSHAPER_MODEL = 'Lykon/dreamshaper-8'
DREAMSHAPER_REVISION = 'a7e52b98680b1ba8ff7bce97c7f9f2e2e5337917'
SAFETY_MODEL = 'CompVis/stable-diffusion-safety-checker'
NEGATIVE = ('watercolor, 3d render, glossy plastic, realistic skin texture, '
            'blurry, low detail, poor quality, distorted anatomy, extra arms, extra legs, '
            'deformed hands, duplicate person, watermark, lettering, text, '
            'warm orange lighting, red color cast, sepia')
_pipeline = None
_pipeline_key = None
_reference_pipeline = None
_reference_pipeline_key = None
_safety_checker = None
_safety_processor = None


@dataclass(frozen=True)
class ImageConfig:
    model: str
    revision: str
    width: int
    height: int
    steps: int
    guidance_scale: float
    reference_sha256: str | None = None
    reference_strength: float = 0.0


def image_config():
    model = os.getenv('CPU_IMAGE_MODEL') or MODEL
    if model not in (DREAMSHAPER_MODEL, SSD_MODEL):
        raise ValueError(f'Unsupported CPU image model: {model}')
    revision = os.getenv('CPU_MODEL_REVISION') or (DREAMSHAPER_REVISION if model == DREAMSHAPER_MODEL else SSD_REVISION)
    reference = os.getenv('CPU_STYLE_REFERENCE', '').strip()
    if reference and model != SSD_MODEL:
        raise ValueError('CPU style reference requires SSD-1B')
    strength = float(os.getenv('CPU_REFERENCE_STRENGTH', '0.85')) if reference else 0.0
    if reference and not 0 < strength <= 1:
        raise ValueError('CPU reference strength must be in (0, 1]')
    reference_sha = hashlib.sha256(Path(reference).read_bytes()).hexdigest() if reference else None
    config = ImageConfig(model, revision, int(os.getenv('CPU_IMAGE_WIDTH', '768' if model == DREAMSHAPER_MODEL else '1024')),
                         int(os.getenv('CPU_IMAGE_HEIGHT', '432' if model == DREAMSHAPER_MODEL else '576')),
                         int(os.getenv('CPU_IMAGE_STEPS', '28' if model == DREAMSHAPER_MODEL else '16')),
                         float(os.getenv('CPU_IMAGE_GUIDANCE_SCALE', '7.5' if model == DREAMSHAPER_MODEL else '9.0')),
                         reference_sha, strength)
    if config.width % 8 or config.height % 8 or not 256 <= config.width <= 1536 or not 256 <= config.height <= 1536:
        raise ValueError('CPU image dimensions must be multiples of eight in 256–1536')
    if not 1 <= config.steps <= 50 or not 1 <= config.guidance_scale <= 15:
        raise ValueError('CPU steps must be 1–50 and guidance scale 1–15')
    return config


def load_pipeline(config):
    """Use the matching SD 1.5 or SDXL pipeline; never fall back silently."""
    import torch
    from diffusers import DPMSolverMultistepScheduler, StableDiffusionPipeline, StableDiffusionXLPipeline
    torch.set_num_threads(min(os.cpu_count() or 2, 4))
    pipeline_type = StableDiffusionXLPipeline if config.model == SSD_MODEL else StableDiffusionPipeline
    print(json.dumps({'image_model_loading': config.model, 'revision': config.revision,
                      'pipeline': pipeline_type.__name__}), flush=True)
    pipe = pipeline_type.from_pretrained(config.model, revision=config.revision,
                                         torch_dtype=torch.float32, use_safetensors=True,
                                         trust_remote_code=False)
    pipe.scheduler = DPMSolverMultistepScheduler.from_config(
        pipe.scheduler.config, algorithm_type='dpmsolver++', use_karras_sigmas=True)
    pipe.to('cpu')
    pipe.enable_attention_slicing()
    pipe.enable_vae_slicing()
    return pipe


def metadata_path(path):
    return Path(path).with_suffix('.image.json')


def check_ssd_safety(image):
    """Run a local open-source safety checker before writing an SSD image."""
    global _safety_checker, _safety_processor
    import numpy as np
    import torch
    from diffusers.pipelines.stable_diffusion.safety_checker import StableDiffusionSafetyChecker
    from transformers import CLIPImageProcessor
    if _safety_checker is None:
        _safety_checker = StableDiffusionSafetyChecker.from_pretrained(SAFETY_MODEL, torch_dtype=torch.float32)
        _safety_checker.eval()
        _safety_processor = CLIPImageProcessor.from_pretrained(SAFETY_MODEL)
    pixels = _safety_processor(images=image, return_tensors='pt').pixel_values
    with torch.no_grad():
        _, flags = _safety_checker(images=np.asarray(image, dtype=np.float32)[None] / 255.0,
                           clip_input=pixels)
    if not flags or len(flags) != 1:
        raise RuntimeError('Local image safety checker returned no decision')
    if flags[0]:
        raise RuntimeError('Image blocked by local safety check')


def generate(prompt, path):
    global _pipeline, _pipeline_key, _reference_pipeline, _reference_pipeline_key
    config = image_config()
    key = (config.model, config.revision)
    if _pipeline is None or _pipeline_key != key:
        _pipeline = load_pipeline(config)
        _pipeline_key = key
        _reference_pipeline = None
        _reference_pipeline_key = None
    built_in_safety = getattr(_pipeline, 'safety_checker', None) is not None
    if not built_in_safety and config.model != SSD_MODEL and os.getenv('CPU_IMAGE_BENCHMARK') != 'true':
        raise RuntimeError(f'{config.model} has no content safety checker; refusing production inference')
    import torch
    seed = int(os.getenv('IMAGE_SEED', '42'))
    negative = ', '.join(filter(None, (NEGATIVE, os.getenv('IMAGE_NEGATIVE_PROMPT', '').strip())))
    start = time.monotonic()
    pipe = _pipeline
    options = {'prompt': prompt, 'negative_prompt': negative,
               'num_inference_steps': config.steps, 'guidance_scale': config.guidance_scale,
               'generator': torch.Generator(device='cpu').manual_seed(seed)}
    if config.reference_sha256:
        from diffusers import AutoPipelineForImage2Image
        from PIL import Image, ImageOps
        if _reference_pipeline is None or _reference_pipeline_key != key:
            _reference_pipeline = AutoPipelineForImage2Image.from_pipe(_pipeline)
            _reference_pipeline_key = key
        pipe = _reference_pipeline
        with Image.open(os.environ['CPU_STYLE_REFERENCE']) as reference:
            options['image'] = ImageOps.fit(reference.convert('RGB'),
                                            (config.width, config.height), method=Image.Resampling.LANCZOS)
        options['strength'] = config.reference_strength
    else:
        options.update(width=config.width, height=config.height)
    result = pipe(**options)
    if any(getattr(result, 'nsfw_content_detected', None) or []):
        raise RuntimeError('Image blocked by model safety check')
    image = result.images[0]
    if config.model == SSD_MODEL and os.getenv('CPU_IMAGE_BENCHMARK') != 'true':
        check_ssd_safety(image)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    report = {**asdict(config), 'seed': seed, 'seconds': round(time.monotonic()-start, 2),
              'safety_check_available': built_in_safety or (config.model == SSD_MODEL and os.getenv('CPU_IMAGE_BENCHMARK') != 'true')}
    metadata_path(path).write_text(json.dumps(report))
    print(json.dumps({'cpu_image_generated': str(path), **report}), flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prompt', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    generate(args.prompt, args.output)
