import json
import unittest
from unittest.mock import MagicMock, patch
import workflow


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        self.store = workflow.Store.__new__(workflow.Store)
        self.store.client = MagicMock()
        self.store.folder = 'folder'
        self.store.check_private = MagicMock()
        self.store.check_quota = MagicMock()
        self.store.find = MagicMock(return_value='existing-id')
        self.media = MagicMock()
        self.modules = patch.dict('sys.modules', {'googleapiclient.http': MagicMock(MediaIoBaseUpload=self.media)})
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.sleep = patch('workflow.time.sleep')
        self.sleep.start()
        self.addCleanup(self.sleep.stop)

    def test_update_timeout_retries_only_same_file_id(self):
        execute = self.store.client.files().update().execute
        execute.side_effect = [TimeoutError(), {}]
        self.store.client.files().update.reset_mock()
        self.store.save('runs/daily-1/cleanup.json', {'deleted': ['a']})
        self.assertEqual(execute.call_count, 2)
        for call in self.store.client.files().update.call_args_list:
            self.assertEqual(call.kwargs['fileId'], 'existing-id')
        self.store.client.files().create.assert_not_called()
        self.assertTrue(all(not c.kwargs['resumable'] for c in self.media.call_args_list))

    def test_ambiguous_create_reuses_allocated_id(self):
        self.store.find.return_value = None
        self.store.client.files().generateIds().execute.return_value = {'ids': ['new-id']}
        conflict = RuntimeError('conflict')
        conflict.resp = type('Response', (), {'status': 409})()
        self.store.client.files().create().execute.side_effect = [TimeoutError(), conflict]
        self.store.client.files().get_media().execute.return_value = json.dumps({'deleted': []}).encode()
        self.store.client.files().create.reset_mock()
        self.store.save('runs/daily-1/cleanup.json', {'deleted': []})
        self.assertEqual(self.store.client.files().create.call_count, 2)
        self.assertEqual({c.kwargs['body']['id'] for c in self.store.client.files().create.call_args_list}, {'new-id'})
        self.store.client.files().update.assert_not_called()

    def test_retries_bounded_and_permission_errors_not_retried(self):
        execute = self.store.client.files().update().execute
        execute.side_effect = TimeoutError()
        with self.assertRaises(TimeoutError):
            self.store.save('history.json', [])
        self.assertEqual(execute.call_count, 5)
        error = RuntimeError('permission')
        error.resp = type('Response', (), {'status': 403})()
        execute.reset_mock()
        execute.side_effect = error
        with self.assertRaises(RuntimeError):
            self.store.save('history.json', [])
        self.assertEqual(execute.call_count, 1)

    def test_media_create_timeout_retries_with_one_id(self):
        self.store.find.return_value = None
        self.store.client.files().generateIds().execute.return_value = {'ids': ['fixed-id']}
        self.store.client.files().get().execute.side_effect = RuntimeError('not found yet')
        execute = self.store.client.files().create().execute
        execute.side_effect = [TimeoutError(), {'id': 'fixed-id'}]
        self.store.client.files().create.reset_mock()
        self.store.put('runs/daily-1/shot-001.png', object(), 123)
        self.assertEqual(execute.call_count, 2)
        self.assertEqual({c.kwargs['body']['id'] for c in self.store.client.files().create.call_args_list}, {'fixed-id'})

    def test_media_timeout_after_success_is_reconciled(self):
        self.store.find.return_value = None
        self.store.client.files().generateIds().execute.return_value = {'ids': ['fixed-id']}
        self.store.client.files().create().execute.side_effect = TimeoutError()
        self.store.client.files().get().execute.return_value = {
            'id': 'fixed-id', 'size': '123', 'parents': ['folder'],
            'appProperties': {'workflow_key': workflow.hashlib.sha256(b'asset').hexdigest()}}
        self.store.put('asset', object(), 123)
        self.assertEqual(self.store.client.files().create().execute.call_count, 1)
