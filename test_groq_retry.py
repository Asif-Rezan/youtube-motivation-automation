import os
import sys
import types
import unittest
from unittest.mock import Mock, patch
import workflow as w


def response(status=429, headers=None, code='rate_limit_exceeded', message=''):
    result = Mock(ok=status == 200, status_code=status, headers=headers or {})
    result.json.return_value = {'error': {'code': code, 'message': message}} if status != 200 else {'choices': []}
    result.content = b'audio'
    return result


class GroqRetryTests(unittest.TestCase):
    def setUp(self):
        # Exercise HTTP response handling without real network calls.
        fake = types.ModuleType('requests')
        fake.post = Mock()
        modules = patch.dict(sys.modules, {'requests': fake})
        modules.start()
        self.addCleanup(modules.stop)

    def test_provider_delays_and_multiple_rejections_then_success(self):
        replies = [response(headers={'retry-after': '90.5'}), response(headers={'retry-after': '2'}), response(200)]
        with patch.dict(os.environ, {'GROQ_API_KEY': 'test'}), \
             patch('requests.post', side_effect=replies) as post, patch.object(w.time, 'sleep') as sleep:
            self.assertEqual(w.request_groq('chat/completions', {}), {'choices': []})
        self.assertEqual(post.call_count, 3)
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [92, 3])

    def test_daily_quota_does_not_loop_or_sleep_past_budget(self):
        reply = response(headers={'retry-after': '3600'})
        with patch.dict(os.environ, {'GROQ_API_KEY': 'test'}), \
             patch('requests.post', return_value=reply) as post, patch.object(w.time, 'sleep') as sleep:
            with self.assertRaisesRegex(RuntimeError, 'organization quotas'):
                w.request_groq('chat/completions', {})
        post.assert_called_once()
        sleep.assert_not_called()

    def test_missing_or_invalid_header_uses_bounded_backoff(self):
        with patch.dict(os.environ, {'GROQ_API_KEY': 'test'}), \
             patch('requests.post', return_value=response(headers={'retry-after': 'invalid'})) as post, \
             patch.object(w.time, 'sleep') as sleep:
            with self.assertRaisesRegex(RuntimeError, 'retry budget exhausted'):
                w.request_groq('chat/completions', {})
        self.assertEqual(post.call_count, 5)
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [60, 120, 240, 300, 300][:len(sleep.call_args_list)])
        self.assertLessEqual(sum(c.args[0] for c in sleep.call_args_list), 900)

    def test_date_and_error_message_cooldowns(self):
        with patch.object(w.time, 'time', return_value=0):
            self.assertEqual(w.groq_retry_delay(response(headers={'retry-after': 'Thu, 01 Jan 1970 00:02:00 GMT'}), 0), 121)
        self.assertEqual(w.groq_retry_delay(response(message='Please try again in 2m3.5s.'), 0), 125)
        self.assertEqual(w.groq_retry_delay(response(message='Please try again in 500ms.'), 0), 2)

    def test_auth_failure_is_not_retried_and_binary_success_unchanged(self):
        with patch.dict(os.environ, {'GROQ_API_KEY': 'test'}), \
             patch('requests.post', return_value=response(401)) as post, patch.object(w.time, 'sleep') as sleep:
            with self.assertRaisesRegex(RuntimeError, 'HTTP 401'):
                w.request_groq('chat/completions', {})
            post.assert_called_once()
            sleep.assert_not_called()
        with patch.dict(os.environ, {'GROQ_API_KEY': 'test'}), patch('requests.post', return_value=response(200)) as post:
            self.assertEqual(w.request_groq('audio/speech', {}, binary=True), b'audio')
            post.assert_called_once()
