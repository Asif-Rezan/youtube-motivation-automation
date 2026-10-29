import errno
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from reliability import retry, transient, atomic_text


def http_error(status, reason):
    error = RuntimeError('private-sensitive-details')
    error.resp = type('Response', (), {'status': status})()
    error.content = json.dumps({'error': {'errors': [{'reason': reason}]}}).encode()
    return error


class RetryTests(unittest.TestCase):
    def test_transient_network_and_rate_limits_retry_but_not_auth_quota_or_disk(self):
        for error in (TimeoutError(), ConnectionError(), http_error(503, 'backendError'),
                      http_error(403, 'userRateLimitExceeded')):
            operation = MagicMock(side_effect=[error, 'ok'])
            with patch('reliability.time.sleep'):
                self.assertEqual(retry(operation, 'test'), 'ok')
            self.assertEqual(operation.call_count, 2)
        for error in (ValueError('invalid'), http_error(401, 'unauthorized'),
                      http_error(403, 'insufficientPermissions'), http_error(403, 'quotaExceeded'),
                      OSError(errno.ENOSPC, 'disk full')):
            operation = MagicMock(side_effect=error)
            with self.assertRaises(type(error)), patch('reliability.time.sleep') as sleep:
                retry(operation, 'test')
            self.assertEqual(operation.call_count, 1)
            sleep.assert_not_called()

    def test_retries_stop_at_budget_and_logs_do_not_include_private_error(self):
        operation = MagicMock(side_effect=TimeoutError('PRIVATE TOKEN'))
        with patch('reliability.time.sleep') as sleep, patch('builtins.print') as output:
            with self.assertRaises(TimeoutError):
                retry(operation, 'test', attempts=3)
        self.assertEqual(operation.call_count, 3)
        self.assertEqual(sleep.call_count, 2)
        self.assertNotIn('PRIVATE TOKEN', str(output.call_args_list))

    def test_atomic_checkpoint_keeps_old_file_if_replace_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'words.json'
            path.write_text('old complete data')
            with patch.object(Path, 'replace', side_effect=OSError(errno.ENOSPC, 'full')):
                with self.assertRaises(OSError):
                    atomic_text(path, 'new data')
            self.assertEqual(path.read_text(), 'old complete data')
            self.assertFalse(path.with_name(path.name+'.partial').exists())
            atomic_text(path, 'new complete data')
            self.assertEqual(path.read_text(), 'new complete data')


class DownloadTests(unittest.TestCase):
    def test_download_restarts_partial_transfer_and_replaces_only_when_complete(self):
        import workflow
        store = workflow.Store.__new__(workflow.Store)
        store.client, store.check_private = MagicMock(), MagicMock()
        attempts = []
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'video.mp4'
            path.write_bytes(b'old complete video')
            class Transfer:
                def __init__(self, stream, request):
                    self.stream = stream
                    attempts.append(self)
                def next_chunk(self, **kwargs):
                    if len(attempts) == 1:
                        self.stream.write(b'partial')
                        self.stream.flush()
                        self.assert_old()
                        raise TimeoutError('temporary')
                    self.stream.write(b'new complete video')
                    return None, True
                def assert_old(self):
                    if path.read_bytes() != b'old complete video':
                        raise AssertionError('Partial download replaced valid asset')
            with patch('googleapiclient.http.MediaIoBaseDownload', Transfer), patch('reliability.time.sleep'):
                store.download('known-file', path)
            self.assertEqual(path.read_bytes(), b'new complete video')
            self.assertEqual(len(attempts), 2)
            self.assertFalse(path.with_name(path.name+'.partial').exists())


