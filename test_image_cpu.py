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
from scene_check import check_scene


class ImageCPUChecks(unittest.TestCase):
    def test_models_and_resolution_configuration(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(image_cpu.image_config().model, image_cpu.MODEL)
            self.assertEqual((image_cpu.image_config().width, image_cpu.image_config().height), (768, 432))
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
            for model in (image_cpu.MODEL, image_cpu.SSD_MODEL):
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
             patch.dict(sys.modules, {'torch': fake_torch}):
            image_cpu._pipeline = None
            path = Path(temp)/'sample.png'
            report = image_cpu.generate('A narrated bridge repair', path)
            self.assertTrue(path.exists())
            self.assertEqual(report['model'], image_cpu.SSD_MODEL)
            self.assertEqual(report['seed'], 1700)
            self.assertEqual(pipe.kwargs['generator'], 1700)
            self.assertIn('deformed hands', pipe.kwargs['negative_prompt'])
            self.assertEqual(json.loads(image_cpu.metadata_path(path).read_text())['model'], image_cpu.SSD_MODEL)
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
                    'negative_prompt': '', 'duration': 7}
            (root/'plan.json').write_text(json.dumps({'storyboard_verified': True,
                'scene_composition_version': 2, 'shots': [shot]}))
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
            fake_scene = types.SimpleNamespace(check_scene=lambda image, shot: {'passed': True})
            with patch.dict(sys.modules, {'scene_check': fake_scene}), \
                 patch.object(long_video.w, 'make_image', side_effect=make), \
                 patch.object(long_video, 'picture_clip'):
                long_video.generate_shard(0, root)
            self.assertEqual(calls, [shot['prompt']])
            self.assertEqual(json.loads((root/'shot-000.qa.json').read_text())['image_generation']['model'], image_cpu.MODEL)

    def test_model_without_safety_checker_cannot_run_in_production(self):
        pipe = types.SimpleNamespace(safety_checker=None)
        with tempfile.TemporaryDirectory() as temp, \
             patch.dict(os.environ, {'CPU_IMAGE_MODEL': image_cpu.SSD_MODEL}, clear=True), \
             patch.object(image_cpu, 'load_pipeline', return_value=pipe):
            image_cpu._pipeline = None
            with self.assertRaisesRegex(RuntimeError, 'no content safety checker'):
                image_cpu.generate('A safe fictional scene', Path(temp)/'scene.png')
        image_cpu._pipeline = None
        image_cpu._pipeline_key = None


if __name__ == '__main__':
    unittest.main()
