"""Story duration, duplicate recovery and publication isolation checks."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from daily_story import music_parts, plan, root_for
from story_writer import VERSION, validate_story, novelty_reason, normalized, scene_prompt, text_hash, save_json
from story_video import validate_timing
from upload_settings import load_settings, upload_body


def example_story():
    line = 'उस दिन राम ने अपनी छोटी दुकान खोली और मन में ठान लिया कि वह आज हर ग्राहक की बात ध्यान से सुनकर उसकी मदद करेगा।'
    scenes = [dict(index=i,speaker='narrator' if i%4 < 3 else ('male' if i%8 == 3 else 'female'),
        text=line,visual='An Indian shopkeeper carefully opens his small village shop at sunrise.') for i in range(48)]
    return dict(content_type='hindi_story',writer_version=VERSION,run_id='story-test',title='एक नई सुबह',
        description='एक दुकानदार के साहस की मौलिक कहानी।',summary='A shopkeeper learns to listen to customers and rebuilds his small business.',
        characters='Ram, an Indian man in a blue kurta, short black hair.',world='Pastel Indian village with warm golden lighting.',
        scenes=scenes,lyrics='\n'.join(s['text'] for s in scenes),tags=['Hindi story'])


class StoryChecks(unittest.TestCase):
    def test_accepts_complete_hindi_story_rejects_english_and_short_script(self):
        story=example_story()
        validate_story(story)
        broken=copy.deepcopy(story)
        broken['scenes'][0]['text']='This is an entirely English paragraph with enough words to pass the word count but should fail the Hindi script validation for daily Hindi uploads.'
        with self.assertRaisesRegex(ValueError,'Devanagari'):
            validate_story(broken)
        broken=copy.deepcopy(story)
        broken['scenes'].pop()
        with self.assertRaisesRegex(ValueError,'48-scene'):
            validate_story(broken)

    def test_duplicate_title_punctuation_and_script_are_detected(self):
        story=example_story()
        self.assertEqual(novelty_reason(story,[{'title':story['title']+'!'}]),'title')
        self.assertEqual(novelty_reason(story,[{'title':'दूसरी कहानी','hash':text_hash(story['lyrics'])}]),'text')

    def test_reference_style_and_scene_action_are_included(self):
        story=example_story()
        prompt=scene_prompt(story,story['scenes'][0])
        self.assertTrue(prompt.startswith(story['scenes'][0]['visual']))
        self.assertIn('Cute colorful 3D storybook cartoon',prompt)
        self.assertIn('bright pastel colors',prompt)
        self.assertIn(story['characters'],prompt)

    def test_music_covers_all_speech_without_tiny_or_overlong_requests(self):
        for seconds in (480,480.1,599.87,600,600.02,719.9,720):
            parts=music_parts(seconds)
            self.assertGreaterEqual(sum(parts),seconds)
            self.assertTrue(all(90 <= n <= 120 for n in parts))
        for seconds in (479.99,720.01):
            with self.assertRaises(ValueError):
                music_parts(seconds)

    def test_timeline_rejects_gaps_and_truncation(self):
        story=example_story()
        timing=dict(duration=600,scenes=[dict(index=i,start=i*12.5,end=(i+1)*12.5) for i in range(48)])
        validate_timing(story,timing)
        timing['scenes'][3]['start'] += 1
        with self.assertRaisesRegex(ValueError,'Non-contiguous'):
            validate_timing(story,timing)

    def test_existing_daily_story_resumes_without_rewriting(self):
        story=example_story()
        store=Mock()
        store.load.side_effect=[[{'run':'story-test','title':story['title']}],story]
        with tempfile.TemporaryDirectory() as temporary,patch('storage.Store',return_value=store),patch('story_writer.ask') as ask:
            result=plan(Path(temporary),'story-test',True)
            self.assertEqual(result,story)
            ask.assert_not_called()
            self.assertEqual(store.save.call_args.args[0],'stories/history.json')

    def test_story_upload_uses_hindi_general_audience_and_keeps_schedule(self):
        with patch.dict('os.environ',{},clear=True):
            story_settings=load_settings(profile='story')
            kids_settings=load_settings()
        self.assertFalse(story_settings['made_for_kids'])
        self.assertTrue(kids_settings['made_for_kids'])
        self.assertEqual(story_settings['language'],'hi')
        self.assertEqual(story_settings['audio_language'],'hi')
        self.assertEqual(story_settings['category_id'],'27')
        self.assertEqual(story_settings['schedule_policy'],'new_york_6am_after_72h')
        body=upload_body(example_story(),'Description',['Hindi story'],story_settings)
        self.assertEqual(body['status']['privacyStatus'],'private')
        self.assertTrue(body['status']['containsSyntheticMedia'])
        self.assertFalse(body['status']['selfDeclaredMadeForKids'])

    def test_invalid_identity_cannot_escape_output_folder(self):
        with self.assertRaises(ValueError):
            root_for('../wrong')


class StoryPublicationChecks(unittest.TestCase):
    def test_new_story_upload_preserves_story_metadata_and_general_audience(self):
        from pipeline import publish
        client,state=Mock(),{}
        client.videos.return_value.insert.return_value.next_chunk.return_value=(None,{'id':'story-video'})
        def readback():
            video=copy.deepcopy(state['upload_body'])
            video.update(id='story-video',contentDetails={'definition':'hd'},processingDetails={'processingStatus':'succeeded'})
            video['snippet']['channelId']='channel'
            video['status']['uploadStatus']='processed'
            return {'items':[video]}
        client.videos.return_value.list.return_value.execute.side_effect=readback
        story=example_story()
        with patch.dict('os.environ',{'UPLOAD_MODE':'public'},clear=True),patch('pipeline.required',return_value='channel'),patch('googleapiclient.http.MediaFileUpload'):
            publish(client,Path('/unused'),story,state,Mock(),upload_thumbnail=False)
        body=client.videos.return_value.insert.call_args.kwargs['body']
        self.assertEqual(body['snippet']['title'],story['title'])
        self.assertEqual(body['snippet']['tags'],story['tags'])
        self.assertEqual(body['snippet']['defaultAudioLanguage'],'hi')
        self.assertFalse(body['status']['selfDeclaredMadeForKids'])
        self.assertEqual(state['phase'],'published')

class StoryCleanupChecks(unittest.TestCase):
    def test_cleanup_uses_story_namespace_and_never_touches_script_or_kids_media(self):
        import hashlib
        from cleanup_drive import cleanup
        story=example_story()
        settings=load_settings(profile='story')
        settings['mode']='public'
        body=upload_body(story,story['description'],story['tags'],settings)
        video=copy.deepcopy(body)
        video.update(id='video',processingDetails={'processingStatus':'succeeded'},contentDetails={'definition':'hd'})
        video['snippet']['channelId']='channel'
        video['status']['uploadStatus']='processed'
        state=dict(song=story,phase='published',video_id='video',thumbnail_uploaded=True,upload_body=body)
        client=Mock()
        client.videos.return_value.list.return_value.execute.return_value={'items':[video]}
        store=Mock(folder='folder')
        store.load.return_value=None
        key='stories/runs/story-test/video.mp4'
        store.find.side_effect=lambda value:'file' if value==key else None
        store.client.files.return_value.get.return_value.execute.return_value=dict(id='file',name=key.replace('/','__'),
            parents=['folder'],appProperties={'workflow_key':hashlib.sha256(key.encode()).hexdigest()},mimeType='video/mp4')
        with patch.dict('os.environ',{'EXPECTED_CHANNEL_ID':'channel'}):
            cleanup(store,client,'story-test',state)
        store.client.files.return_value.delete.assert_called_once_with(fileId='file')
        keys=[call.args[0] for call in store.find.call_args_list]
        self.assertTrue(all(key.startswith('stories/runs/story-test/') for key in keys))
        self.assertNotIn('stories/runs/story-test/story.json',keys)
        self.assertEqual(store.save.call_args.args[0],'stories/runs/story-test/cleanup.json')
        video['status']['privacyStatus']='private'
        store.client.files.return_value.delete.reset_mock()
        with patch.dict('os.environ',{'EXPECTED_CHANNEL_ID':'channel'}),self.assertRaises((ValueError,RuntimeError)):
            cleanup(store,client,'story-test',state)
        store.client.files.return_value.delete.assert_not_called()

if __name__=='__main__':
    unittest.main()
