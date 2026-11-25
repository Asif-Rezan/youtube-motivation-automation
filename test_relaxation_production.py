import unittest,tempfile,json,copy
from pathlib import Path
from unittest.mock import patch
from relaxation.production import build_timeline,chapter_text
from relaxation.planning import generate,INITIAL_HISTORY
from relaxation.preview import seed
from test_relaxation_preview import package
class ProductionTests(unittest.TestCase):
 def test_three_hours_twenty_images_no_adjacent_repeats(self):
  rows=build_timeline(20,10800,123)
  self.assertEqual(len(rows),1080);self.assertEqual(rows[-1]['start']+rows[-1]['duration'],10800)
  self.assertTrue(all(a['image']!=b['image'] for a,b in zip(rows,rows[1:])))
  self.assertEqual({i:sum(r['image']==i for r in rows) for i in range(20)},dict.fromkeys(range(20),54))
  self.assertEqual(len({(r['image'],r['variant']) for r in rows}),80)
  self.assertNotEqual(rows,build_timeline(20,10800,456))
 def test_actual_chapter_timestamps(self):
  text=chapter_text(['Chapter '+str(i) for i in range(12)])
  self.assertIn('00:00 Chapter 0',text);self.assertIn('15:00 Chapter 1',text)
  self.assertIn('01:00:00 Chapter 4',text);self.assertIn('02:45:00 Chapter 11',text)
  self.assertEqual(len(text.splitlines()),12)
 def test_impossible_reuse_or_duration_rejected(self):
  for args in [(1,10800),(20,10801)]:
   with self.assertRaises(ValueError):build_timeline(*args)
 def test_ai_full_length_metadata_chapters_and_image_pool(self):
  data=package();data['title']='CALM Highland Rain Piano — 3 Hours';source=data['scenes'][0]
  data['scenes']=[dict(source,chapter='View '+str(i),view='Distinct mountain lakeshore view '+str(i)) for i in range(20)]
  data['chapter_titles']=['Lake chapter '+str(i) for i in range(12)]
  with tempfile.TemporaryDirectory() as tmp,patch('storage.Store') as store,patch('lyrics_cpu.request_story') as ai:
   store.return_value.load.side_effect=[INITIAL_HISTORY,None];ai.return_value={'choices':[{'message':{'content':json.dumps(data)}}]}
   result=generate(Path(tmp),'long',seed,seconds=10800,image_count=20)
   self.assertEqual(result['seconds'],10800);self.assertEqual(len(result['timeline']),1080)
   self.assertIn('02:45:00',result['youtube']['snippet']['description']);self.assertNotIn('One-minute',result['description']);self.assertFalse(result['publish'])
if __name__=='__main__':unittest.main()
