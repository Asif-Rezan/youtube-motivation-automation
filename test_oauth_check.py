"""Exercise preflight decisions without real credentials or network requests."""
import contextlib
import io
import json
import os
import runpy
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


class OAuthPreflightTests(unittest.TestCase):
    def check(self, drive_error=None, groq='configured'):
        creds = MagicMock()
        creds.granted_scopes = ['https://www.googleapis.com/auth/youtube.upload']
        youtube, drive = MagicMock(), MagicMock()
        youtube.channels.return_value.list.return_value.execute.return_value = {
            'items': [{'id': 'UCztvMrNCT34DO3DtzLPgWaw', 'snippet': {'title': 'Test'}}]}
        drive.about.return_value.get.return_value.execute.return_value = {'storageQuota': {}}
        drive.files.return_value.list.return_value.execute.return_value = {'files': []}
        def build(service, *args, **kwargs):
            if service == 'drive' and drive_error:
                raise RuntimeError(drive_error)
            return youtube if service == 'youtube' else drive
        modules = {name: types.ModuleType(name) for name in (
            'google', 'google.auth', 'google.auth.transport', 'google.auth.transport.requests',
            'google.oauth2', 'google.oauth2.credentials', 'googleapiclient', 'googleapiclient.discovery')}
        modules['google.auth.transport.requests'].Request = MagicMock()
        modules['google.oauth2.credentials'].Credentials = MagicMock()
        modules['google.oauth2.credentials'].Credentials.from_authorized_user_info.return_value = creds
        modules['googleapiclient.discovery'].build = build
        token = json.dumps(dict(client_id='client', client_secret='secret', refresh_token='refresh'))
        output = io.StringIO()
        with patch.dict(os.environ, {'YOUTUBE_TOKEN_JSON': token, 'DRIVE_TOKEN_JSON': token,
                'REQUIRE_GROQ': 'true', 'GROQ_API_KEY': groq}, clear=True), \
                patch.dict(sys.modules, modules), contextlib.redirect_stdout(output):
            with self.assertRaises(SystemExit) as result:
                runpy.run_path('oauth_check.py', run_name='__main__')
        return result.exception.code, [json.loads(line) for line in output.getvalue().splitlines()]

    def test_private_upload_needs_no_publish_scope(self):
        code, reports = self.check()
        self.assertEqual(code, 0)
        self.assertEqual(reports[1]['publish_scope'], 'missing')

    def test_missing_groq_stops_before_generation(self):
        code, reports = self.check(groq=' ')
        self.assertEqual(code, 1)
        self.assertEqual(reports[-1]['check'], 'Groq readiness')

    def test_rejected_drive_grant_fails_with_safe_recovery_guidance(self):
        code, reports = self.check(drive_error='invalid_grant private-sensitive-response')
        self.assertEqual(code, 1)
        error = next(r for r in reports if r.get('error') == 'invalid_grant')
        self.assertIn('Production', error['action'])
        self.assertNotIn('private-sensitive-response', json.dumps(reports))
