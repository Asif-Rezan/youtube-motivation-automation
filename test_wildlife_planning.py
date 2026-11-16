import unittest
from dataclasses import asdict, replace
from unittest.mock import patch

from wildlife.episodes import GOATS, GOAT_PACKAGING
from wildlife.generate import build
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
            'tags':['Earth','planet rings','orbital science','what if'],
            'thumbnail_text':'RINGS OVER EARTH',
            'premise':'A ring appears around Earth and its shadow changes over time.',
            'arc':'Show the rings from orbit, then examine their moving shadow and possible seasonal effects.',
        }
        batch = []
        for beat in GOATS[:4]:
            scene = asdict(beat)
            scene['forage_percent'] = round(scene.pop('forage') * 20) * 5
            scene['population'] = 0
            scene['narration'] = ' '.join(['Example'] * 75) + '.'
            scene['visual'] = 'Wide view of Earth and the orbital ring system.'
            batch.append(scene)
        store = MemoryStore()
        episode = 'auto-2026-11-16'
        with patch('wildlife.generate.select_topic',return_value=(
                'space','rings','Earth','What if Earth had rings?',False)), patch(
                'wildlife.generate.ask',side_effect=[idea]+[{'scenes':batch}]*5):
            manifest = build(episode,store)
        self.assertEqual(manifest['idea']['domain'],'space')
        self.assertNotIn('species',manifest['idea'])
        package, beats, timeline = plan_episode(episode,False,manifest)
        self.assertEqual(len(beats),20)
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
            scene['narration'] = ' '.join(['Example'] * 75) + '.'
            scene['visual'] = 'Wide view of the forest edge in the evening.'
            if index in (0, 8, 9):
                scene['label'] = 'The herd grows'
            scenes.append(scene)
        store = MemoryStore()
        episode = 'auto-2026-11-15'
        with patch('wildlife.generate.select_topic',return_value=(
                'wildlife','bridge','Deer','What if a land bridge opened?',False)), patch(
                'wildlife.generate.ask',side_effect=[idea]+[
                    {'scenes':scenes[i:i+4]} for i in range(0,20,4)]) as request:
            manifest = build(episode, store)
            self.assertEqual(build(episode, store), manifest)
        self.assertEqual(request.call_count, 6)
        self.assertEqual(manifest['idea']['thumbnail_text'], 'THE GREEN VANISHES')
        package, beats, timeline = plan_episode(episode, False, manifest)
        self.assertEqual(len(beats), 20)
        self.assertEqual(beats[0].label, 'The herd grows')
        self.assertEqual(len({beat.label.casefold() for beat in beats}), 20)
        self.assertTrue(beats[8].label.startswith('The herd grows ('))
        self.assertTrue(600 <= sum(chapter['seconds'] for chapter in timeline) <= 900)
        self.assertEqual(package.build(timeline)['title'],
                         'Deer on an Island: What If Their Food Starts to VANISH?')
