import copy
import hashlib
import unittest
from unittest.mock import patch
import human_history as h
import workflow as w
from script_quality import narration_issues
import test_story_recovery
from test_video_metadata import metadata_fixture


class NarrationRepairTests(unittest.TestCase):
    def draft(self):
        draft = test_story_recovery.StoryRecoveryTests().outline()
        draft['scenes'] = list(draft['scenes'].values())
        draft.update(content_profile=h.PROFILE, content_pillar='fire')
        for i, chapter in enumerate(draft['scenes']):
            chapter['narration'] = ' '.join(hashlib.sha256(f'{i}-{j}'.encode()).hexdigest()[:12] for j in range(80)) + '.'
        draft['scenes'][4]['narration'] = draft['scenes'][0]['narration']
        return draft

    def test_saved_duplicate_is_rewritten_without_regenerating_good_chapters(self):
        draft = self.draft()
        original = copy.deepcopy(draft)
        saved = []
        def ask(prompt, limit, schema):
            self.assertIn('Rewrite chapter 5 only', prompt)
            return {'narration': ' '.join(hashlib.sha256(f'repaired-{j}'.encode()).hexdigest()[:12] for j in range(80)) + '.'}
        with patch('video_metadata.generate_metadata', return_value=metadata_fixture()):
            result = h.generate('test', [], ask, lambda _: None, lambda *args: None,
                                lambda props: dict(type='object', properties=props, required=list(props), additionalProperties=False), draft=draft, checkpoint=lambda value: saved.append(value))
        self.assertFalse(narration_issues(result))
        self.assertEqual(draft, original)
        self.assertEqual(result['scenes'][0], draft['scenes'][0])
        self.assertNotEqual(result['scenes'][4], draft['scenes'][4])
        self.assertTrue(any(not narration_issues(value) for value in saved))

    def test_persistent_bad_model_output_is_bounded_and_checkpointed(self):
        draft = self.draft()
        calls = []
        def ask(*args):
            calls.append(1)
            return {'narration': draft['scenes'][0]['narration']}
        with self.assertRaisesRegex(ValueError, 'three passes'):
            h.generate('test', [], ask, lambda _: None, lambda *args: None,
                       lambda props: dict(type='object', properties=props, required=list(props), additionalProperties=False), draft=draft)
        self.assertEqual(len(calls), 3)
