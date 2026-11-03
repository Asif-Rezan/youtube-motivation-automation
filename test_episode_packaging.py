import copy
import unittest
from unittest.mock import patch
from episode_packaging import VERSION,source_identity,validate_package,generate_package,public_metadata


def fixture_package(song,anchor=0):
    title=song['title'][:65]+' | Kids Dance Song'
    return dict(version=VERSION,source_sha256=source_identity(song),
        title_candidates=[title,'Baby Animal Friends | Nursery Rhyme','Dreamy Garden Play | Kids Song'],
        video=dict(title=title,description=song['description']+' Sing and dance with the actual baby animal friends. Original AI-generated music and illustrations.',
            tags=['kids dance song','nursery rhyme','baby animal song','garden song','Dudi Dam TV']),
        shorts=dict(title='Baby Animal Garden Dance | Kids Song #Shorts',
            description='Sing along with the baby animal friends in this short garden dance. Original AI-generated music and illustrations.',
            tags=['kids dance song','nursery rhyme','baby animals','garden dance','Shorts']),
        thumbnail=dict(scene_index=anchor,focus='The same smiling toddlers and baby animals share the scene prop with joyful expressions.'))


class EpisodePackagingTests(unittest.TestCase):
    def song(self):
        from test_prepare_original_lyrics import fixture_song
        return fixture_song()

    def test_generated_packaging_is_based_on_episode_facts_and_reused(self):
        song=self.song()
        with patch('rhyme_writer.request_json',return_value=fixture_package(song)) as model:
            package=generate_package(song)
        prompt=model.call_args.args[1]
        self.assertIn(song['story_summary'],prompt)
        self.assertIn(song['scenes'][0]['lyric'],prompt)
        self.assertIn('first 40 seconds',prompt)
        self.assertIn('No invented animals',prompt)
        song['packaging']=package
        self.assertEqual(public_metadata(song),package['video'])
        self.assertEqual(public_metadata(song,'shorts'),package['shorts'])
        model.assert_called_once()

    def test_different_story_generates_different_public_metadata(self):
        first=self.song();second=copy.deepcopy(first);second['title']='Tiny Turtles Discover a Stream'
        first['packaging']=fixture_package(first);second['packaging']=fixture_package(second)
        self.assertNotEqual(public_metadata(first),public_metadata(second))

    def test_stale_or_invalid_packages_never_reach_upload(self):
        song=self.song();package=fixture_package(song)
        for mutate in (lambda p:p.update(source_sha256='stale'),
                       lambda p:p['thumbnail'].update(scene_index=999),
                       lambda p:p['video'].update(tags=['spam']*6),
                       lambda p:p['video'].update(title='Not a candidate')):
            bad=copy.deepcopy(package);mutate(bad)
            with self.assertRaises(Exception):validate_package(bad,song)

    def test_invalid_semantic_output_retries_then_reports_safe_failure(self):
        from lyrics_cpu import StoryGenerationError
        song=self.song();bad=fixture_package(song)
        bad['video']['tags']=['x'*40+str(i) for i in range(15)]
        with patch('rhyme_writer.request_json',return_value=bad) as model:
            with self.assertRaises(StoryGenerationError):generate_package(song)
        self.assertEqual(model.call_count,3)
