import os
import sys
import types
import unittest
from unittest.mock import Mock, patch
import workflow as w


def reply(status):
    return types.SimpleNamespace(ok=status==200,status_code=status,headers={'retry-after':'3600'},
        content=b'audio',json=lambda:{'choices':[]} if status==200 else {'error':{'code':'rate_limit_exceeded'}})


class GroqBackupTests(unittest.TestCase):
    def setUp(self):
        for context in [patch.dict(os.environ, {'GROQ_API_KEY':'primary','GROQ_API_KEY_BACKUP':'backup','GEMINI_API_KEY':'must-not-use'}, clear=True),
                        patch.object(w,'_groq_backup_active',False)]:
            context.start(); self.addCleanup(context.stop)
        self.requests=types.ModuleType('requests'); self.requests.post=Mock()
        modules=patch.dict(sys.modules,{'requests':self.requests}); modules.start();self.addCleanup(modules.stop)

    def test_switch_and_keep_backup_without_sleep_or_gemini(self):
        self.requests.post.side_effect=[reply(429),reply(200),reply(200)]
        with patch.object(w.time,'sleep') as sleep:
            for _ in range(2):self.assertEqual(w.request_groq('chat/completions',{}),{'choices':[]})
        self.assertEqual([c.kwargs['headers']['Authorization'] for c in self.requests.post.call_args_list],
                         ['Bearer primary','Bearer backup','Bearer backup'])
        self.assertTrue(all(c.args[0].startswith('https://api.groq.com/') for c in self.requests.post.call_args_list))
        sleep.assert_not_called()

    def test_primary_success_does_not_use_backup(self):
        self.requests.post.return_value=reply(200)
        w.request_groq('chat/completions',{})
        self.requests.post.assert_called_once()
        self.assertFalse(w._groq_backup_active)

    def test_auth_or_server_error_uses_backup(self):
        for status in (401,403,500,502,503,504):
            with self.subTest(status=status):
                w._groq_backup_active=False
                self.requests.post.reset_mock();self.requests.post.side_effect=[reply(status),reply(200)]
                w.request_groq('chat/completions',{})
                self.assertEqual(self.requests.post.call_count,2)

    def test_validation_error_does_not_switch_keys(self):
        self.requests.post.return_value=reply(400)
        with self.assertRaisesRegex(RuntimeError,'HTTP 400'):w.request_groq('chat/completions',{})
        self.assertFalse(w._groq_backup_active)

    def test_both_keys_limited_stops_within_budget(self):
        self.requests.post.return_value=reply(429)
        with patch.object(w.time,'sleep') as sleep:
            with self.assertRaisesRegex(RuntimeError,'rate limit remains active'):w.request_groq('chat/completions',{})
        self.assertEqual(self.requests.post.call_count,2)
        sleep.assert_not_called()

    def test_binary_response_can_use_backup(self):
        self.requests.post.side_effect=[reply(429),reply(200)]
        self.assertEqual(w.request_groq('audio/speech',{},binary=True),b'audio')

    def test_primary_connection_failure_uses_backup(self):
        self.requests.post.side_effect=[TimeoutError('offline'),reply(200)]
        self.assertEqual(w.request_groq('chat/completions',{}),{'choices':[]})
        self.assertTrue(w._groq_backup_active)
