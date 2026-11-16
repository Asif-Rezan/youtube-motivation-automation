import unittest
from dataclasses import asdict, replace
from unittest.mock import patch

from lyrics_cpu import StoryGenerationError
from wildlife.episodes import GOATS, GOAT_PACKAGING
from wildlife.generate import build, validate_opening
from wildlife.render import plan_episode
from wildlife.whatif import ACTIVE_DOMAINS, TOPICS, select_topic
from wildlife.metadata import emphasize_title, thumbnail_hook, validate_title


class MemoryStore:
    def __init__(self):
        self.data = {}

    def load(self, key, default):
        return self.data.get(key, default)

    def save(self, key, value):
        self.data[key] = value


class WildlifePlanningTests(unittest.TestCase):
    def test_edits_use_story_time_and_compare_the_final_scene_to_the_start(self):
        from wildlife.editing import scene_edit
        from wildlife.publication import is_generated
        from wildlife.thumbnail import episode_cue

        beats = list(GOATS)
        beats[1] = replace(beats[1], narration='Week three begins with a surge in new grass.')
        self.assertEqual(scene_edit(beats, 1, 30)['text'], 'WEEK THREE')
        self.assertLessEqual(len(scene_edit(beats, len(beats)//2, 30)['text'].split()), 4)
        self.assertEqual(scene_edit(beats, len(beats)-1, 30)['compare_to'], 0)
        for episode in ('auto-2026-11-16', 'auto-2026-11-16-43806880042'):
            self.assertTrue(is_generated(episode))
            self.assertEqual(episode_cue(episode), episode_cue('auto-2026-11-16'))

    def test_opening_requires_an_early_question_and_skips_greetings(self):
        validate_opening('The river changed course overnight. What happens to the wetland it left behind?')
        with self.assertRaisesRegex(ValueError, 'greeting'):
            validate_opening('Welcome back. What happens when a river changes course?')
        with self.assertRaisesRegex(ValueError, '34 spoken words'):
            validate_opening('One ' * 34 + 'What happens next?')

    def test_cover_uses_a_distinct_supported_hook(self):
        idea = {
            'topic': 'rivers',
            'title': 'Rivers Change Course: Can a Wetland SURVIVE?',
            'arc': 'Follow the old riverbed across 10 years of change.',
            'thumbnail_text': '10 YEARS LATER',
        }
        self.assertEqual(thumbnail_hook(idea), '10 YEARS LATER')
        for rejected in ('20 YEARS LATER', 'RIVERS CHANGE COURSE', 'WHAT HAPPENS NEXT'):
            with self.subTest(rejected=rejected):
                self.assertEqual(thumbnail_hook({**idea, 'thumbnail_text': rejected}),
                                 'THE OLD BED DRIES')

    def test_metadata_includes_the_rendered_chapters_and_topic_search_phrases(self):
        package = replace(
            GOAT_PACKAGING, subject='Rivers',
            title='Rivers Change Course: Can a Wetland SURVIVE?',
            opening='Rivers can leave wetlands behind when a channel shifts.',
            premise='A river leaves its old course after a flood.',
            tags=('rivers and wetlands', 'stream flow', 'wetland hydrology', 'river habitat'),
            topic='rivers',
        )
        metadata = package.build([
            {'start': 0, 'chapter': 'The flood'},
            {'start': 17.8, 'chapter': 'A new route'},
            {'start': 82.6, 'chapter': 'The wetland'},
        ])
        self.assertTrue(metadata['description'].startswith(package.premise))
        self.assertIn('0:00 The flood\n0:17 A new route\n1:22 The wetland', metadata['description'])
        self.assertIn('Background reading\nUSGS', metadata['description'])
        self.assertTrue(metadata['description'].endswith('#simulation #rivers #ecology #whatif #animation'))
        self.assertEqual(metadata['tags'][:2], ['river changes course', 'wetland hydrology'])
        self.assertEqual(metadata['tags'].count('wetland hydrology'), 1)

    def test_production_fields_are_excluded_from_spoken_copy(self):
        from wildlife.narration import spoken_text

        text = ('Birds look for food. Forage percent drops to 30. Population zero. '
                'Marsh floor darkens with sediment. Aerial view shows flooded patches. '
                'Camera: aerial. Action: walk. Visual: Dark mud. '
                'Visual cues still help birds find food. The population rises as birds return.')
        self.assertEqual(
            spoken_text(text),
            'Birds look for food. Marsh floor darkens with sediment. '
            'Visual cues still help birds find food. The population rises as birds return.')
        self.assertEqual(
            spoken_text('Forage is scarce. The population reached 40 birds.'),
            'Forage is scarce. The population reached 40 birds.')

    def test_episode_visuals_use_scene_descriptions_and_episode_specific_seeds(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from PIL import Image
        from wildlife.render import generate_scene_illustration

        manifest = {
            'episode': 'auto-2026-11-16-123',
            'idea': {'species': 'deer', 'habitat': 'wooded island'},
            'scenes': [
                {'visual': 'Rain collects in a small pool under ferns.', 'camera': 'pasture'},
                {'visual': 'A footpath winds along a clifftop.', 'camera': 'aerial'},
            ],
        }

        def draw_image(prompt, target, **options):
            Image.new('RGB', (options['width'], options['height'])).save(target)

        with TemporaryDirectory() as directory, patch('image_cpu.generate', side_effect=draw_image) as generate:
            target = Path(directory) / 'scene.png'
            generate_scene_illustration(manifest, 0, target)
            generate_scene_illustration(manifest, 1, target)
            generate_scene_illustration({**manifest, 'episode': 'auto-2026-11-16-456'}, 0, target)
        first, second, other_episode = generate.call_args_list
        self.assertIn('pool under ferns', first.args[0])
        self.assertIn('clifftop', second.args[0])
        self.assertEqual(len({call.kwargs['seed'] for call in (first, second, other_episode)}), 3)

    def test_tidal_marsh_renders_bird_motion_and_a_visible_change_in_waterline(self):
        from PIL import ImageChops
        from wildlife.science_visuals import science_frames
        from wildlife.tidal_marsh import landscape

        beat = replace(GOATS[0], camera='shore', forage=.2)
        frames = list(science_frames((320,180), beat, 1, 4, domain='ocean', topic='tides'))
        self.assertEqual(len(frames), 4)
        self.assertIsNotNone(ImageChops.difference(frames[0], frames[-1]).getbbox())
        _, low_waterline, _ = landscape('shore', .2)
        _, high_waterline, _ = landscape('shore', .8)
        self.assertGreater(high_waterline[20][1] - low_waterline[20][1], 200)

    def test_tag_repair_for_tides_reserves_room_for_the_subject(self):
        from wildlife.metadata import normalize_generated_tags, tag_cost

        candidates = [' tidal marsh ecology ', 'TIDAL MARSH ECOLOGY', 'high tide and marsh birds',
                      'estuary habitat', 'marsh food web', 'oversize ' * 70]
        candidates.extend(f'coastal marsh search phrase {index}' for index in range(20))
        tags = normalize_generated_tags(candidates, 'Tides')
        self.assertEqual(tags[:3], ['Tides what if', 'tidal marsh ecology', 'high tide and marsh birds'])
        self.assertEqual(len({tag.casefold() for tag in tags}), len(tags))
        self.assertLessEqual(len(tags), 12)
        self.assertLessEqual(sum(map(tag_cost, tags)) + len(tags) - 1, 500)
        self.assertEqual(normalize_generated_tags(tags, 'Tides'), tags)

    def test_ecosystem_upload_has_english_education_and_audience_metadata(self):
        from upload_settings import load_settings, upload_body

        body = upload_body({'title': GOAT_PACKAGING.title}, 'Episode synopsis',
                           ['island ecology'], load_settings(wildlife=True))
        self.assertEqual(body['snippet']['categoryId'], '27')
        self.assertEqual(load_settings(wildlife=True, domain='wildlife')['category_id'], '15')
        self.assertEqual(load_settings(wildlife=True, domain='ocean')['category_id'], '27')
        self.assertEqual(body['snippet']['defaultLanguage'], 'en')
        self.assertEqual(body['snippet']['defaultAudioLanguage'], 'en')
        self.assertIs(body['status']['selfDeclaredMadeForKids'], False)
        self.assertIs(body['paidProductPlacementDetails']['hasPaidProductPlacement'], False)

    def test_power_word_is_required_and_can_be_recovered_from_the_premise(self):
        with self.assertRaisesRegex(ValueError, 'uppercase power word'):
            replace(GOAT_PACKAGING, title=GOAT_PACKAGING.title.replace('SURVIVE', 'survive')).validate()
        self.assertEqual(emphasize_title('What Happens to Deer?', 'deer', 'habitat recovery'),
                         'Deer on an Island: Can Their Habitat RECOVER?')

    def test_what_if_categories_rotate_without_revisiting_used_topics(self):
        history = []
        for _ in range(sum(len(TOPICS[domain]) for domain in ACTIVE_DOMAINS)):
            domain, topic, _, _, reused = select_topic(history, 4)
            self.assertFalse(reused)
            history.append({'domain':domain,'topic':topic})
        self.assertEqual({row['domain'] for row in history[:len(ACTIVE_DOMAINS)]},set(ACTIVE_DOMAINS))
        self.assertTrue(select_topic(history,4)[-1])

    def test_all_non_wildlife_topics_repair_titles_without_power_words(self):
        for domain, topics in TOPICS.items():
            if domain == 'wildlife':
                continue
            for topic, subject, _ in topics:
                with self.subTest(topic=topic):
                    title = emphasize_title(f'{subject}: What Happens Next?',subject,topic=topic)
                    validate_title(title,subject)

    def test_space_plan_round_trip_contains_no_wildlife_fields(self):
        idea = {
            'title':'Earth With Rings: Would the Seasons Change?',
            'opening':'Imagine Earth with a bright ring system and watch how its shadows move through the year.',
            'description':'A hypothetical view of what a new planetary ring could change.',
            'tags':['planet rings','orbital science','planetary shadows','what if'],
            'thumbnail_text':'RINGS OVER EARTH',
            'premise':'A ring appears around Earth and its shadow changes over time.',
            'arc':'Show the rings from orbit, then examine their moving shadow and possible seasonal effects.',
        }
        batch = []
        for beat in GOATS[:1]:
            scene = asdict(beat)
            scene['forage_percent'] = round(scene.pop('forage') * 20) * 5
            scene['population'] = 0
            scene['narration'] = 'What happens to the seasons? ' + ' '.join(['Example'] * 75) + '.'
            scene['visual'] = 'Wide view of Earth and the orbital ring system.'
            batch.append(scene)
        store = MemoryStore()
        episode = 'auto-2026-11-16'
        with patch('wildlife.generate.select_topic',return_value=(
                'space','rings','Earth','What if Earth had rings?',False)), patch(
                'wildlife.generate.ask',side_effect=[idea]+[{'scenes':batch}]*20):
            manifest = build(episode,store)
        self.assertEqual(manifest['idea']['domain'],'space')
        self.assertNotIn('species',manifest['idea'])
        self.assertEqual(manifest['idea']['tags'][0], 'Earth what if')
        package, beats, timeline = plan_episode(episode,False,manifest)
        self.assertEqual(len(beats),20)
        self.assertIn('text', timeline[0]['edit'])
        self.assertGreaterEqual(sum('text' in chapter['edit'] for chapter in timeline), 17)
        self.assertEqual(package.build(timeline)['title'],'Earth Gets Rings: Can Its Seasons SURVIVE?')

    def test_ai_plan_keeps_a_full_runtime_and_reuses_the_same_episode_on_retry(self):
        idea = {
            'species': 'deer', 'habitat': 'wooded island', 'pressure': 'vegetation loss',
            'title': 'Deer on an Island: What If Their Food Starts to Vanish?',
            'opening': 'Follow the deer as browsing changes the mix of plants on one wooded island.',
            'description': 'An illustrative story about woodland recovery and pressure from browsing.',
            'tags': ['woodland deer', 'wildlife simulation', 'island ecology', 'browsing pressure'],
            'thumbnail_prompt': 'A pair of deer beside a sunlit forest clearing and open blue sky.',
            'thumbnail_text': 'This accidental caption is too long for the thumbnail.',
            'arc': 'Deer multiply, the forest thins, and surviving patches begin to recover.',
        }
        scenes = []
        for index, beat in enumerate(GOATS):
            scene = asdict(beat)
            scene['forage_percent'] = round(scene.pop('forage') * 20) * 5
            scene['narration'] = 'Where will the deer find shelter? ' + ' '.join(['Example'] * 75) + '.'
            scene['visual'] = 'Wide view of the forest edge in the evening.'
            if index in (0, 8, 9):
                scene['label'] = 'The herd grows'
            scenes.append(scene)
        # A valid script should survive unusable caption/background lengths in scene 7.
        scenes[6]['label'] = '<>'
        scenes[6]['visual'] = ' '
        scenes[7]['label'] = 'A long descriptive caption ' * 5
        scenes[7]['visual'] = 'Overhead view of the surrounding forest and clearings. ' * 8
        store = MemoryStore()
        episode = 'auto-2026-11-15'
        truncated = StoryGenerationError(
            'Incomplete model output', details={'constraint': 'incomplete_output'}, retryable=True)
        completions = [idea, truncated, *({'scenes': [scene]} for scene in scenes)]
        with patch('wildlife.generate.select_topic',return_value=(
                'wildlife','bridge','Deer','What if a land bridge opened?',False)), patch(
                'wildlife.generate.ask',side_effect=completions) as request:
            manifest = build(episode, store)
            self.assertEqual(build(episode, store), manifest)
        self.assertEqual(request.call_count, 22)
        initial, retry, second = request.call_args_list[1:4]
        self.assertEqual(initial.args[1]['properties']['scenes']['maxItems'], 1)
        self.assertIn('incomplete_output', retry.args[0])
        self.assertNotEqual(initial.args[2], retry.args[2])
        self.assertIn(scenes[0]['label'], second.args[0])
        self.assertEqual(manifest['idea']['thumbnail_text'], 'THE GREEN VANISHES')
        package, beats, timeline = plan_episode(episode, False, manifest)
        self.assertEqual(len(beats), 20)
        self.assertEqual(beats[0].label, 'The herd grows')
        self.assertEqual(beats[6].label, 'Scene 7')
        self.assertEqual(beats[6].narration, scenes[6]['narration'])
        self.assertEqual(beats[6].camera, scenes[6]['camera'])
        self.assertLessEqual(len(beats[7].label), 45)
        for index in (6, 7):
            self.assertTrue(24 <= len(manifest['scenes'][index]['visual']) <= 220)
        self.assertEqual(len({beat.label.casefold() for beat in beats}), 20)
        self.assertTrue(beats[8].label.startswith('The herd grows ('))
        self.assertTrue(600 <= sum(chapter['seconds'] for chapter in timeline) <= 900)
        self.assertEqual(package.build(timeline)['title'],
                         'Deer on an Island: What If Their Food Starts to VANISH?')
