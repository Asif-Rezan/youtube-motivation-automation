import unittest
from script_quality import validate, fingerprint


class QualityTests(unittest.TestCase):
    def story(self):
        subjects = ['Fuel collection changes the work needed at a hearth',
                    'Shelter location affects conditions around a camp',
                    'Material traces require careful archaeological interpretation']
        return {'scenes': [{'narration': subject + '. ' + ' '.join(f'{word}{i}' for i in range(150)) + '.'}
                           for subject, word in zip(subjects, ['embers', 'rain', 'evidence'])]}

    def test_distinct_narration_passes_and_shared_title_keyword_does_not_matter(self):
        story = self.story()
        story['title'] = 'Ancient Humans Kept Fire'
        result = validate(story, [{'title': 'Ancient Humans Built Shelter'}])
        self.assertTrue(result['repetition_checks_passed'])
        self.assertFalse(result['monetization_eligibility_verified'])

    def test_duplicate_chapters_and_repeated_filler_are_rejected(self):
        story = self.story()
        story['scenes'].append(story['scenes'][0].copy())
        with self.assertRaisesRegex(ValueError, 'identical narration'):
            validate(story)
        story = {'scenes': [{'narration': 'This general explanation repeats the same idea without adding anything. ' * 3}]}
        with self.assertRaisesRegex(ValueError, 'repeated three'):
            validate(story)

    def test_reused_script_is_detected_even_when_title_changes(self):
        story = self.story()
        history = [{'title': 'Different title', 'content_fingerprint_v1': fingerprint(story)}]
        with self.assertRaisesRegex(ValueError, 'earlier upload'):
            validate(story, history)

    def test_normalized_fingerprints_ignore_shared_cta(self):
        import copy
        from human_history import CTA
        story = self.story()
        other = copy.deepcopy(story)
        other['scenes'][-1]['narration'] += CTA
        self.assertEqual(fingerprint(story), fingerprint(other))
