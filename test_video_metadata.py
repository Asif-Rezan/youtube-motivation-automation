import copy
import json
import unittest
from unittest.mock import Mock, patch
from video_metadata import generate_metadata, validate_metadata, public_description, repair_hashtag_footer, repair_topic_tags, build_metadata_schema


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
    return {'title': 'How Ancient Humans Kept Their Fire Alive', 'description': description,
            'tags': ['ancient humans fire', 'Ancient Humans', 'prehistoric fire maintenance',
                     'prehistoric life', 'early human survival', 'ancient campfires', 'hearths',
                     'fire maintenance', 'human history', 'prehistoric shelters']}


class VideoMetadataTests(unittest.TestCase):
    def test_short_and_long_drafts_reach_repair_through_real_schema_transport(self):
        import story_cpu
        from jsonschema import Draft202012Validator
        from video_metadata import build_metadata_request_schema
        def schema(props):
            return {'type': 'object', 'properties': props, 'required': list(props),
                    'additionalProperties': False}
        for description in ('Too short.', 'X' * 5000):
            with self.subTest(length=len(description)):
                draft = {**metadata_fixture(), 'description': description}
                Draft202012Validator(build_metadata_request_schema(schema)).validate(draft)
                outputs = [draft, metadata_fixture()]
                model = Mock(tokenize=Mock(return_value=[1]), create_chat_completion=Mock(
                    side_effect=[{'choices': [{'finish_reason': 'stop',
                        'message': {'content': json.dumps(data)}}]} for data in outputs]))
                prompts = []
                def ask(prompt, limit, response_schema):
                    prompts.append(prompt)
                    response = story_cpu.request_story('chat/completions', {
                        'messages': [{'role': 'user', 'content': prompt}],
                        'response_format': {'json_schema': {'schema': response_schema}},
                        'max_completion_tokens': limit})
                    return json.loads(response['choices'][0]['message']['content'])
                with patch.object(story_cpu, 'load_model', return_value=model):
                    result = generate_metadata({'title': draft['title'], 'scenes': [
                        {'narration': 'PRIVATE COMPLETED NARRATION'}]}, ask, lambda _: None, schema)
                validate_metadata(result)
                self.assertEqual(model.create_chat_completion.call_count, 2)
                self.assertRegex(prompts[1], r'currently contains [0-9]+ characters')
                self.assertIn('Validation issue:', prompts[1])
                self.assertIn('PRIVATE COMPLETED NARRATION', prompts[1])

    def test_repeated_invalid_description_still_fails_bounded_editorial_validation(self):
        calls = []
        def ask(*args):
            calls.append(args)
            return {**metadata_fixture(), 'description': 'Too short.'}
        with self.assertRaisesRegex(ValueError, '1000'):
            generate_metadata({'title': 'Ancient Humans', 'scenes': []}, ask,
                              lambda _: None, lambda props: props)
        self.assertEqual(len(calls), 2)

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

    def test_malformed_tags_recover_without_another_model_call(self):
        original = metadata_fixture()
        story = {'title': original['title'], 'scenes': [
            {'narration': 'Ancient Humans tended glowing embers. Fire maintenance required dry fuel and a sheltered camp.'}]}
        cases = [[], None, ['#AncientHumans', ' ancient humans ', 'fire maintenance'] * 9,
                 ['Ancient Humans'] * 10, original['tags'] * 4,
                 ['A very long but grounded phrase about ancient human fire maintenance and dry fuel'] * 18,
                 ['fire maintenance, dry fuel;glowing embers|sheltered camp'],
                 ['  fire   maintenance ', '', '#AncientHumans', 123, None],
                 ['#Viral', '#Trending'], 'not an array']
        for raw in cases:
            with self.subTest(raw=raw):
                draft = {**original, 'tags': raw}
                before = copy.deepcopy(draft)
                calls = []
                def ask(*args):
                    calls.append(args)
                    return draft
                result = generate_metadata(story, ask, lambda _: None, lambda props: props)
                validate_metadata(result)
                self.assertEqual(len(calls), 1)
                self.assertEqual(result['title'], original['title'])
                self.assertEqual(result['description'], original['description'])
                self.assertEqual(draft, before)
                self.assertNotIn('Viral', result['tags'])
                self.assertIn('fire maintenance', [tag.casefold() for tag in result['tags']])

    def test_valid_tag_list_keeps_order_spelling_and_long_relevant_phrases(self):
        draft = metadata_fixture()
        draft['tags'][0] = 'how ancient humans maintained a camp fire through a cold night'
        validate_metadata(draft)
        self.assertIs(repair_topic_tags(draft, {}), draft)

    def test_tag_repair_never_bypasses_title_and_description_validation(self):
        for change in ({'title': 'Unrelated keyword title'}, {'description': 'Too short.'},
                       {'description': 'A' * 4600}):
            draft = {**metadata_fixture(), **change, 'tags': []}
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_metadata(repair_topic_tags(draft, {}))

    def test_metadata_schema_bounds_tag_shape_before_long_generation(self):
        from jsonschema import Draft202012Validator, ValidationError
        schema = build_metadata_schema(lambda props: {'type': 'object', 'properties': props})
        validator = Draft202012Validator(schema)
        validator.validate(metadata_fixture())
        for tags in ([], ['one'] * 19, [''] * 8, ['x' * 49] * 8):
            with self.subTest(tags=tags), self.assertRaises(ValidationError):
                validator.validate({**metadata_fixture(), 'tags': tags})

    def test_old_music_footer_removed_and_empty_credit_has_no_trailing_blanks(self):
        footer = 'Background music: original Magenta MusicRNN melody with synthesized ambient piano.'
        self.assertEqual(public_description('Video description.\n\n'+footer, footer), 'Video description.')
        self.assertEqual(public_description('Video description.', ''), 'Video description.')
        # An actual licensed-source attribution remains separate from the removed technical footer.
        self.assertEqual(public_description('Video description.', 'Track attribution required by its license.'),
                         'Video description.\n\nTrack attribution required by its license.')