class KnownUploadTests(unittest.TestCase):
    def run_case(self, state, channel='c'):
        import workflow
        story = {'title': 'T', 'description': 'D', 'tags': ['tag']}
        client, store = MagicMock(), MagicMock()
        client.channels().list().execute.return_value = {'items': [{'id': 'c'}]}
        client.videos().list().execute.side_effect = [
            {'items': [{'snippet': {'channelId': channel, **story}, 'status': {'privacyStatus': 'private'}}]},
            {'items': [{'status': {'privacyStatus': 'private', 'uploadStatus': 'processed'},
                        'processingDetails': {'processingStatus': 'succeeded'}}]}]
        client.thumbnails().set().execute.side_effect = [TimeoutError(), {}]
        client.videos().insert.reset_mock()
        with patch.dict('os.environ', {'YOUTUBE_TOKEN_JSON': '{}', 'EXPECTED_CHANNEL_ID': 'c'}), \
             patch('google.oauth2.credentials.Credentials.from_authorized_user_info', return_value=MagicMock()), \
             patch('googleapiclient.discovery.build', return_value=client), \
             patch('googleapiclient.http.MediaFileUpload'), patch('reliability.time.sleep'):
            if channel != 'c' or state.get('phase') == 'upload_started':
                with self.assertRaises(RuntimeError):
                    workflow.upload_private(None, Path('thumbnail.jpg'), story, state, store, 'key')
            else:
                workflow.upload_private(None, Path('thumbnail.jpg'), story, state, store, 'key')
                self.assertEqual(state['phase'], 'complete')
                self.assertTrue(state['thumbnail_uploaded'])
                self.assertEqual(client.thumbnails().set().execute.call_count, 2)
        client.videos().insert.assert_not_called()
        return client

    def test_thumbnail_timeout_resumes_known_video_without_inserting_again(self):
        self.run_case({'phase': 'uploaded', 'video_id': 'v', 'thumbnail_uploaded': False})

    def test_wrong_channel_and_ambiguous_insertion_never_insert(self):
        client = self.run_case({'phase': 'uploaded', 'video_id': 'v'}, channel='other')
        client.thumbnails().set().execute.assert_not_called()
        self.run_case({'phase': 'upload_started'})


class PartialShardTests(unittest.TestCase):
    def test_only_complete_qa_passed_shots_are_saved_after_partial_failure(self):
        import long_video
        store = MagicMock()
        plan = {'image_interval_seconds': 7, 'shots': [{'index': 0}, {'index': 20}]}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'plan.json').write_text(json.dumps(plan))
            for index in (0, 20):
                (root/f'shot-{index:03}.png').write_bytes(b'image')
                (root/f'shot-{index:03}.qa.json').write_text(json.dumps({'passed': True, 'source_signature': 'sig'}))
            (root/'shot-000.mp4').write_bytes(b'clip')
            with patch.object(long_video, 'ROOT', root), patch('workflow.Store', return_value=store), \
                 patch('scene_check.scene_signature', return_value='sig'):
                long_video.save_shard(0)
        self.assertEqual(store.upload.call_count, 3)
        self.assertTrue(all('shot-000.' in call.args[1] for call in store.upload.call_args_list))


class InsertionSafetyTests(unittest.TestCase):
    def test_generic_retry_refuses_video_or_drive_create(self):
        from reliability import api_execute
        for uri in ('https://youtube.googleapis.com/upload/youtube/v3/videos?uploadType=resumable',
                    'https://www.googleapis.com/drive/v3/files'):
            request = MagicMock(method='POST', uri=uri)
            with self.assertRaisesRegex(ValueError, 'Non-idempotent'):
                api_execute(request)
            request.execute.assert_not_called()


class StoryboardResumeTests(unittest.TestCase):
    def test_second_batch_network_error_does_not_repeat_completed_first_batch(self):
        import long_video
        requests = []
        def ask(endpoint, payload):
            keys = payload['response_format']['json_schema']['schema']['required']
            requests.append(keys)
            if len(requests) == 2:
                raise TimeoutError('temporary network failure')
            return {'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps({
                key: 'An adult tends glowing embers beside a sheltered stone hearth' for key in keys})}}]}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'story.json').write_text(json.dumps({'title': 'Ancient Humans Fire',
                'character_description': 'An adult in hide clothing', 'scenes': [{'narration': 'An adult tends embers.'}]}))
            (root/'plan.json').write_text(json.dumps({'shots': [
                {'index': i, 'start': i*7, 'duration': 7, 'chapter': 0, 'narration': 'An adult tends embers.'}
                for i in range(9)]}))
            with patch('reliability.time.sleep'):
                result = retry(lambda: long_video.storyboard(root, ask=ask, pause=lambda _: None), 'storyboard', attempts=2)
        self.assertTrue(result['storyboard_verified'])
        self.assertEqual(len(requests), 3)
        self.assertEqual(sum('shot_000' in keys for keys in requests), 1)


