from contextlib import nullcontext
import json
from pathlib import Path
import random
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from PIL import Image
import long_video as video
import scene_check as check


class SceneAlignmentTests(unittest.TestCase):
    def test_changed_scene_regenerates_image_and_clip(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            shot = {'index': 0, 'seed': 1700, 'duration': 7,
                    'prompt': 'Maya opens a suitcase.', 'semantic_target': 'Maya opens a suitcase.'}
            plan = {'shots': [shot], 'image_interval_seconds': 7, 'storyboard_verified': True,
                    'style': video.w.VISUAL_STYLE_ID, 'scene_composition_version': 2}
            def make_image(prompt, path):
                path.write_bytes(b'new image')
            def make_clip(image, duration, path):
                self.assertFalse(path.exists(), 'A stale clip must not survive image regeneration')
                path.write_bytes(b'new clip')
            (root/'shot-000.mp4').write_bytes(b'stale clip without image')
            with patch.dict('os.environ', {'IMAGE_BACKEND': 'hf'}), \
                 patch.object(video.w, 'make_image', side_effect=make_image) as make, \
                 patch.object(check, 'check_scene', return_value={'passed': True, 'required': True}), \
                 patch.object(video, 'picture_clip', side_effect=make_clip) as clip:
                for target in ('Maya opens a suitcase.', 'Maya repairs a broken clock.'):
                    shot.update(prompt=target, semantic_target=target)
                    (root/'plan.json').write_text(json.dumps(plan))
                    video.generate_shard(0, root)
                self.assertEqual(make.call_count, 2)
                self.assertEqual(clip.call_count, 2)
            report = json.loads((root/'shot-000.qa.json').read_text())
            self.assertEqual(report['source_signature'], check.scene_signature(shot))

    def test_assembly_rejects_old_character_checks_that_skipped_semantics(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            shot = {'index': 0, 'prompt': 'Maya repairs a clock.'}
            (root/'plan.json').write_text(json.dumps({'shots': [shot]}))
            (root/'shot-000.qa.json').write_text(json.dumps({'passed': True, 'required': False,
                'source_signature': check.scene_signature(shot)}))
            with self.assertRaisesRegex(RuntimeError, 'Every image'):
                video.finish(root)

    def test_character_images_record_semantic_mismatch_without_blocking_render(self):
        with tempfile.TemporaryDirectory() as temp:
            image = Path(temp)/'scene.png'
            rng = random.Random(10)
            Image.frombytes('RGB', (64, 64), bytes(rng.randrange(256) for _ in range(64*64*3))).save(image)
            processor = MagicMock(return_value={})
            model = MagicMock()
            model.return_value.logits_per_image.__getitem__.return_value.tolist.return_value = [20, 26, 10, 8, 9]
            shot = {'focus': 'person', 'semantic_target': 'Maya repairs the broken clock at her desk.',
                    'semantic_alternatives': ['Maya boards a train at the station.']}
            with patch.object(check, '_processor', processor), patch.object(check, '_model', model), \
                 patch.dict(sys.modules, {'torch': SimpleNamespace(inference_mode=nullcontext),
                     'transformers': SimpleNamespace(CLIPModel=object, CLIPProcessor=object)}):
                result = check.check_scene(image, shot)
            self.assertTrue(result['required'])
            self.assertTrue(result['passed'])
            self.assertFalse(result['semantic_match'])
            self.assertIn(shot['semantic_target'], processor.call_args.kwargs['text'])
            self.assertIn(shot['semantic_alternatives'][0], processor.call_args.kwargs['text'])

    def test_nearly_identical_neighbor_is_not_used_as_wrong_event(self):
        target = 'Maya repairs the broken clock at her desk.'
        candidates = check.scene_candidates({'semantic_target': target,
            'semantic_alternatives': [target, target.replace('.', '!'), 'A truck crosses a flooded bridge.']})
        self.assertEqual(candidates.count(target), 1)
        self.assertNotIn(target.replace('.', '!'), candidates)
        self.assertIn('A truck crosses a flooded bridge.', candidates)
        self.assertTrue(check.evaluate_scores([25, 20, 19]))
        self.assertFalse(check.evaluate_scores([20, 20, 19]))
        self.assertFalse(check.evaluate_scores([float('nan'), 10]))

    def test_prompt_or_narration_changes_invalidate_previous_scene_check(self):
        shot = {'prompt': 'Maya opens the shop.', 'narration': 'She opens the shop.'}
        original = check.scene_signature(shot)
        self.assertNotEqual(original, check.scene_signature({**shot, 'narration': 'She closes the shop.'}))
        self.assertNotEqual(original, check.scene_signature({**shot, 'prompt': 'Maya closes the shop.'}))

    def test_refinement_preserves_both_actions_and_compares_neighboring_events(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'story.json').write_text(json.dumps({'protagonist_name': 'Maya',
                'character_description': 'woman wearing a blue coat', 'scenes': [{'narration': 'Maya works.'}]}))
            action = 'Maya signals the driver; the truck crosses the bridge'
            (root/'plan.json').write_text(json.dumps({'shots': [
                {'visual_action': action}, {'visual_action': 'Maya counts coins in the shop.'}]}))
            plan = video.refine_visual_plan(root)
            self.assertEqual(plan['shots'][0]['semantic_target'], action)
            self.assertIn(plan['shots'][1]['semantic_target'], plan['shots'][0]['semantic_alternatives'])

    def test_cross_chapter_storyboard_receives_both_contexts(self):
        story = {'character_description': 'Maya in a blue coat', 'scenes': [
            {'narration': 'Maya lifts her suitcase at the station.'},
            {'narration': 'Her brother repairs a clock in his shop.'}]}
        words = [[{'word': 'suitcase', 'start': 0, 'end': 7.2}],
                 [{'word': 'clock', 'start': 0, 'end': 8.3}]]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = video.shot_plan(story, [7.2, 8.3], words)
            (root/'story.json').write_text(json.dumps(story))
            (root/'plan.json').write_text(json.dumps(plan))
            def ask(endpoint, payload):
                prompt = payload['messages'][0]['content']
                self.assertIn(story['scenes'][0]['narration'], prompt)
                self.assertIn(story['scenes'][1]['narration'], prompt)
                self.assertIn('previous_spoken', prompt)
                self.assertIn('next_spoken', prompt)
                return {'choices': [{'message': {'content': json.dumps({f'shot_{i:03}':
                    'Maya carries a red suitcase beside the station bench.' for i in range(3)})}}]}
            video.storyboard(root, ask=ask, pause=lambda _: None)


if __name__ == '__main__':
    unittest.main()
