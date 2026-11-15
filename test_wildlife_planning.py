import unittest
from dataclasses import asdict, replace
from unittest.mock import patch

from wildlife.episodes import GOATS, GOAT_PACKAGING
from wildlife.generate import build
from wildlife.render import plan_episode
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
            scene['visual'] = f'Wide view of the forest edge from position {index}.'
            scenes.append(scene)
        store = MemoryStore()
        episode = 'auto-2026-11-15'
        with patch('wildlife.generate.ask', side_effect=[idea] + [
                {'scenes': scenes[i:i+4]} for i in range(0,20,4)]) as request:
            manifest = build(episode, store)
            self.assertEqual(build(episode, store), manifest)
        self.assertEqual(request.call_count, 6)
        self.assertEqual(manifest['idea']['thumbnail_text'], 'THE GREEN VANISHES')
        package, beats, timeline = plan_episode(episode, False, manifest)
        self.assertEqual(len(beats), 20)
        self.assertTrue(600 <= sum(chapter['seconds'] for chapter in timeline) <= 900)
        self.assertEqual(package.build(timeline)['title'],
                         'Deer on an Island: What If Their Food Starts to VANISH?')
