import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from PIL import Image
import workflow as w


class Checks(unittest.TestCase):

    def test_global_ten_second_timeline(self):
        from long_video import shot_plan
        story = {'scenes': [{'image_prompt': 'first chapter'}, {'image_prompt': 'second chapter'}]}
        plan = shot_plan(story, [330.5, 280])
        self.assertEqual(len(plan['shots']), 62)
        self.assertEqual([s['start'] for s in plan['shots']], list(range(0, 620, 10)))
        self.assertTrue(all(s['duration'] == 10 for s in plan['shots'][:-1]))
        self.assertEqual(plan['shots'][-1]['duration'], .5)
        self.assertEqual(plan['shots'][33]['chapter'], 0)
        self.assertEqual(plan['shots'][34]['chapter'], 1)

    def test_actual_ten_second_image_change(self):
        from long_video import picture_clip
        import subprocess
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for i, color in enumerate(((230, 20, 20), (20, 20, 230))):
                Image.new('RGB', (640, 360), color).save(root/f'{i}.png')
                picture_clip(root/f'{i}.png', 10, root/f'{i}.mp4')
                self.assertAlmostEqual(w.duration(root/f'{i}.mp4'), 10, places=2)
            (root/'list.txt').write_text("file '0.mp4'\nfile '1.mp4'\n")
            w.shell('ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(root/'list.txt'),
                '-c', 'copy', str(root/'joined.mp4'))
            def pixel(at):
                return subprocess.check_output(['ffmpeg', '-v', 'error', '-ss', str(at),
                    '-i', str(root/'joined.mp4'), '-frames:v', '1', '-s', '1x1',
                    '-pix_fmt', 'rgb24', '-f', 'rawvideo', 'pipe:1'])
            before, after = pixel(9), pixel(11)
            self.assertGreater(before[0], before[2])
            self.assertGreater(after[2], after[0])

    def test_music_is_present_and_balanced(self):
        from long_video import mix_audio
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            w.shell('ffmpeg', '-y', '-f', 'lavfi', '-i',
                'sine=frequency=220:duration=5', str(root/'voice.wav'))
            w.shell('ffmpeg', '-y', '-f', 'lavfi', '-i',
                'sine=frequency=660:duration=2', str(root/'music.wav'))
            result = mix_audio(root/'voice.wav', root/'music.wav', root/'mix.wav', 5)
            self.assertTrue(result['music_audibility_passed'])
            self.assertTrue(5 < result['music_gap_db'] < 22)
            self.assertAlmostEqual(w.duration(root/'mix.wav'), 5, places=1)
            w.shell('ffmpeg', '-y', '-f', 'lavfi', '-i',
                'anullsrc=r=24000:cl=stereo', '-t', '2', str(root/'silent.wav'))
            with self.assertRaisesRegex(RuntimeError, 'inaudible'):
                mix_audio(root/'voice.wav', root/'silent.wav', root/'bad.wav', 5)

    def test_closing_cta_is_required(self):
        from long_video import validate_engagement
        story = {'character_description': 'a young carpenter in a blue coat',
            'scenes': [{'narration': 'Like this story, comment with your next step, and subscribe.'}]}
        validate_engagement(story)
        story['scenes'][0]['narration'] = 'Thank you for watching.'
        with self.assertRaisesRegex(ValueError, 'like, comment, and subscribe'):
            validate_engagement(story)

    def test_time_rounding(self):
        self.assertEqual(w.timestamp(59.9996), '00:01:00,000')

    def test_speech_input_limit(self):
        text = 'A small daily step can rebuild your confidence. ' * 30
        chunks = w.speech_chunks(text)
        self.assertTrue(all(0 < len(c) <= 200 for c in chunks))
        self.assertEqual(' '.join(chunks), ' '.join(text.split()))
        with self.assertRaises(ValueError):
            w.speech_chunks('x' * 201)

    def test_daily_gate(self):
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'disabled'):
                w.run(daily=True)

    def test_missing_credentials(self):
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'GROQ_API_KEY'):
                w.preflight()

    def test_free_drive_quota_guard(self):
        store = w.Store.__new__(w.Store)
        store.client = MagicMock()
        query = store.client.about.return_value.get.return_value.execute
        query.return_value = {'storageQuota': {'limit': str(15*1024**3), 'usage': '0'}}
        store.check_quota(1024)
        query.return_value['storageQuota']['usage'] = str(15*1024**3 - 50*1024**2)
        with self.assertRaisesRegex(RuntimeError, 'Free storage'):
            store.check_quota(1024)
        query.return_value = {'storageQuota': {'usage': '0'}}
        with self.assertRaisesRegex(RuntimeError, 'Cannot verify'):
            store.check_quota(1024)

    def test_shared_drive_file_rejected(self):
        store = w.Store.__new__(w.Store)
        store.client = MagicMock()
        query = store.client.permissions.return_value.list.return_value.execute
        query.return_value = {'permissions': [{'type': 'user', 'role': 'owner'}]}
        store.check_private('folder')
        query.return_value['permissions'].append({'type': 'anyone', 'role': 'reader'})
        with self.assertRaisesRegex(RuntimeError, 'private'):
            store.check_private('folder')

    def test_story_validation(self):
        story = dict(title='The Last Step', description='An original fictional story.', tags=['motivation'],
                     thumbnail_text='ONE MORE STEP', thumbnail_prompt='A determined runner',
                     scenes=[dict(narration=' '.join(['word']*450), image_prompt='cinematic road') for _ in range(4)])
        self.assertEqual(w.validate_story(story), story)
        story['title'] = 'x'*101
        with self.assertRaises(ValueError):
            w.validate_story(story)

    def test_aligned_captions(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'captions.srt'
            w.aligned_subtitles([[dict(word='Keep', start=0.2, end=0.5), dict(word='going', start=0.6, end=1.2)]], [2], path)
            self.assertIn('00:00:00,200 --> 00:00:01,200', path.read_text())
            with self.assertRaises(ValueError):
                w.aligned_subtitles([[dict(word='Bad',start=1,end=4)]],[2],path)

    def test_real_hd_render(self):
        # Synthetic test fixtures only; this is not the requested AI story test.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            Image.new('RGB', (1344,768), (25,40,60)).save(root/'image.png')
            w.shell('ffmpeg','-y','-f','lavfi','-i','sine=frequency=440:duration=2',str(root/'audio.wav'))
            length = w.render_scene(root/'image.png',root/'audio.wav',root/'clip.mp4')
            self.assertAlmostEqual(length, 2, places=1)
            metadata = w.check_video(root/'clip.mp4', min_duration=1, max_duration=900)
            self.assertEqual(metadata['streams'][0]['width'],1920)
            with self.assertRaises(AssertionError):
                w.check_video(root/'clip.mp4')


if __name__ == '__main__':
    unittest.main()
