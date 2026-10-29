import copy
import json
import os
import unittest
from unittest.mock import patch

import workflow as w
from content_strategy import PROFILE, PILLARS, select_pillar, validate_pov


class ContentStrategyTests(unittest.TestCase):
    def test_topic_rotation_avoids_recent_three_and_favors_less_used_topics(self):
        history = [{'content_pillar': key} for key in list(PILLARS)[:3]]
        first = select_pillar('daily-123', history)
        self.assertNotIn(first, list(PILLARS)[:3])
        self.assertEqual(first, select_pillar('daily-123', history))
        history += [{'content_pillar': first}]*5
        self.assertNotEqual(first, select_pillar('daily-124', history))
        self.assertIn(select_pillar('old', [{'title': 'Legacy story'}]), PILLARS)

    def test_pov_contract_rejects_lost_viewpoint_and_missing_continuity(self):
        story = {'content_profile': PROFILE, 'title': 'POV: You Turn Down a Raise That Costs Too Much',
                 'description': 'An original fictional scenario.', 'story_bible': 'Maya earns $3000 take-home.',
                 'scenes': [{'narration': 'You read the offer twice.', 'continuity_note': 'Day one; offer undecided.'}]}
        validate_pov(story)
        for field, value in [('title', 'The Wealthy Carpenter'), ('description', 'A true story'),
                             ('story_bible', '')]:
            changed = copy.deepcopy(story)
            changed[field] = value
            with self.assertRaises(ValueError):
                validate_pov(changed)
        changed = copy.deepcopy(story)
        changed['scenes'][0]['narration'] = 'Maya reads the offer twice.'
        with self.assertRaisesRegex(ValueError, 'second-person'):
            validate_pov(changed)
        changed = copy.deepcopy(story)
        changed['scenes'][0]['continuity_note'] = ''
        with self.assertRaisesRegex(ValueError, 'continuity note'):
            validate_pov(changed)
        validate_pov({'title': 'Legacy story'})

    def test_duration_rewrite_retains_pov_contract(self):
        from long_video import rewrite_for_duration
        story = {'content_profile': PROFILE, 'title': 'POV: You Choose Time Over Extra Pay',
                 'description': 'An original fictional scenario.', 'story_bible': 'Maya earns $3000 take-home.',
                 'tags': [], 'thumbnail_text': 'YOUR TIME', 'thumbnail_prompt': 'Maya studies an offer',
                 'character_description': 'Maya in a teal jacket',
                 'scenes': [{'narration': 'You consider the offer and the time it would cost your family. '*7,
                             'image_prompt': 'Maya studies an offer', 'continuity_note': f'Day {i}.'} for i in range(20)]}
        story['scenes'][-1]['narration'] += w.FINAL_CTA
        def ask(endpoint, payload):
            prompt = payload['messages'][0]['content']
            self.assertIn(story['story_bible'], prompt)
            self.assertIn('second person', prompt)
            keys = payload['response_format']['json_schema']['schema']['required']
            return {'choices': [{'message': {'content': json.dumps({key: 'You make a choice that costs time. '*10 for key in keys})}}]}
        revised, changed = rewrite_for_duration(story, 1200, [60]*20, ask=ask)
        self.assertTrue(changed)
        validate_pov(revised)
        self.assertTrue(revised['scenes'][-1]['narration'].endswith(w.FINAL_CTA))

    def test_generated_story_preserves_profile_and_continuity_across_batches(self):
        self._generated_story()

    def test_missing_pov_repairs_only_failed_chapter_before_next_batch(self):
        self._generated_story(bad_responses=1)

    def test_persistent_missing_pov_stops_after_two_repairs(self):
        with self.assertRaisesRegex(ValueError, 'after two repairs: chapter_01'):
            self._generated_story(bad_responses=3)

    def _generated_story(self, bad_responses=0):
        requests = []
        def ask(endpoint, payload, binary=False):
            requests.append(payload)
            properties = payload['response_format']['json_schema']['schema']['properties']
            if 'scenes' in properties:
                result = {'title': 'POV: You Turn Down a Raise That Costs Too Much',
                          'description': 'Original fictional educational scenario, not personal advice.',
                          'tags': ['money'], 'thumbnail_text': 'THE REAL COST',
                          'thumbnail_prompt': 'Maya considers an offer beside a school timetable',
                          'protagonist_name': 'Maya', 'character_description': 'Maya in a teal jacket',
                          'story_bible': 'Maya earns $3000 take-home; the offer adds a night shift.',
                          'scenes': {f'chapter_{i:02}': {'summary': f'Event {i}',
                              'image_prompt': 'Maya studies an offer', 'image_prompts': ['Offer on table'],
                              'continuity_note': f'Day {i}; offer remains undecided.'} for i in range(1, 21)}}
            else:
                keys = properties['narrations']['required']
                result = {'narrations': {key: 'You weigh the extra pay against the hours you would lose. '*7 for key in keys}}
                if 'chapter_01' in keys and len(requests) <= bad_responses + 1:
                    result['narrations']['chapter_01'] = 'Maya weighs the extra pay against the hours she would lose. '*7
                if len(keys) == 1:
                    self.assertEqual(keys, ['chapter_01'])
                    self.assertIn('Day 20; offer remains undecided.', payload['messages'][0]['content'])
            return {'choices': [{'message': {'content': json.dumps(result)}, 'finish_reason': 'stop'}]}
        with patch.dict(os.environ, {'CONTENT_TYPE': 'financial-storytelling'}, clear=True), \
             patch.object(w, 'request_text', side_effect=ask), patch.object(w.time, 'sleep'):
            story = w.make_story('daily-123', [])
        self.assertEqual(story['content_profile'], PROFILE)
        self.assertIn(story['content_pillar'], PILLARS)
        self.assertEqual(len(story['scenes']), 20)
        self.assertEqual(len(requests), 5 + bad_responses)
        for request in requests[1:]:
            prompt = request['messages'][0]['content']
            self.assertIn(story['story_bible'], prompt)
            self.assertIn('Day 20; offer remains undecided.', prompt)
        self.assertTrue(story['scenes'][-1]['narration'].endswith(w.FINAL_CTA))


if __name__ == '__main__':
    unittest.main()
