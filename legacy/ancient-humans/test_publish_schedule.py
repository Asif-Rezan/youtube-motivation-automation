import unittest
from unittest.mock import MagicMock
from publish_schedule import first_publish_time, schedule_verified

class ScheduleTests(unittest.TestCase):
    def test_first_six_am_after_full_24_hours(self):
        self.assertEqual(first_publish_time('2026-10-27T09:59:00Z'), '2026-10-28T10:00:00Z')
        self.assertEqual(first_publish_time('2026-10-27T10:01:00Z'), '2026-10-29T10:00:00Z')
        self.assertEqual(first_publish_time('2026-10-27T10:00:00Z'), '2026-10-28T10:00:00Z')

    def test_dst_uses_24_elapsed_hours_and_local_six_am(self):
        self.assertEqual(first_publish_time('2027-03-13T11:00:00Z'), '2027-03-15T10:00:00Z')
        self.assertEqual(first_publish_time('2026-10-31T10:00:00Z'), '2026-11-01T11:00:00Z')
        with self.assertRaises(ValueError):
            first_publish_time('2026-10-27T10:00:00')

    def test_retry_recognizes_existing_schedule_without_update(self):
        state = {'video_id': 'v', 'schedule_requested': True, 'publish_at': '2099-01-01T11:00:00Z'}
        client, store = MagicMock(), MagicMock()
        client.videos().list().execute.return_value = {'items': [{'status': {
            'privacyStatus': 'private', 'publishAt': state['publish_at']}}]}
        schedule_verified(client, state, store, 'key')
        client.videos().update.assert_not_called()
        self.assertTrue(state['schedule_verified'])

    def test_updates_only_status_preserving_disclosures(self):
        state = {'video_id': 'v', 'schedule_requested': True, 'uploaded_at': '2098-12-30T11:01:00Z'}
        client, store = MagicMock(), MagicMock()
        status = {'privacyStatus': 'private', 'containsSyntheticMedia': True, 'selfDeclaredMadeForKids': False}
        client.videos().list().execute.side_effect = [
            {'items': [{'status': status}]},
            {'items': [{'status': dict(status, publishAt='2099-01-01T11:00:00Z')}]}]
        schedule_verified(client, state, store, 'key')
        body = client.videos().update.call_args.kwargs['body']
        self.assertTrue(body['status']['containsSyntheticMedia'])
        self.assertEqual(body['status']['publishAt'], '2099-01-01T11:00:00Z')

    def test_legacy_upload_untouched(self):
        client = MagicMock()
        schedule_verified(client, {}, MagicMock(), 'key')
        client.videos.assert_not_called()


class ScheduleReceiptTests(unittest.TestCase):
    def test_update_response_confirms_omitted_list_schedule(self):
        state = {'video_id': 'v', 'schedule_requested': True, 'uploaded_at': '2098-12-30T11:01:00Z'}
        client, store = MagicMock(), MagicMock()
        client.videos().list().execute.return_value = {'items': [{'status': {'privacyStatus': 'private'}}]}
        client.videos().update().execute.return_value = {'id': 'v', 'status': {
            'privacyStatus': 'private', 'publishAt': '2099-01-01T11:00:00.000Z'}}
        schedule_verified(client, state, store, 'key')
        self.assertTrue(state['schedule_verified'])
        client.videos().update.reset_mock()
        schedule_verified(client, state, store, 'key')
        client.videos().update.assert_not_called()

    def test_missing_list_and_unconfirmed_update_fails(self):
        state = {'video_id': 'v', 'schedule_requested': True, 'uploaded_at': '2098-12-30T11:01:00Z'}
        client = MagicMock()
        client.videos().list().execute.return_value = {'items': [{'status': {'privacyStatus': 'private'}}]}
        client.videos().update().execute.return_value = {'id': 'v', 'status': {'privacyStatus': 'private'}}
        with self.assertRaisesRegex(RuntimeError, 'schedule verification failed'):
            schedule_verified(client, state, MagicMock(), 'key')
