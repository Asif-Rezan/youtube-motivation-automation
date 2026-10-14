import hashlib
import unittest
from unittest.mock import MagicMock
from daily_publish import cleanup, disposable, validate_remote


class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.store = MagicMock()
        self.run = 'daily-123'
        self.state = {'phase': 'published', 'video_id': 'video', 'verification': {
            'video_id': 'video', 'hd': True, 'processed': True, 'metadata': True, 'public': True}}
        self.entry = {'id': 'file', 'name': 'runs__daily-123__video.mp4', 'parents': ['folder'],
            'mimeType': 'video/mp4', 'appProperties': {'automation_run': self.run,
                'disposable': 'v1', 'workflow_key': hashlib.sha256(b'runs/daily-123/video.mp4').hexdigest()}}
        self.store.folder = 'folder'
        self.store.load.return_value = {'run': self.run, 'video_id': 'video', 'files': [self.entry], 'deleted': []}
        self.store.client.files().get().execute.return_value = self.entry

    def test_failed_and_incomplete_uploads_never_delete(self):
        for phase in ('prepared', 'upload_started', 'uploaded', 'complete'):
            with self.assertRaises(RuntimeError):
                cleanup(self.store, self.run, dict(self.state, phase=phase))
        self.store.client.files().delete.assert_not_called()

    def test_missing_hd_or_metadata_never_deletes(self):
        for flag in ('hd', 'metadata', 'processed', 'public'):
            state = dict(self.state, verification=dict(self.state['verification'], **{flag: False}))
            with self.assertRaises(RuntimeError):
                cleanup(self.store, self.run, state)
        self.store.client.files().delete.assert_not_called()

    def test_unrelated_moved_or_essential_file_rejected(self):
        for edit in ({'parents': ['other']}, {'name': 'runs__daily-123__state.json'},
                     {'appProperties': {'automation_run': 'daily-999'}}):
            self.store.client.files().get().execute.return_value = dict(self.entry, **edit)
            with self.assertRaises(ValueError):
                cleanup(self.store, self.run, self.state)
        self.store.client.files().delete.assert_not_called()

    def test_success_deletes_only_exact_manifest_id_and_is_idempotent(self):
        cleanup(self.store, self.run, self.state)
        self.store.client.files().delete.assert_called_once_with(fileId='file')
        cleanup(self.store, self.run, self.state)
        self.store.client.files().delete.assert_called_once_with(fileId='file')

    def test_already_deleted_id_is_checkpointed(self):
        error = RuntimeError('gone')
        error.resp = type('Response', (), {'status': 404})()
        self.store.client.files().get().execute.side_effect = error
        cleanup(self.store, self.run, self.state)
        self.assertTrue(self.store.load.return_value['complete'])
        self.store.client.files().delete.assert_not_called()

    def test_preserves_essential_data(self):
        for name in ('state.json', 'story.json', 'history.json', 'config.json', 'token.json', 'validation.json'):
            self.assertFalse(disposable(name))
        self.assertTrue(disposable('shot-123.qa.json'))

    def test_metadata_and_hd_gate(self):
        state = {'video_id': 'v', 'story': {'title': 'Title', 'tags': ['money'], 'description': 'Fiction'}}
        video = {'id': 'v', 'snippet': {'channelId': 'c', 'title': 'Title', 'tags': ['money'], 'description': 'Fiction\nCredit'},
                 'status': {'uploadStatus': 'processed'}, 'processingDetails': {'processingStatus': 'succeeded'},
                 'contentDetails': {'definition': 'sd'}}
        self.assertFalse(validate_remote(video, state, 'c'))
        video['contentDetails']['definition'] = 'hd'
        self.assertTrue(validate_remote(video, state, 'c'))
        with self.assertRaises(RuntimeError):
            validate_remote(video, state, 'wrong-channel')
