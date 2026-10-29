import unittest
from validate_publication_config import REQUIRED, validate


class PublicationConfigTests(unittest.TestCase):
    def test_preview_needs_no_publication_credentials(self):
        validate({})
        validate({'PUBLISH_ENABLED': 'false'})

    def test_each_missing_secret_fails_before_expensive_generation(self):
        ready = dict.fromkeys(REQUIRED, 'present-secret-value')
        ready['PUBLISH_ENABLED'] = 'true'
        validate(ready)
        for name in REQUIRED:
            for absent in ('', '   '):
                with self.subTest(name=name, absent=absent):
                    with self.assertRaisesRegex(ValueError, name) as raised:
                        validate(dict(ready, **{name: absent}))
                    self.assertNotIn('present-secret-value', str(raised.exception))
