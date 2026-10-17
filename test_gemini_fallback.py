import json
import os
import sys
import types
import unittest
from unittest.mock import Mock, patch
import workflow as w

PAYLOAD = {'messages': [{'role':'system','content':'Return JSON.'}, {'role':'user','content':'Return ok true.'}],
           'max_completion_tokens':128, 'response_format':{'type':'json_schema','json_schema':{'schema':{
               'type':'object','properties':{'ok':{'type':'boolean'}},'required':['ok'],'additionalProperties':False}}}}


def reply(status=200, text='{"ok": true}', reason='STOP'):
    return types.SimpleNamespace(ok=status==200,status_code=status,headers={},json=lambda: {
        'candidates':[{'finishReason':reason,'content':{'parts':[{'thought':True,'text':'hidden'}, {'text':text}]}}]})


class GeminiFallbackTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'GROQ_API_KEY':'test','GEMINI_API_KEY':'test'}, clear=True)
        self.env.start(); self.addCleanup(self.env.stop)
        self.mod = types.ModuleType('requests'); self.mod.post = Mock()
        self.modules = patch.dict(sys.modules, {'requests':self.mod})
        self.modules.start(); self.addCleanup(self.modules.stop)
        self.active = patch.object(w,'_gemini_fallback_active',False)
        self.active.start(); self.addCleanup(self.active.stop)
        self.last = patch.object(w,'_gemini_last_request',None)
        self.last.start(); self.addCleanup(self.last.stop)

    def test_429_switches_to_gemini_and_stays_for_process(self):
        self.mod.post.side_effect = [reply(429), reply(), reply()]
        with patch.object(w.time,'sleep') as sleep:
            result = w.request_groq('chat/completions',PAYLOAD)
            again = w.request_groq('chat/completions',PAYLOAD)
        self.assertEqual(json.loads(result['choices'][0]['message']['content']), {'ok':True})
        self.assertEqual(result,again)
        calls = self.mod.post.call_args_list
        self.assertIn('api.groq.com',calls[0].args[0])
        self.assertTrue(all('generativelanguage.googleapis.com' in c.args[0] for c in calls[1:]))
        body = calls[1].kwargs['json']
        self.assertEqual(body['generationConfig']['responseJsonSchema'],PAYLOAD['response_format']['json_schema']['schema'])
        self.assertEqual(body['systemInstruction']['parts'],[{'text':'Return JSON.'}])
        self.assertGreaterEqual(body['generationConfig']['maxOutputTokens'], 16384)
        self.assertEqual(body['generationConfig']['thinkingConfig'], {'thinkingLevel':'low'})
        sleep.assert_called_once()  # Gemini pacing, not a Groq cooldown.

    def test_success_and_auth_errors_do_not_use_fallback(self):
        good = types.SimpleNamespace(ok=True,json=lambda:{'choices':[]})
        self.mod.post.return_value = good
        self.assertEqual(w.request_groq('chat/completions',PAYLOAD),{'choices':[]})
        self.mod.post.assert_called_once()
        self.mod.post.reset_mock(); self.mod.post.return_value=reply(401)
        with self.assertRaisesRegex(RuntimeError,'HTTP 401'):
            w.request_groq('chat/completions',PAYLOAD)
        self.mod.post.assert_called_once()

    def test_provider_failure_uses_fallback_but_audio_does_not(self):
        self.mod.post.side_effect=[reply(503),reply()]
        w.request_groq('chat/completions',PAYLOAD)
        self.assertTrue(w._gemini_fallback_active)
        self.mod.post.reset_mock(); self.mod.post.side_effect=None; self.mod.post.return_value=reply(503)
        with self.assertRaisesRegex(RuntimeError,'HTTP 503'):
            w.request_groq('audio/speech',{},binary=True)
        self.mod.post.assert_called_once()

    def test_rejects_truncation_safety_empty_invalid_json_and_wrong_schema(self):
        for candidate in [reply(reason='MAX_TOKENS'),reply(reason='SAFETY'),reply(text=''),
                          reply(text='broken'),reply(text='{"ok":"wrong"}'),
                          types.SimpleNamespace(ok=True,json=lambda:{'promptFeedback':{'blockReason':'SAFETY'}})]:
            with self.subTest(candidate=candidate), patch.object(w.time,'sleep'):
                self.mod.post.return_value=candidate
                with self.assertRaises(Exception): w.request_gemini(PAYLOAD)

    def test_gemini_quota_failure_has_no_silent_fallback_or_retry(self):
        self.mod.post.return_value=reply(429)
        with self.assertRaisesRegex(RuntimeError,'Gemini fallback failed with HTTP 429'):
            w.request_gemini(PAYLOAD)
        self.mod.post.assert_called_once()
