import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
import workflow as w


class Checks(unittest.TestCase):
    def test_time_rounding(self):
        self.assertEqual(w.timestamp(59.9996), '00:01:00,000')

    def test_daily_gate(self):
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'disabled'):
                w.run(daily=True)

    def test_missing_credentials(self):
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'GROQ_API_KEY'):
                w.preflight()

    def test_story_validation(self):
        story = dict(title='The Last Step', description='An original fictional story.', tags=['motivation'],
                     thumbnail_text='ONE MORE STEP', thumbnail_prompt='A determined runner',
                     scenes=[dict(narration=' '.join(['word']*130), image_prompt='cinematic road') for _ in range(4)])
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
            metadata = w.check_video(root/'clip.mp4', min_duration=1)
            self.assertEqual(metadata['streams'][0]['width'],1920)
            with self.assertRaises(AssertionError):
                w.check_video(root/'clip.mp4')


if __name__ == '__main__':
    unittest.main()
