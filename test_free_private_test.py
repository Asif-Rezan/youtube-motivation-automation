import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

import free_private_test as private
import workflow as w


class PrivateTestDurationTests(unittest.TestCase):
    def test_short_duration_bounds_preserve_daily_defaults(self):
        for seconds in (179, 180, 270, 600, 601):
            metadata = {'format': {'duration': str(seconds)}, 'streams': [
                {'codec_type': 'video', 'width': 1920, 'height': 1080},
                {'codec_type': 'audio'}]}
            with self.subTest(seconds=seconds), patch.object(w, 'probe', return_value=metadata), \
                 patch.object(w, 'shell'):
                if 180 <= seconds <= 600:
                    self.assertEqual(private.check_test_video(Path('video.mp4')), metadata)
                else:
                    with self.assertRaisesRegex(AssertionError, 'Duration'):
                        private.check_test_video(Path('video.mp4'))
                if seconds < 600:
                    with self.assertRaisesRegex(AssertionError, 'Duration'):
                        w.check_video(Path('video.mp4'))

    def test_render_uses_short_test_validation(self):
        story = {'scenes': [{'narration': 'A scene.', 'image_prompt': 'A scene.'}] * 4,
                 'thumbnail_prompt': 'A scene.'}
        def make_image(prompt, path):
            Image.new('RGB', (16, 9)).save(path)
        with tempfile.TemporaryDirectory() as temp, patch.object(private, 'ROOT', Path(temp)), \
             patch.object(w, 'validate_story', return_value=story), \
             patch('music_cpu.generate'), patch.object(w, 'make_narration'), \
             patch.object(w, 'transcribe', return_value=[{'word': 'scene', 'start': 0, 'end': 1}]), \
             patch.object(w, 'make_image', side_effect=make_image), \
             patch.object(w, 'render_scene', return_value=60), \
             patch.object(w, 'shell'), \
             patch.object(w, 'check_video', return_value={'format': {'duration': '240'}}) as check:
            private.render()
            check.assert_called_once_with(Path(temp)/'video.mp4', min_duration=180, max_duration=600)
            self.assertTrue(json.loads((Path(temp)/'validation.json').read_text())['render_passed'])

    def test_upload_uses_short_test_validation(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(private, 'ROOT', Path(temp)), \
             patch.object(w, 'check_video') as check, patch.object(w, 'Store') as store, \
             patch.object(w, 'upload_private') as upload:
            root = Path(temp)
            (root/'validation.json').write_text(json.dumps({'render_passed': True}))
            (root/'story.json').write_text(json.dumps({'title': 'Test', 'scenes': [{'narration': 'Test'}]}))
            store.return_value.load.side_effect = [{}, []]
            def finish(video, thumbnail, story, state, *args):
                state.update(video_id='test-id', processing_status='succeeded')
            upload.side_effect = finish
            private.upload()
            check.assert_called_once_with(root/'video.mp4', min_duration=180, max_duration=600)

    def test_restore_uses_short_test_validation(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(private, 'ROOT', Path(temp)), \
             patch.object(w, 'check_video') as check, patch.object(w, 'Store') as store:
            store.return_value.load.return_value = {'phase': 'rendered', 'validation': {'render_passed': True}}
            private.restore()
            check.assert_called_once_with(Path(temp)/'video.mp4', min_duration=180, max_duration=600)
            self.assertEqual(store.return_value.download.call_count, 6)


if __name__ == '__main__':
    unittest.main()
