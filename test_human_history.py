import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import human_history as h
import workflow as w


class HumanHistoryTests(unittest.TestCase):
    def test_thumbnail_recovery_and_strict_validation(self):
        for pillar in h.PILLARS:
            for value in ('', 'FIRE', 'one two three four five six', 'x'*46 + ' y', None, [], 42):
                with self.subTest(pillar=pillar, value=value):
                    story = dict(content_profile=h.PROFILE, content_pillar=pillar,
                                 title=h.PILLARS[pillar], story_bible='Evidence limits',
                                 thumbnail_text=value)
                    with self.assertRaises(ValueError):
                        h.validate(story)
                    h.repair_thumbnail_text(story)
                    h.validate(story)
                    self.assertEqual(story['thumbnail_text'], h.THUMBNAIL_FALLBACKS[pillar])
        story = {'content_pillar': 'fire', 'thumbnail_text': '  FIRE  GONE?\n'}
        self.assertIs(h.repair_thumbnail_text(story), story)
        self.assertEqual(story['thumbnail_text'], 'FIRE GONE?')

    def test_narrated_humans_and_animals_are_kept_in_visual_plan(self):
        from long_video import refine_visual_plan
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            story = dict(content_profile=h.PROFILE, protagonist_name='Ari',
                character_description='Adult in hide clothing', scenes=[{'narration': 'Hunters follow a deer.'}])
            actions = ['Hunters track deer across grassland', 'Wolf standing beside a woodland stream',
                       'Children gather berries with their mother', 'Flint tools rest beside hearth ashes']
            (root/'story.json').write_text(json.dumps(story))
            (root/'plan.json').write_text(json.dumps({'shots': [{'visual_action': a} for a in actions]}))
            shots = refine_visual_plan(root)['shots']
            self.assertEqual([s['focus'] for s in shots], ['group', 'animal', 'group', 'object'])
            for i in (0, 2):
                self.assertNotIn('people, person, face, portrait', shots[i]['negative_prompt'])
            for i in (0, 1):
                self.assertIn('Natural animal anatomy and scale', shots[i]['prompt'])
                self.assertIn(actions[i], shots[i]['prompt'])
            self.assertNotIn('An adult', shots[1]['prompt'])
            self.assertNotIn('person, face, portrait', shots[1]['negative_prompt'])
            self.assertIn('human portrait', shots[1]['negative_prompt'])

    def test_environmental_reconstruction_avoids_mascot_and_preserves_objects(self):
        action = 'Cold hearth ashes beside flint tools under a limestone rock shelter'
        prompt = h.visual_prompt(action, people=False)
        self.assertIn(action, prompt)
        self.assertIn('Realistic stone, wood and earth textures', prompt)
        self.assertNotIn('adult', prompt)
        self.assertNotIn('white circle', prompt)
        self.assertIn('cartoon', h.image_negative(action))

    def test_cold_ashes_suppress_flames_without_suppressing_ember_scenes(self):
        self.assertIn('flames', h.image_negative('Ari examines cold gray ashes'))
        self.assertNotIn('flames', h.image_negative('Ari blows on a red ember'))
        prompt = h.visual_prompt('Ari sits beside gray ashes')
        self.assertIn('Historical documentary reconstruction', prompt)
        self.assertNotIn('stick figure', prompt)
        self.assertNotIn('caveman', prompt)

    def test_scene_plan_preserves_action_and_allows_large_character(self):
        from long_video import refine_visual_plan
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            story = dict(content_profile=h.PROFILE, protagonist_name='Ari',
                character_description='Ari in a tunic', scenes=[{'narration': 'Ari watches cold ashes.'}])
            plan = {'shots': [{'visual_action': 'Ari kneels beside cold hearth ashes'},
                              {'visual_action': 'Gray ashes fill a stone hearth'}]}
            (root/'story.json').write_text(json.dumps(story))
            (root/'plan.json').write_text(json.dumps(plan))
            result = refine_visual_plan(root)
            person, objects = result['shots']
            self.assertIn('kneels beside cold hearth ashes', person['prompt'])
            self.assertNotIn('close-up face', person['negative_prompt'])
            self.assertNotIn('wide scene', person['prompt'])
            self.assertNotIn('caveman', objects['prompt'])
            self.assertIn('people, person, face, portrait', objects['negative_prompt'])
            self.assertNotIn('people, person, face, portrait', person['negative_prompt'])
            with patch('image_cpu.generate') as generate:
                w.make_image(person['prompt'], root/'sample.png')
            self.assertEqual(generate.call_args.args[0], person['prompt'])

    def test_fresh_run_uses_explainer_and_keyword_contract(self):
        calls = []
        def ask(endpoint, payload):
            calls.append(payload)
            props = payload['response_format']['json_schema']['schema']['properties']
            if 'scenes' in props:
                self.assertEqual(props['thumbnail_text'], h.THUMBNAIL_SCHEMA)
                result = dict(title='How Ancient Humans Kept Their Fire Alive',
                    description='Educational overview with illustrative reconstructions and uncertainty.',
                    tags=['Ancient Humans'], thumbnail_text='What happens when the fire goes out?',
                    thumbnail_prompt='A worried cartoon person beside cold embers',
                    character_description='Cream oval head, ochre tunic, blue wrist tie',
                    protagonist_name='Ari', story_bible='Illustrative camp; time and region unspecified; avoid precise claims.',
                    scenes={key: dict(summary='Explain the problem', image_prompt='Cold embers beside a shelter',
                        continuity_note='Same camp', image_prompts=['Embers cooling', 'Dry kindling'])
                        for key in props['scenes']['required']})
            elif 'narrations' in props:
                result = {'narrations': {key: ' '.join(__import__('hashlib').sha256(f'{key}-{i}'.encode()).hexdigest()[:12] for i in range(80)) + '.'
                    for key in props['narrations']['required']}}
            else:
                from test_video_metadata import metadata_fixture
                result = metadata_fixture()
                # Reproduce production: completed narration followed by malformed SEO tags.
                result['tags'] = ['#AncientHumans', ' ancient humans ', 'fire maintenance'] * 9
            return {'choices': [{'message': {'content': json.dumps(result)}, 'finish_reason': 'stop'}]}
        with patch.dict(os.environ, {}, clear=True), patch.object(w, 'request_text', side_effect=ask), \
                patch.object(w.time, 'sleep'):
            story = w.make_story('daily-123', [{'format': 'human_history_explainer'}])
        self.assertEqual(story['content_profile'], h.PROFILE)
        self.assertEqual(len(calls), 6)
        from video_metadata import validate_metadata
        validate_metadata(story)
        self.assertEqual(story['thumbnail_text'], h.THUMBNAIL_FALLBACKS[story['content_pillar']])
        self.assertTrue(story['scenes'][-1]['narration'].endswith(h.CTA))
        w.validate_story(story)
        invalid = copy.deepcopy(story)
        invalid['title'] = 'How Fire Changed Everything'
        with self.assertRaisesRegex(ValueError, 'title must contain'):
            w.validate_story(invalid)
        invalid['title'] = 'How Humans Kept Their Fire Alive'
        w.validate_story(invalid)

    def test_duration_rewrite_preserves_explainer_direction_and_cta(self):
        from long_video import rewrite_for_duration
        story = dict(content_profile=h.PROFILE, content_pillar='fire', title='How Ancient Humans Kept Fire',
            description='Educational overview', tags=[], thumbnail_text='FIRE GONE?', thumbnail_prompt='Embers',
            character_description='A cartoon stick figure', story_bible='Evidence is uncertain.',
            scenes=[dict(narration='A fire can cool before the camp returns. '*11, image_prompt='Embers') for _ in range(20)])
        story['scenes'][-1]['narration'] += h.CTA
        def ask(endpoint, payload):
            self.assertIn('educational human-history explainer', payload['messages'][0]['content'])
            keys = payload['response_format']['json_schema']['schema']['required']
            return {'choices': [{'message': {'content': json.dumps({key: 'A fire cools gradually. '*20 for key in keys})}}]}
        revised, _ = rewrite_for_duration(story, 1200, [60]*20, ask=ask)
        self.assertTrue(revised['scenes'][-1]['narration'].endswith(h.CTA))


if __name__ == '__main__':
    unittest.main()
