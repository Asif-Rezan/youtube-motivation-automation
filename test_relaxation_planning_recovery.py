import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from relaxation.planning import generate,INITIAL_HISTORY,normalize
from relaxation.preview import seed
from test_relaxation_preview import package

class RecoveryTests(unittest.TestCase):
 def data(self):
  data=package();data['title']='CALM Highland Rain Piano — 3 Hours'
  base=data['scenes'][0]
  data['scenes']=[dict(base,view='Distinct lakeshore composition '+str(i)) for i in range(20)]
  data['chapter_titles']=['Lake chapter '+str(i) for i in range(12)]
  return data
 def reply(self,data):return {'choices':[{'message':{'content':json.dumps(data)}}]}
 def test_repeated_batches_recover_to_100_distinct_generated_image_prompts(self):
  data=self.data();reply=self.reply(dict(scenes=data['scenes']))
  with tempfile.TemporaryDirectory() as tmp,patch('storage.Store') as store,patch('lyrics_cpu.request_story',side_effect=[self.reply(data),reply,reply,reply]) as ai:
   store.return_value.load.side_effect=[INITIAL_HISTORY,None]
   result=generate(Path(tmp),'123',seed,seconds=10800,image_count=100)
   self.assertEqual(ai.call_count,4)
   self.assertEqual(len({normalize(s['view']) for s in result['scenes']}),100)
   self.assertEqual(len({s['seed'] for s in result['scenes']}),100)
   self.assertTrue(any(c.args[1].get('planning_in_progress') for c in store.return_value.save.call_args_list if isinstance(c.args[1],dict)))
 def test_valid_scenes_from_partial_duplicate_batch_are_preserved(self):
  data=self.data();mixed=copy.deepcopy(data['scenes']);mixed[-1]['view']='New secluded mossy shore composition'
  with tempfile.TemporaryDirectory() as tmp,patch('storage.Store') as store,patch('lyrics_cpu.request_story',return_value=self.reply(dict(scenes=mixed))):
   store.return_value.load.side_effect=[INITIAL_HISTORY,dict(planning_in_progress=True,run_id='123',seconds=10800,image_count=100,data=data)]
   result=generate(Path(tmp),'123',seed,seconds=10800,image_count=100)
   self.assertIn('New secluded mossy shore composition',[s['view'] for s in result['scenes']])
 def test_resume_rejects_changed_budget(self):
  with tempfile.TemporaryDirectory() as tmp,patch('storage.Store') as store:
   store.return_value.load.side_effect=[INITIAL_HISTORY,dict(planning_in_progress=True,run_id='123',seconds=60,image_count=6,data={})]
   with self.assertRaises(ValueError):generate(Path(tmp),'123',seed,seconds=10800,image_count=100)
