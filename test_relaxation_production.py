import unittest,tempfile,json,copy
from pathlib import Path
from unittest.mock import patch
from relaxation.production import build_timeline,chapter_text,shard_images,image_shard
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
 def test_twenty_workers_five_images_each_and_balanced_reuse(self):
  groups=[shard_images(i) for i in range(20)]
  self.assertTrue(all(len(g)==5 for g in groups));self.assertEqual([x for g in groups for x in g],list(range(100)))
  rows=build_timeline(100,10800,17)
  self.assertEqual(len(rows),1080);self.assertTrue(all(a['image']!=b['image'] for a,b in zip(rows,rows[1:])))
  counts=[sum(r['image']==i for r in rows) for i in range(100)]
  self.assertEqual(counts.count(11),80);self.assertEqual(counts.count(10),20)
  self.assertEqual(len({(r['image'],r['variant']) for r in rows}),400)
 def test_batch_reuses_loaded_image_model(self):
  with tempfile.TemporaryDirectory() as tmp,patch('relaxation.preview.image_pipeline') as loader,patch('relaxation.preview.image') as infer,patch('relaxation.preview.depth_mask') as depth:
   out=Path(tmp);(out/'plan.json').write_text(json.dumps(dict(scenes=[{} for _ in range(100)])))
   image_shard(out,19)
   self.assertEqual(loader.call_count,1);self.assertEqual([call.args[1] for call in infer.call_args_list],[95,96,97,98,99]);self.assertEqual(depth.call_count,5)
   self.assertTrue(all(c.kwargs['pipeline'] is loader.return_value and c.kwargs['make_depth'] is False for c in infer.call_args_list))
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
 def test_hundred_ai_views_are_planned_in_bounded_batches(self):
  data=package();data['title']='CALM Highland Rain Piano — 3 Hours';source=data['scenes'][0]
  def views(start):return [dict(source,chapter='View '+str(i),view='Distinct mountain lakeshore view '+str(i)) for i in range(start,start+20)]
  data['scenes']=views(0);data['chapter_titles']=['Lake chapter '+str(i) for i in range(12)]
  def reply(x):return {'choices':[{'message':{'content':json.dumps(x)}}]}
  responses=[reply(data)]+[reply(dict(scenes=views(i))) for i in [20,40,60,80]]
  with tempfile.TemporaryDirectory() as tmp,patch('storage.Store') as store,patch('lyrics_cpu.request_story',side_effect=responses) as ai:
   store.return_value.load.side_effect=[INITIAL_HISTORY,None]
   result=generate(Path(tmp),'hundred',seed,seconds=10800,image_count=100)
   self.assertEqual(ai.call_count,5);self.assertEqual(len(result['scenes']),100);self.assertEqual(len(result['timeline']),1080)
   self.assertEqual(len({s['seed'] for s in result['scenes']}),100)
if __name__=='__main__':unittest.main()
