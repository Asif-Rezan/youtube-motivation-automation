"""Reproduce a successful insert followed by temporarily stale YouTube metadata."""
import copy
import unittest
from unittest.mock import MagicMock, patch
from reliability import ProcessingPending
from workflow import wait_for_upload_metadata


class UploadPropagationTests(unittest.TestCase):
    def setUp(self):
        self.story = {'title': 'Ancient Humans and Fire', 'description': 'Exact completed description', 'tags': ['Ancient Humans', 'fire']}
        self.state = {'video_id': 'known', 'upload_description': self.story['description']}
        self.remote = {'id': 'known', 'snippet': {'channelId': 'c', **self.story},
                       'status': {'privacyStatus': 'private', 'uploadStatus': 'processed'}}

    def check(self, responses, attempts=3):
        client = MagicMock()
        client.videos().list().execute.side_effect = responses
        with patch.dict('os.environ', {'EXPECTED_CHANNEL_ID': 'c'}), patch('workflow.time.sleep') as sleep:
            result = wait_for_upload_metadata(client, self.story, self.state, attempts)
        client.videos().insert.assert_not_called()
        client.videos().update.assert_not_called()
        return result, sleep.call_count

    def test_stale_metadata_after_insert_converges_without_mutation(self):
        stale = copy.deepcopy(self.remote)
        stale['snippet'].update(title='', description='', tags=[])
        result, sleeps = self.check([{'items': [stale]}, {'items': [self.remote]}])
        self.assertEqual(result, self.remote)
        self.assertEqual(sleeps, 1)

    def test_temporarily_missing_video_can_be_read_later(self):
        result, sleeps = self.check([{'items': []}, {'items': [self.remote]}])
        self.assertEqual(result['id'], 'known')
        self.assertEqual(sleeps, 1)

    def test_permanent_mismatch_is_bounded_and_preserves_saved_identity(self):
        stale = copy.deepcopy(self.remote)
        stale['snippet']['tags'] = []
        original = copy.deepcopy(self.state)
        with self.assertRaisesRegex(ProcessingPending, 'tags'):
            self.check([{'items': [stale]}] * 3)
        self.assertEqual(self.state, original)

    def test_wrong_identity_or_public_video_fails_immediately(self):
        for section, field, value in [('snippet', 'channelId', 'other'), ('status', 'privacyStatus', 'public')]:
            wrong = copy.deepcopy(self.remote)
            wrong[section][field] = value
            with self.assertRaises(RuntimeError):
                self.check([{'items': [wrong]}])