class RestorePartialShotsTests(unittest.TestCase):
    def test_only_matching_complete_cached_shots_are_restored(self):
        import long_video
        from image_cpu import metadata_path
        store = MagicMock()
        store.find.side_effect = lambda key: key if 'shot-000.' in key else None
        def download(fid, path):
            if str(path).endswith('qa.json'):
                path.write_text(json.dumps({'passed': True, 'source_signature': 'sig',
                    'image_generation': {'model': 'segmind/SSD-1B'}}))
            else:
                path.write_bytes(b'complete cached asset')
        store.download.side_effect = download
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch('scene_check.scene_signature', return_value='sig'):
                long_video.restore_cached_shots(store, root, {'shots': [{'index': 0}, {'index': 20}]}, 0)
            self.assertTrue((root/'shot-000.mp4').exists())
            self.assertFalse((root/'shot-020.mp4').exists())
            self.assertEqual(json.loads(metadata_path(root/'shot-000.png').read_text())['model'], 'segmind/SSD-1B')
        self.assertEqual(store.download.call_count, 3)


class CaptionRecoveryTests(unittest.TestCase):
    def test_corrupt_word_cache_rebuilds_alignment_without_regenerating_audio(self):
        import long_video
        import workflow
        narration = 'An adult tends embers.'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'narration-00.wav').write_bytes(b'existing audio')
            (root/'narration-00.sha256').write_text(long_video.narration_digest(narration))
            (root/'words-00.json').write_text('{partial json')
            timings = [{'word': 'embers', 'start': 0.0, 'end': 1.0}]
            with patch.object(workflow, 'make_narration') as generate, \
                 patch.object(workflow, 'duration', return_value=1.0), \
                 patch.object(workflow, 'transcribe', return_value=timings) as transcribe:
                long_video.measure_chapters({'scenes': [{'narration': narration}]}, root)
            generate.assert_not_called()
            transcribe.assert_called_once()
            self.assertEqual(json.loads((root/'words-00.json').read_text()), timings)


class CleanupFinalizationRecoveryTests(unittest.TestCase):
    def test_cleanup_only_can_finish_thumbnail_for_known_uploaded_id(self):
        import daily_publish
        state = {'phase': 'uploaded', 'video_id': 'v', 'thumbnail_uploaded': False,
                 'hash': 'h', 'story': {'title': 'T', 'description': 'D', 'tags': []}}
        store, client = MagicMock(), MagicMock()
        store.load.side_effect = [state, []]
        store.find.return_value = 'saved-thumbnail'
        store.download.side_effect = lambda fid, path: path.write_bytes(b'complete thumbnail')
        client.videos().list().execute.return_value = {'items': [{'id': 'v',
            'snippet': {'channelId': 'c', 'title': 'T', 'description': 'D', 'tags': []},
            'status': {'privacyStatus': 'private', 'uploadStatus': 'processed'},
            'processingDetails': {'processingStatus': 'succeeded'}, 'contentDetails': {'definition': 'hd'}}]}
        def finish(*args):
            self.assertEqual(args[3]['video_id'], 'v')
            state.update(phase='complete', thumbnail_uploaded=True)
        with patch.dict('os.environ', {'SAVED_RUN_ID': 'daily-123', 'YOUTUBE_TOKEN_JSON': '{}', 'EXPECTED_CHANNEL_ID': 'c'}), \
             patch('workflow.Store', return_value=store), \
             patch('google.oauth2.credentials.Credentials.from_authorized_user_info', return_value=MagicMock()), \
             patch('googleapiclient.discovery.build', return_value=client), \
             patch('workflow.finalize_uploaded', side_effect=finish) as finalizer, patch('daily_publish.cleanup') as cleanup:
            daily_publish.main()
        finalizer.assert_called_once()
        cleanup.assert_called_once()
        client.videos().insert.assert_not_called()


class ResumeIdentityTests(unittest.TestCase):
    def test_resume_rejects_wrong_or_mismatched_run_identity(self):
        import long_video
        for requested, saved in [('daily-123', 'daily-456'), ('not-a-daily-run', 'not-a-daily-run')]:
            with patch.dict('os.environ', {'RESUME_DAILY_RUN': requested, 'SAVED_RUN_ID': saved}):
                with self.assertRaisesRegex(ValueError, 'exact original'):
                    long_video.run_id()
        with patch.dict('os.environ', {'RESUME_DAILY_RUN': 'daily-123', 'SAVED_RUN_ID': 'daily-123'}):
            self.assertEqual(long_video.run_id(), 'daily-123')