if __name__ == '__main__':
    unittest.main()


class ShortDescriptionRecoveryTests(unittest.TestCase):
    def test_previous_failure_lengths_are_shortened_without_another_model_call(self):
        from video_metadata import repair_description_length
        fixture = metadata_fixture()
        prose, footer = fixture['description'].rsplit('\n\n', 1)
        for length in (2352, 3163):
            body = prose + '\n\n' + ('The episode connects fuel, shelter and the work of maintaining a hearth. ' * 40)
            body = body[:length - len(footer) - 2 - 1].rstrip() + '.'
            draft = {**fixture, 'description': body + '\n\n' + footer}
            calls = []
            def ask(*args):
                calls.append(args)
                return copy.deepcopy(draft)
            result = generate_metadata({'title': fixture['title'], 'scenes': []}, ask,
                                       lambda _: None, lambda props: props)
            self.assertEqual(len(calls), 1)
            self.assertTrue(1000 <= len(result['description']) <= 2000)
            self.assertTrue(result['description'].startswith('How did Ancient Humans'))
            self.assertEqual(result['description'].splitlines()[-1], footer)
            validate_metadata(result)

    def test_short_copy_can_use_distinct_completed_narration_only(self):
        from video_metadata import repair_description_length
        fixture = metadata_fixture()
        sentences = [
            'A sheltered hearth changes the physical conditions around the fire and the work needed to maintain useful heat.',
            'Fuel gathering requires effort, so the available materials influence the choices that people face at a camp.',
            'An ember and an open flame present different immediate conditions when people return to a fading hearth.',
            'Archaeological remains need interpretation because one surviving trace cannot record every action at a camp.',
            'The account distinguishes physical mechanisms from claims about one universal prehistoric daily routine.',
            'The explanation connects the location of a shelter with the resources available in the surrounding landscape.',
            'Shared effort offers one possible relationship between attending a hearth and meeting other daily needs.',
            'Questions about preservation remind viewers that the surviving evidence is an incomplete record of human activity.',
            'Every example remains an illustrative reconstruction rather than archival footage of a particular community.',
            'The video explores how materials, changing conditions and human attention combine around an ordinary survival problem.',
        ]
        draft = {**fixture, 'description': 'How did Ancient Humans maintain fire? This video explores the practical problem.\n\n#AncientHumans #HumanHistory #Prehistory'}
        story = {'scenes': [{'narration': sentence} for sentence in sentences + sentences]}
        result = repair_description_length(draft, story)
        validate_metadata(result)
        for line in result['description'].splitlines():
            if line.startswith('- '):
                self.assertIn(line[2:], sentences)
                self.assertEqual(result['description'].count(line), 1)

    def test_unrepairable_copy_is_rejected_instead_of_padded_or_mid_sentence_cut(self):
        from video_metadata import repair_description_length
        fixture = metadata_fixture()
        for body in ('A' * 2400, 'Too short.'):
            draft = {**fixture, 'description': body + '\n\n#AncientHumans #HumanHistory #Prehistory'}
            result = repair_description_length(draft, {'scenes': []})
            with self.assertRaises(ValueError):
                validate_metadata(result)
