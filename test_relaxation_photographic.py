import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from relaxation.art_style import STYLE_ID,negative_prompt
from relaxation.preview import thumbnail,plan
from test_relaxation_preview import package
from relaxation.planning import INITIAL_HISTORY
from upload_settings import load_settings,upload_body

class PhotographicTests(unittest.TestCase):
 def test_new_prompts_and_seo_brief_use_natural_photography(self):
  with tempfile.TemporaryDirectory() as tmp,patch('storage.Store') as store,patch('lyrics_cpu.request_story') as ai:
   store.return_value.load.side_effect=[INITIAL_HISTORY,None]
   ai.return_value={'choices':[{'message':{'content':json.dumps(package())}}]}
   data=plan(Path(tmp),'new-photo')
   self.assertEqual(data['art_style'],STYLE_ID)
   self.assertTrue(all('Ultra-realistic nature photograph' in s['prompt'] and 'storybook' not in s['prompt'] for s in data['scenes']))
   prompt=ai.call_args.args[1]['messages'][0]['content']
   self.assertIn('Chapter titles',prompt);self.assertIn('first two description sentences',prompt)
   self.assertIn('CGI',negative_prompt(STYLE_ID))
   self.assertNotIn('photorealistic',negative_prompt(STYLE_ID))
 def test_thumbnail_is_full_hd_with_image_dependent_colour(self):
  with tempfile.TemporaryDirectory() as tmp:
   out=Path(tmp);data=dict(thumbnail=dict(scene_index=0,headline='PEACEFUL RAIN'))
   thumbnail(out,[Image.new('RGB',(1024,576),(60,120,70))],data)
   with Image.open(out/'thumbnail.jpg') as im:self.assertEqual(im.size,(1920,1080))
   self.assertLess((out/'thumbnail.jpg').stat().st_size,2000000)
 def test_publishing_details_match_general_audience_music(self):
  with patch.dict('os.environ',{'UPLOAD_MODE':'public','PUBLISH_AT':''}):settings=load_settings(relaxation=True)
  data=package();body=upload_body(data,data['description'],data['tags'],settings)
  self.assertEqual(body['snippet']['categoryId'],'10')
  self.assertEqual(body['snippet']['defaultLanguage'],'en');self.assertEqual(body['snippet']['defaultAudioLanguage'],'en')
  self.assertFalse(body['status']['selfDeclaredMadeForKids']);self.assertTrue(body['status']['containsSyntheticMedia'])
  self.assertFalse(body['paidProductPlacementDetails']['hasPaidProductPlacement'])
