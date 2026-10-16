import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import long_video as video
import workflow as w


class DurationRecoveryTests(unittest.TestCase):
    def test_duration_boundaries(self):
        expected = {580: 'rewrite', 600: 'accept', 840: 'accept',
                    900: 'accept', 904.3: 'tempo', 1000: 'rewrite', 1200: 'rewrite'}
        for seconds, action in expected.items():
            with self.subTest(seconds=seconds):
                self.assertEqual(video.duration_action(seconds), action)

    def test_tempo_scales_words_captions_and_seven_second_shots(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            audio = root/'narration-00.wav'
            audio.write_bytes(b'original')
            words = [{'word': 'opening', 'start': 0, 'end': 7},
                     {'word': 'ending', 'start': 897, 'end': 904.3}]
            def fake_shell(*args):
                Path(args[-1]).write_bytes(b'adjusted')
            with patch.object(video.w, 'shell', side_effect=fake_shell), \
                 patch.object(video.w, 'duration', return_value=895):
                lengths, aligned, factor = video.adjust_tempo(root, [audio], [904.3], [words], 904.3)
            self.assertLess(factor, 1.02)
            self.assertEqual(lengths, [895])
            self.assertAlmostEqual(aligned[0][-1]['end'], 895)
            w.aligned_subtitles(aligned, lengths, root/'captions.srt')
            self.assertIn('00:14:55,000', (root/'captions.srt').read_text())
            plan = video.shot_plan({'scenes': [{'narration': 'opening ending'}]}, lengths, aligned)
            self.assertEqual([s['start'] for s in plan['shots']], list(range(0, 895, 7)))
            self.assertEqual(plan['shots'][-1]['duration'], 6)
            self.assertEqual(json.loads((root/'words-00.json').read_text()), aligned[0])

    def test_rewrite_preserves_final_cta(self):
        scenes = [{'narration': ' '.join(['event']*83), 'image_prompt': 'A scene'} for _ in range(20)]
        scenes[-1]['narration'] += w.FINAL_CTA
        story = {'title': 'A Choice', 'description': 'Fiction', 'tags': [],
                 'thumbnail_text': 'THE CHOICE', 'thumbnail_prompt': 'A choice',
                 'character_description': 'woman in a blue coat', 'scenes': scenes}
        def ask(endpoint, payload):
            keys = payload['response_format']['json_schema']['schema']['required']
            return {'choices': [{'message': {'content': json.dumps({key: ' '.join(['new']*70)
                                                              for key in keys})}}]}
        revised, changed = video.rewrite_for_duration(story, 1200, [60]*20, ask=ask)
        self.assertGreater(len(changed), 0)
        self.assertLess(len(changed), 20)
        self.assertTrue(revised['scenes'][-1]['narration'].endswith(w.FINAL_CTA))
        self.assertEqual(story['scenes'][0]['narration'].split()[0], 'event')

    def test_small_overrun_rewrites_only_selected_chapters(self):
        scenes = [{'narration': ' '.join(['event']*83), 'image_prompt': 'A scene'} for _ in range(20)]
        scenes[-1]['narration'] += w.FINAL_CTA
        story = {'title': 'A Choice', 'description': 'Fiction', 'tags': [],
                 'thumbnail_text': 'THE CHOICE', 'thumbnail_prompt': 'A choice',
                 'character_description': 'woman in a blue coat', 'scenes': scenes}
        def ask(endpoint, payload):
            keys = payload['response_format']['json_schema']['schema']['required']
            return {'choices': [{'message': {'content': json.dumps({key: ' '.join(['new']*70)
                                                              for key in keys})}}]}
        revised, changed = video.rewrite_for_duration(story, 940, [47]*20, ask=ask)
        self.assertLess(len(changed), 10)
        self.assertTrue(revised['scenes'][-1]['narration'].endswith(w.FINAL_CTA))
        self.assertEqual(revised['scenes'][10], story['scenes'][10])

    def test_prepare_recovers_904_seconds_before_storyboard(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            story = {'scenes': [{'narration': 'A short event.'}]}
            audio = root/'narration-00.wav'
            initial = ([904.3], [[{'word': 'event', 'start': 0, 'end': 904.3}]], [audio])
            corrected = ([895], [[{'word': 'event', 'start': 0, 'end': 895}]], [audio])
            def fake_shell(*args):
                (root/'narration.wav').write_bytes(b'joined')
            with patch.object(video.w, 'validate_story'), \
                 patch.object(video, 'measure_chapters', side_effect=[initial, corrected]) as measure, \
                 patch.object(video, 'adjust_tempo', return_value=(corrected[0], corrected[1], 1.0104)) as adjust, \
                 patch.object(video.w, 'shell', side_effect=fake_shell):
                plan = video.prepare(story, root)
            self.assertEqual(measure.call_count, 2)
            adjust.assert_called_once()
            self.assertEqual(plan['duration_seconds'], 895)
            self.assertEqual(plan['shots'][-1]['duration'], 6)
            self.assertIn('00:14:55,000', (root/'captions.srt').read_text())

    def test_changed_text_invalidates_audio_and_alignment_cache(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            audio = root/'narration-00.wav'
            words = root/'words-00.json'
            digest = root/'narration-00.sha256'
            audio.write_bytes(b'old')
            words.write_text(json.dumps([{'word': 'old', 'start': 0, 'end': 1}]))
            digest.write_text(video.narration_digest('old words'))
            generated = []
            def make(text, path):
                generated.append(text)
                path.write_bytes(b'new')
            with patch.object(video.w, 'make_narration', side_effect=make), \
                 patch.object(video.w, 'duration', return_value=2), \
                 patch.object(video.w, 'transcribe', return_value=[{'word': 'new', 'start': 0, 'end': 1}]):
                result = video.measure_chapters({'scenes': [{'narration': 'new words'}]}, root)
            self.assertEqual(generated, ['new words'])
            self.assertEqual(result[1][0][0]['word'], 'new')
            self.assertEqual(digest.read_text(), video.narration_digest('new words'))


if __name__ == '__main__':
    unittest.main()
