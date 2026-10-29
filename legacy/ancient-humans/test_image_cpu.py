import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from PIL import Image
import image_cpu
import long_video
import workflow
from scene_check import check_scene


class ImageCPUChecks(unittest.TestCase):
    def test_models_and_resolution_configuration(self):
        self.assertNotIn('photograph', image_cpu.NEGATIVE)
        for term in ('watercolor', '3d render', 'blurry', 'low detail', 'poor quality', 'distorted anatomy', 'watermark', 'text'):
            self.assertIn(term, image_cpu.NEGATIVE)
        self.assertIn('cel shading', image_cpu.NEGATIVE)
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(image_cpu.image_config().model, image_cpu.MODEL)
            self.assertEqual((image_cpu.image_config().width, image_cpu.image_config().height), (1024, 576))
            self.assertEqual((image_cpu.image_config().steps, image_cpu.image_config().guidance_scale), (16, 9.0))
        with patch.dict(os.environ, {'CPU_IMAGE_MODEL': image_cpu.SSD_MODEL,
                                     'CPU_IMAGE_WIDTH': '1024', 'CPU_IMAGE_HEIGHT': '576',
                                     'CPU_IMAGE_STEPS': '16', 'CPU_IMAGE_GUIDANCE_SCALE': '7.0'}):
            config = image_cpu.image_config()
            self.assertEqual((config.width, config.height, config.steps, config.guidance_scale),
                             (1024, 576, 16, 7.0))
        with patch.dict(os.environ, {'CPU_IMAGE_MODEL': 'unreviewed/model'}):
            with self.assertRaisesRegex(ValueError, 'Unsupported'):
                image_cpu.image_config()
        with patch.dict(os.environ, {'CPU_IMAGE_WIDTH': '1001'}):
            with self.assertRaisesRegex(ValueError, 'multiples of eight'):
                image_cpu.image_config()

    def test_story_image_prompt_adds_cinematic_style(self):
        with patch.object(image_cpu, 'generate') as generate:
            workflow.make_image('Mayra reads a letter', Path('sample.png'))
        prompt = generate.call_args.args[0]
        self.assertEqual(prompt.count(workflow.VISUAL_STYLE), 1)
        self.assertIn('historical documentary reconstruction', prompt)
        self.assertIn('Mayra reads a letter', prompt)

    def test_ssd_uses_sdxl_and_dreamshaper_uses_sd15(self):
        called = []
        class Scheduler:
            @staticmethod
            def from_config(*args, **kwargs):
                return object()
        class Base:
            @classmethod
            def from_pretrained(cls, model, **kwargs):
                called.append((cls.__name__, model, kwargs))
                pipe = cls()
                pipe.scheduler = types.SimpleNamespace(config={})
                return pipe
            def to(self, device):
                self.device = device
            def enable_attention_slicing(self):
                pass
            def enable_vae_slicing(self):
                pass
        class StableDiffusionPipeline(Base):
            pass
        class StableDiffusionXLPipeline(Base):
            pass
        fake_diffusers = types.SimpleNamespace(StableDiffusionPipeline=StableDiffusionPipeline,
            StableDiffusionXLPipeline=StableDiffusionXLPipeline, DPMSolverMultistepScheduler=Scheduler)
        fake_torch = types.SimpleNamespace(float32='float32', set_num_threads=lambda n: None)
        with patch.dict(sys.modules, {'torch': fake_torch, 'diffusers': fake_diffusers}):
            for model in (image_cpu.DREAMSHAPER_MODEL, image_cpu.SSD_MODEL):
                config = image_cpu.ImageConfig(model, 'main', 1024, 576, 16, 7)
                image_cpu.load_pipeline(config)
        self.assertEqual([item[0] for item in called], ['StableDiffusionPipeline', 'StableDiffusionXLPipeline'])
        self.assertTrue(all(item[2]['use_safetensors'] for item in called))
        self.assertTrue(all(item[2]['trust_remote_code'] is False for item in called))

    def test_generation_records_model_and_seed_without_fallback(self):
        class Pipe:
            safety_checker = object()
            def __call__(self, **kwargs):
                self.kwargs = kwargs
                return types.SimpleNamespace(images=[Image.new('RGB', (1024, 576), 'blue')],
                                             nsfw_content_detected=[False])
        pipe = Pipe()
        fake_torch = types.SimpleNamespace(Generator=lambda device: types.SimpleNamespace(
            manual_seed=lambda seed: seed))
        with tempfile.TemporaryDirectory() as temp, \
             patch.dict(os.environ, {'CPU_IMAGE_MODEL': image_cpu.SSD_MODEL,
                                     'CPU_IMAGE_WIDTH': '1024', 'CPU_IMAGE_HEIGHT': '576',
                                     'IMAGE_SEED': '1700'}, clear=True), \
             patch.object(image_cpu, 'load_pipeline', return_value=pipe), \
             patch.object(image_cpu, 'check_ssd_safety') as safety_check, \
             patch.dict(sys.modules, {'torch': fake_torch}):
            image_cpu._pipeline = None
            path = Path(temp)/'sample.png'
            report = image_cpu.generate('A narrated bridge repair', path)
            self.assertTrue(path.exists())
            self.assertEqual(report['model'], image_cpu.SSD_MODEL)
            self.assertEqual(report['seed'], 1700)
            safety_check.assert_called_once()
            self.assertEqual(pipe.kwargs['generator'], 1700)
            self.assertIn('deformed hands', pipe.kwargs['negative_prompt'])
            self.assertIn('cartoon', pipe.kwargs['negative_prompt'])
            self.assertNotIn('photorealistic', pipe.kwargs['negative_prompt'])
            self.assertNotIn('realistic skin texture', pipe.kwargs['negative_prompt'])
            self.assertEqual(json.loads(image_cpu.metadata_path(path).read_text())['model'], image_cpu.SSD_MODEL)
        image_cpu._pipeline = None
        image_cpu._pipeline_key = None

    def test_style_reference_guides_style_without_copying_scene_geometry(self):
        class Pipe:
            safety_checker = object()
            def __init__(self): self.calls = []
            def __call__(self, **kwargs):
                self.calls.append(kwargs)
                return types.SimpleNamespace(images=[Image.new('RGB', (1024, 576), 'blue')],
                                             nsfw_content_detected=[False])
        pipe = Pipe()
        generator = types.SimpleNamespace(Generator=lambda device: types.SimpleNamespace(
            manual_seed=lambda seed: seed))
        prompts = ['Worker leaves the office', 'Hands count coins at a kitchen table',
                   'Mechanic repairs a bicycle outside a garage']
        with tempfile.TemporaryDirectory() as temp:
            reference = Path(temp)/'reference.png'
            Image.new('RGB', (1024, 576), (85, 105, 130)).save(reference)
            with patch.dict(os.environ, {'CPU_IMAGE_MODEL': image_cpu.SSD_MODEL,
                    'CPU_STYLE_REFERENCE': str(reference), 'CPU_REFERENCE_STRENGTH': '0.35'}, clear=True), \
                 patch.object(image_cpu, 'load_pipeline', return_value=pipe), \
                 patch.object(image_cpu, 'check_ssd_safety'), \
                 patch.dict(sys.modules, {'torch': generator}):
                image_cpu._pipeline = None
                image_cpu._pipeline_key = None
                for index, prompt in enumerate(prompts):
                    os.environ['IMAGE_SEED'] = str(1700+index)
                    report = image_cpu.generate(prompt, Path(temp)/f'shot-{index}.png')
                    self.assertEqual(report['reference_mode'], 'style-only-v1')
                    self.assertEqual(report['reference_strength'], 0)
                    self.assertTrue(report['reference_sha256'])
            for index, call in enumerate(pipe.calls):
                self.assertEqual(call['prompt'], prompts[index])
                self.assertIn('realistic material textures', call['prompt_2'])
                self.assertIn('natural lighting', call['prompt_2'])
                self.assertNotIn('slate blue', call['prompt_2'])
                self.assertIn(prompts[index], call['prompt_2'])
                self.assertNotIn('image', call)
                self.assertNotIn('strength', call)
                self.assertEqual(call['generator'], 1700+index)
                self.assertEqual(call['num_inference_steps'], 16)
                self.assertEqual((call['width'], call['height']), (1024, 576))
        image_cpu._pipeline = None
        image_cpu._pipeline_key = None

    def test_blank_frame_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'blank.png'
            Image.new('RGB', (768, 432), 'gray').save(path)
            fake_torch = types.SimpleNamespace()
            fake_transformers = types.SimpleNamespace(CLIPModel=object, CLIPProcessor=object)
            with patch.dict(sys.modules, {'torch': fake_torch, 'transformers': fake_transformers}):
                # A blank frame is rejected before CLIP inference.
                report = check_scene(path, {'focus': 'object'})
            self.assertFalse(report['passed'])
            self.assertEqual(report['method'], 'image-detail-check')

    def test_stale_model_image_is_regenerated_and_recorded(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {'IMAGE_BACKEND': 'cpu'}, clear=True):
            root = Path(temp)
            shot = {'index': 0, 'seed': 1700, 'prompt': 'Maya repairs a bridge',
                    'negative_prompt': '', 'duration': 5}
            (root/'plan.json').write_text(json.dumps({'storyboard_verified': True,
                'scene_composition_version': 2, 'style': workflow.VISUAL_STYLE_ID,
                'image_interval_seconds': long_video.INTERVAL,
                'shots': [shot]}))
            image = root/'shot-000.png'
            image.write_bytes(b'stale')
            image_cpu.metadata_path(image).write_text(json.dumps({'model': image_cpu.SSD_MODEL}))
            calls = []
            def make(prompt, path):
                calls.append(prompt)
                path.write_bytes(b'new')
                config = image_cpu.image_config()
                image_cpu.metadata_path(path).write_text(json.dumps({
                    'model': config.model, 'revision': config.revision,
                    'width': config.width, 'height': config.height,
                    'steps': config.steps, 'guidance_scale': config.guidance_scale}))
            from scene_check import scene_signature
            fake_scene = types.SimpleNamespace(check_scene=lambda image, shot: {'passed': True},
                                               scene_signature=scene_signature)
            with patch.dict(sys.modules, {'scene_check': fake_scene}), \
                 patch.object(long_video.w, 'make_image', side_effect=make), \
                 patch.object(long_video, 'picture_clip'):
                long_video.generate_shard(0, root)
            self.assertEqual(calls, [shot['prompt']])
            self.assertEqual(json.loads((root/'shot-000.qa.json').read_text())['image_generation']['model'], image_cpu.MODEL)

    def test_shard_safety_rejections_use_new_seeds_and_remain_bounded(self):
        for rejected in (1, 2, 3, 6, 7):
            with self.subTest(rejected=rejected), tempfile.TemporaryDirectory() as temp, \
                 patch.dict(os.environ, {'IMAGE_BACKEND': 'cpu'}, clear=True):
                root = Path(temp)
                shot = {'index': 0, 'seed': 1700, 'prompt': 'An adult repairs a bridge',
                        'duration': 5}
                (root/'plan.json').write_text(json.dumps({'storyboard_verified': True,
                    'scene_composition_version': 2, 'style': workflow.VISUAL_STYLE_ID,
                    'image_interval_seconds': long_video.INTERVAL, 'shots': [shot]}))
                seeds, prompts = [], []
                def render(prompt, target):
                    seeds.append(int(os.environ['IMAGE_SEED']))
                    prompts.append(prompt)
                    if len(seeds) <= rejected:
                        target.write_bytes(b'rejected')
                        image_cpu.metadata_path(target).write_text('{}')
                        raise image_cpu.ImageSafetyRejected('Image blocked by local safety check')
                    self.assertFalse(target.exists())
                    target.write_bytes(b'accepted')
                    image_cpu.metadata_path(target).write_text(json.dumps({'seed': seeds[-1]}))
                with patch.object(long_video.w, 'make_image', side_effect=render), \
                     patch('scene_check.check_scene', return_value={'passed': True}) as check, \
                     patch.object(long_video, 'picture_clip') as clip:
                    if rejected == 7:
                        with self.assertRaisesRegex(RuntimeError, 'safety rejected all 7'):
                            long_video.generate_shard(0, root)
                        check.assert_not_called()
                        clip.assert_not_called()
                        self.assertFalse((root/'shot-000.png').exists())
                        self.assertFalse((root/'shot-000.image.json').exists())
                    else:
                        long_video.generate_shard(0, root)
                        check.assert_called_once()
                        clip.assert_called_once()
                        qa = json.loads((root/'shot-000.qa.json').read_text())
                        self.assertEqual(qa['image_generation']['seed'], 1700+rejected*1000)
                self.assertEqual(seeds, [1700+i*1000 for i in range(len(seeds))])
                self.assertEqual(prompts[:2], [shot['prompt']]*min(2, len(prompts)))
                if len(prompts) > 2:
                    self.assertNotEqual(prompts[2], shot['prompt'])
                    self.assertIn('fully clothed adults', prompts[2])
                    self.assertIn(shot['prompt'], prompts[2])
                    self.assertTrue(all(p == prompts[2] for p in prompts[2:]))

    def test_thumbnail_safety_retries_then_rewrites(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {'IMAGE_SEED': '9931'}):
            source = Path(temp)/'thumbnail-source.png'
            calls = []
            def render(prompt, target):
                calls.append((prompt, int(os.environ['IMAGE_SEED'])))
                if len(calls) < 3:
                    raise image_cpu.ImageSafetyRejected('blocked')
                target.write_bytes(b'accepted')
            with patch.object(long_video.w, 'make_image', side_effect=render):
                long_video.render_safe_thumbnail('A woman studies a letter', source)
            self.assertEqual([seed for _, seed in calls], [9931, 10931, 11931])
            self.assertEqual(calls[0][0], calls[1][0])
            self.assertIn('Family-friendly', calls[2][0])
            self.assertEqual(os.environ['IMAGE_SEED'], '9931')

    def test_ssd_requires_local_safety_check_before_saving(self):
        class Pipe:
            safety_checker = None
            def __call__(self, **kwargs):
                return types.SimpleNamespace(images=[Image.new('RGB', (1024, 576), 'blue')])
        fake_torch = types.SimpleNamespace(Generator=lambda device: types.SimpleNamespace(
            manual_seed=lambda seed: seed))
        with tempfile.TemporaryDirectory() as temp, \
             patch.dict(os.environ, {'CPU_IMAGE_MODEL': image_cpu.SSD_MODEL}, clear=True), \
             patch.object(image_cpu, 'load_pipeline', return_value=Pipe()), \
             patch.object(image_cpu, 'check_ssd_safety', side_effect=RuntimeError('blocked')) as check, \
             patch.dict(sys.modules, {'torch': fake_torch}):
            image_cpu._pipeline = None
            path = Path(temp)/'scene.png'
            with self.assertRaisesRegex(RuntimeError, 'blocked'):
                image_cpu.generate('A safe fictional scene', path)
            check.assert_called_once()
            self.assertFalse(path.exists())
        image_cpu._pipeline = None
        image_cpu._pipeline_key = None


if __name__ == '__main__':
    unittest.main()
