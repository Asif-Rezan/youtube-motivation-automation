import hashlib
import json
import os
import re
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

import story_cpu as s
import workflow as w


@patch.dict(os.environ, {'TEXT_BACKEND': 'qwen-local', 'STORY_MODEL': s.MODEL_ID})
class QwenTests(unittest.TestCase):
    def payload(self):
        return {'model': s.MODEL_ID, 'messages': [{'role': 'user', 'content': 'private narration'}],
            'response_format': {'type': 'json_schema', 'json_schema': {'schema': {
                'type': 'object', 'properties': {'ready': {'type': 'boolean'}},
                'required': ['ready'], 'additionalProperties': False}}},
            'max_completion_tokens': 256}

    def result(self, content='{"ready":true}', finish='stop'):
        return {'choices': [{'finish_reason': finish, 'message': {'content': content}}]}

    def model(self, **kwargs):
        return Mock(tokenize=Mock(return_value=[1]), **kwargs)

    def test_local_generation_constrains_and_validates_original_schema(self):
        model = self.model(create_chat_completion=Mock(return_value=self.result()))
        payload = self.payload()
        original = json.dumps(payload)
        with patch.object(s, 'load_model', return_value=model), patch('requests.post') as post:
            self.assertEqual(w.request_text('chat/completions', payload), self.result())
        post.assert_not_called()
        self.assertEqual(json.dumps(payload), original)
        sent = model.create_chat_completion.call_args.kwargs
        self.assertEqual(sent['response_format'], {'type': 'json_object',
            'schema': payload['response_format']['json_schema']['schema']})
        self.assertNotIn('reasoning_effort', sent)
        self.assertIn('JSON Schema', sent['messages'][-1]['content'])

    def test_invalid_type_extra_fields_and_truncation_never_accepted(self):
        for content, finish in [('{"ready":"yes"}', 'stop'),
                                ('{"ready":true,"extra":1}', 'stop'),
                                ('private broken output', 'stop'),
                                ('{"ready":true}', 'length')]:
            with self.subTest(content=content, finish=finish):
                model = self.model(create_chat_completion=Mock(return_value=self.result(content, finish)))
                with patch.object(s, 'load_model', return_value=model), patch('builtins.print') as output:
                    with self.assertRaisesRegex(s.StoryGenerationError, 'three attempts') as caught:
                        s.request_story('chat/completions', self.payload())
                self.assertEqual(model.create_chat_completion.call_count, 3)
                self.assertNotIn(content, str(caught.exception))
                self.assertNotIn('private broken output', str(output.call_args_list))

    def test_invalid_json_can_recover_on_same_local_model(self):
        model = self.model(create_chat_completion=Mock(side_effect=[self.result('{}'), self.result()]))
        with patch.object(s, 'load_model', return_value=model):
            s.request_story('chat/completions', self.payload())
        self.assertEqual(model.create_chat_completion.call_count, 2)

    def test_truncation_increases_budget_and_supplies_correction(self):
        model = self.model(create_chat_completion=Mock(side_effect=[
            self.result('{"ready":', 'length'), self.result()]))
        with patch.object(s, 'load_model', return_value=model):
            s.request_story('chat/completions', self.payload())
        first, second = [call.kwargs for call in model.create_chat_completion.call_args_list]
        self.assertGreater(second['max_tokens'], first['max_tokens'])
        self.assertLessEqual(second['max_tokens'], 6000)
        self.assertIn('complete valid JSON', second['messages'][-1]['content'])

    def test_length_retry_gives_measured_feedback_without_logging_private_text(self):
        payload = self.payload()
        payload['response_format']['json_schema']['schema']['properties']['ready'] = {
            'type': 'string', 'minLength': 300, 'maxLength': 400}
        model = self.model(create_chat_completion=Mock(side_effect=[
            self.result(json.dumps({'ready': 'PRIVATE DRAFT'})),
            self.result(json.dumps({'ready': 'x' * 350}))]))
        with patch.object(s, 'load_model', return_value=model), patch('builtins.print') as output:
            s.request_story('chat/completions', payload)
        sent = model.create_chat_completion.call_args.kwargs['messages'][-1]['content']
        self.assertIn('minLength requires 300', sent)
        self.assertIn('length 13', sent)
        self.assertNotIn('PRIVATE DRAFT', str(output.call_args_list))
        self.assertIn('schema_validation', str(output.call_args_list))

    def test_retry_feedback_is_included_in_context_budget(self):
        model = self.model(create_chat_completion=Mock(return_value=self.result('{}')))
        # Original request fits, but the extra corrective message does not.
        model.tokenize.side_effect = lambda content, **kwargs: [1] * (
            s.CONTEXT_TOKENS if b'previous response' in content else 1)
        with patch.object(s, 'load_model', return_value=model):
            with self.assertRaisesRegex(s.StoryGenerationError, 'context budget'):
                s.request_story('chat/completions', self.payload())
        model.create_chat_completion.assert_called_once()

    def test_context_overflow_stops_before_inference(self):
        model = self.model()
        model.tokenize.return_value = [1] * s.CONTEXT_TOKENS
        with patch.object(s, 'load_model', return_value=model):
            with self.assertRaisesRegex(s.StoryGenerationError, 'context budget'):
                s.request_story('chat/completions', self.payload())
        model.create_chat_completion.assert_not_called()

    def test_model_substitution_and_non_text_endpoints_are_refused(self):
        payload = self.payload()
        payload['model'] = 'different/model'
        with patch.object(s, 'load_model') as load:
            with self.assertRaisesRegex(s.StoryGenerationError, 'STORY_MODEL'):
                s.request_story('chat/completions', payload)
            with self.assertRaisesRegex(s.StoryGenerationError, 'script JSON'):
                s.request_story('audio/speech', self.payload())
        load.assert_not_called()

    def test_runtime_failure_does_not_print_or_retry_private_content(self):
        model = self.model(create_chat_completion=Mock(side_effect=RuntimeError('private narration')))
        with patch.object(s, 'load_model', return_value=model):
            with self.assertRaises(s.StoryGenerationError) as caught:
                s.request_story('chat/completions', self.payload())
        self.assertNotIn('private narration', str(caught.exception))
        model.create_chat_completion.assert_called_once()

    def test_model_checksum_detects_changed_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'model.gguf'
            path.write_bytes(b'expected weights')
            with patch.object(s, 'GGUF_SHA256', hashlib.sha256(b'expected weights').hexdigest()):
                self.assertTrue(s.verify_model(path))
                path.write_bytes(b'corrupt weights')
                self.assertFalse(s.verify_model(path))

    def test_model_load_is_pinned_anonymous_cpu_and_reused(self):
        llama = Mock(return_value=self.model())
        with patch.object(s, '_model', None), patch('huggingface_hub.hf_hub_download', return_value='/weights.gguf') as download, patch.dict('sys.modules', {'llama_cpp': types.SimpleNamespace(Llama=llama)}), patch.object(s, 'verify_model', return_value=True):
            model = s.load_model()
            self.assertIs(s.load_model(), model)
        download.assert_called_once_with(repo_id=s.GGUF_REPO, filename=s.GGUF_FILE,
            revision=s.GGUF_REVISION, token=False, force_download=False)
        self.assertEqual(llama.call_args.kwargs['n_gpu_layers'], 0)
        self.assertFalse(llama.call_args.kwargs['verbose'])
        llama.assert_called_once()

    def test_bad_download_is_bounded_and_runtime_does_not_load(self):
        llama = Mock()
        with patch.object(s, '_model', None), patch('huggingface_hub.hf_hub_download', return_value='/weights.gguf') as download, patch.dict('sys.modules', {'llama_cpp': types.SimpleNamespace(Llama=llama)}), patch.object(s, 'verify_model', return_value=False), patch.object(s.time, 'sleep'):
            with self.assertRaisesRegex(s.StoryGenerationError, 'three attempts'):
                s.load_model()
        self.assertEqual(download.call_count, 3)
        llama.assert_not_called()



