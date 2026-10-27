import copy
import unittest
from video_metadata import generate_metadata, validate_metadata, public_description, repair_hashtag_footer


def metadata_fixture():
    description = '''How did Ancient Humans keep a camp fire alive when dry fuel was scarce? This educational explainer explores prehistoric fire maintenance, the practical work behind a warm shelter, and the choices that made a hearth useful for everyday life.

Follow the relationship between fuel, shelter and glowing embers through illustrative examples. Rather than imagining one universal routine for every ancient community, the episode considers how a particular setting changes the problem. The focus stays on the camp, the materials available nearby, and the human effort involved in keeping useful heat through changing conditions.

In this video:
- Why a working hearth needed attention rather than simply being left alone.
- How fuel and shelter shape the immediate problem facing a camp.
- What a fading ember changes about the next practical decision.
- Why evidence limits matter when reconstructing prehistoric daily life.

Archaeological evidence, plausible inference and illustrative reconstructions are distinguished; examples are not authentic footage or proof of one routine shared by all prehistoric peoples.

Which challenge would you like us to explore next: finding dry fuel or choosing a sheltered camp? Share your answer in the comments and subscribe for more Ancient Humans explainers about survival, tools and everyday life.

#AncientHumans #PrehistoricLife #FireMaintenance'''
    description = description.replace('In this video:', ('Additional script-grounded detail about fuel, shelter, embers and the limits of archaeological interpretation. ' * 22) + '\n\nIn this video:')
    return {'title': 'How Ancient Humans Kept Their Fire Alive', 'description': description,
            'tags': ['ancient humans fire', 'Ancient Humans', 'prehistoric fire maintenance',
                     'prehistoric life', 'early human survival', 'ancient campfires', 'hearths',
                     'fire maintenance', 'human history', 'prehistoric shelters']}


class VideoMetadataTests(unittest.TestCase):
    def test_malformed_footer_is_repaired_without_another_model_call(self):
        original = metadata_fixture()
        prose = original['description'].rsplit('\n\n', 1)[0]
        story = {'title': original['title'], 'scenes': [
            {'narration': 'Ancient humans worked on fire maintenance and sheltered camps.'}]}
        for footer in ('', '\n\n#FireMaintenance #AncientHumans',
                       '\n\n#AncientHumans #ancienthumans #FireMaintenance',
                       '\n\nHashtags: #AncientHumans, #FireMaintenance, #Viral',
                       '\n\n#AncientHumans\n#FireMaintenance\n#Trending',
                       '\n\n#AncientHumans #FireMaintenance #One #Two #Three #Four'):
            with self.subTest(footer=footer):
                draft = {**original, 'description': prose + footer}
                before = copy.deepcopy(draft)
                requests = []
                def ask(*args):
                    requests.append(args)
                    return draft
                result = generate_metadata(story, ask, lambda _: None, lambda props: props)
                validate_metadata(result)
                self.assertEqual(len(requests), 1)
                self.assertEqual(result['description'].rsplit('\n\n', 1)[0], prose)
                self.assertTrue(result['description'].splitlines()[-1].startswith('#AncientHumans '))
                self.assertIn('#FireMaintenance', result['description'].splitlines()[-1])
                self.assertNotIn('#Viral', result['description'])
                self.assertNotIn('#Trending', result['description'])
                self.assertEqual(draft, before)

    def test_inline_hashtags_move_to_footer_without_losing_prose(self):
        draft = metadata_fixture()
        prose = draft['description'].rsplit('\n\n', 1)[0]
        draft['description'] = prose + ' #AncientHumans #FireMaintenance'
        result = repair_hashtag_footer(draft, {'title': draft['title'], 'scenes': []})
        validate_metadata(result)
        self.assertEqual(result['description'].rsplit('\n\n', 1)[0], prose)

    def test_valid_metadata_is_preserved_exactly(self):
        draft = metadata_fixture()
        self.assertEqual(repair_hashtag_footer(draft, {}), draft)

    def test_footer_repair_cannot_bypass_description_or_tag_validation(self):
        for change in ({'description': 'Too short.'},
                       {'description': 'A' * 4600},
                       {'description': metadata_fixture()['description'].rsplit('\n\n', 1)[0] + '\nBackground music: Magenta'},
                       {'tags': ['duplicate'] * 10}):
            with self.subTest(change=change):
                draft = {**metadata_fixture(), **change}
                with self.assertRaises(ValueError):
                    validate_metadata(repair_hashtag_footer(draft, {}))

    def test_detailed_description_hashtags_and_distinct_tags(self):
        validate_metadata(metadata_fixture())
        for change in ({'description': 'An educational overview.'},
                       {'description': metadata_fixture()['description']+'\nBackground music: Magenta MusicRNN'},
                       {'description': metadata_fixture()['description'].split('#AncientHumans')[0]},
                       {'tags': ['Ancient Humans']*10}):
            with self.subTest(change=change):
                data = {**metadata_fixture(), **change}
                with self.assertRaises(ValueError):
                    validate_metadata(data)

    def test_metadata_uses_completed_script_and_repairs_short_description(self):
        requests, pauses = [], []
        def schema(props):
            return {'type': 'object', 'properties': props, 'required': list(props)}
        def ask(prompt, limit, response_schema):
            requests.append(prompt)
            self.assertIn('UNIQUE COMPLETED NARRATION', prompt)
            data = copy.deepcopy(metadata_fixture())
            if len(requests) == 1:
                data['description'] = 'Too short.'
            return data
        result = generate_metadata({'title': 'How Ancient Humans Kept Fire',
            'scenes': [{'narration': 'UNIQUE COMPLETED NARRATION'}]}, ask, pauses.append, schema)
        self.assertEqual(len(requests), 2)
        self.assertIn('Validation issue:', requests[1])
        self.assertEqual(pauses, [60, 60])
        validate_metadata(result)

    def test_old_music_footer_removed_and_empty_credit_has_no_trailing_blanks(self):
        footer = 'Background music: original Magenta MusicRNN melody with synthesized ambient piano.'
        self.assertEqual(public_description('Video description.\n\n'+footer, footer), 'Video description.')
        self.assertEqual(public_description('Video description.', ''), 'Video description.')
        # An actual licensed-source attribution remains separate from the removed technical footer.
        self.assertEqual(public_description('Video description.', 'Track attribution required by its license.'),
                         'Video description.\n\nTrack attribution required by its license.')


if __name__ == '__main__':
    unittest.main()
