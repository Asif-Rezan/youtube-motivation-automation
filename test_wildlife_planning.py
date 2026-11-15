import unittest
from dataclasses import asdict, replace
from unittest.mock import patch

from wildlife.episodes import GOATS, GOAT_PACKAGING
from wildlife.generate import build
from wildlife.render import plan_episode
from wildlife.whatif import ACTIVE_DOMAINS, TOPICS, select_topic
from wildlife.metadata import emphasize_title


class MemoryStore:
    def __init__(self):
        self.data = {}

    def load(self, key, default):
        return self.data.get(key, default)

    def save(self, key, value):
        self.data[key] = value


class WildlifePlanningTests(unittest.TestCase):
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

    def test_space_plan_round_trip_contains_no_wildlife_fields(self):
        idea = {
            'title':'Earth With Rings: Can Its Seasons SURVIVE?',
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
        self.assertEqual(package.build(timeline)['title'],idea['title'])

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