class DecoderSchemaSafetyTests(unittest.TestCase):
    def test_unsupported_patterns_fail_before_loading_or_calling_native_model(self):
        for pattern in (r'^\S+( \S+){1,4}$', r'^\w+$', r'^\d+$', r'(?=x)x', r'^(x)\1$'):
            with self.subTest(pattern=pattern):
                payload = QwenTests().payload()
                payload['response_format']['json_schema']['schema']['properties']['ready'] = {
                    'type': 'string', 'pattern': pattern}
                with patch.object(s, 'load_model') as load:
                    with self.assertRaisesRegex(s.StoryGenerationError, 'explicit character classes'):
                        s.request_story('chat/completions', payload)
                load.assert_not_called()

    def test_large_text_limits_stay_in_validator_not_nested_native_grammar(self):
        schema = {'type': 'object', 'properties': {'description': {
            'type': 'string', 'minLength': 3500, 'maxLength': 4500}}}
        original = json.dumps(schema)
        converted = s.decoder_schema(schema)
        self.assertEqual(converted['properties']['description'], {'type': 'string'})
        self.assertEqual(json.dumps(schema), original)
        from jsonschema import Draft202012Validator, ValidationError
        with self.assertRaises(ValidationError):
            Draft202012Validator(schema).validate({'description': 'short'})

    def test_production_thumbnail_pattern_preserves_word_count(self):
        from human_history import THUMBNAIL_SCHEMA, THUMBNAIL_FALLBACKS
        from jsonschema import Draft202012Validator, ValidationError
        s.decoder_schema({'type': 'object', 'properties': {'thumbnail_text': THUMBNAIL_SCHEMA}})
        validator = Draft202012Validator(THUMBNAIL_SCHEMA)
        for text in THUMBNAIL_FALLBACKS.values():
            validator.validate(text)
        for text in ('FIRE', 'ONE TWO THREE FOUR FIVE SIX', 'FIRE\nGONE?', 'x' * 46):
            with self.subTest(text=text), self.assertRaises(ValidationError):
                validator.validate(text)

    def test_original_large_description_limit_still_rejects_model_output(self):
        payload = QwenTests().payload()
        payload['response_format']['json_schema']['schema']['properties']['ready'] = {
            'type': 'string', 'minLength': 3500, 'maxLength': 4500}
        model = QwenTests().model(create_chat_completion=Mock(return_value=QwenTests().result('{"ready":"short"}')))
        with patch.object(s, 'load_model', return_value=model):
            with self.assertRaisesRegex(s.StoryGenerationError, 'three attempts'):
                s.request_story('chat/completions', payload)
        self.assertEqual(model.create_chat_completion.call_args.kwargs['response_format']['schema']
                         ['properties']['ready'], {'type': 'string'})
