"""A metadata failure must preserve narration and resume within the same run."""
import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
import human_history as h
import workflow as w


class StoryRecoveryTests(unittest.TestCase):
    def outline(self):
        return dict(title='How Ancient Humans Kept Their Fire Alive', description='Outline only.',
            tags=['Ancient Humans'], thumbnail_text='FIRE GONE?', thumbnail_prompt='An adult tends embers.',
            character_description='An adult in hide clothing', protagonist_name='Ari',
            story_bible='An illustrative camp with uncertain historical details.',
            scenes={f'chapter_{i:02}': dict(summary='Explain fuel and shelter',
                image_prompt='Embers beside a sheltered camp', continuity_note='Same camp',
                image_prompts=['Embers', 'Dry fuel']) for i in range(1, 21)})

    def test_metadata_failure_keeps_twenty_chapters_and_resume_skips_generation(self):
        saved = []
        def ask(endpoint, payload):
            props = payload['response_format']['json_schema']['schema']['properties']
            if 'scenes' in props:
                value = self.outline()
            else:
                value = {'narrations': {key: 'A cold camp presents a practical problem with several possible solutions. ' * 8
                    for key in props['narrations']['properties']}}
            return {'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(value)}}]}
        with patch.dict(os.environ, {}, clear=True), patch.object(w, 'request_text', side_effect=ask), \
             patch('video_metadata.generate_metadata', side_effect=ValueError('metadata rejected')):
            with self.assertRaisesRegex(ValueError, 'metadata rejected'):
                w.make_story('daily-recovery-test', [], checkpoint=lambda value: saved.append(copy.deepcopy(value)))
        self.assertEqual([sum(bool(c.get('narration')) for c in s['scenes']) for s in saved], [0, 5, 10, 15, 20, 20])
        draft = saved[-1]
        original = copy.deepcopy(draft)
        from test_video_metadata import metadata_fixture
        with patch.dict(os.environ, {}, clear=True), patch.object(w, 'request_text') as model, \
             patch('video_metadata.generate_metadata', return_value=metadata_fixture()):
            result = w.make_story('daily-recovery-test', [], draft=draft)
        model.assert_not_called()
        self.assertEqual(draft, original)
        self.assertEqual(result['scenes'], draft['scenes'])
        self.assertEqual(result['scenes'][-1]['narration'].count(h.CTA), 1)
        w.validate_story(result)

    def test_mismatched_checkpoint_run_never_generates_or_overwrites(self):
        import long_video
        store = MagicMock()
        store.load.side_effect = [{}, [], {'run': 'different-run', 'model': 'Qwen/Qwen3-4B-Instruct-2507', 'story': {}}]
        with tempfile.TemporaryDirectory() as directory, patch.object(long_video, 'ROOT', Path(directory)), \
             patch.object(w, 'Store', return_value=store), patch.object(w, 'make_story') as generate, \
             patch.dict(os.environ, {'GENERATE_FRESH_STORY': 'true', 'SAVED_RUN_ID': 'daily-123'}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'checkpoint identity'):
                long_video.stage_story()
        generate.assert_not_called()
        store.save.assert_not_called()
