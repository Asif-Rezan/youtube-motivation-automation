import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from test_relaxation_preview import package
from relaxation.planning import validate,generate,INITIAL_HISTORY,normalize
from relaxation.preview import seed

class ValidationRecoveryTests(unittest.TestCase):
 def test_shared_seo_wording_does_not_reject_a_different_setting(self):
  data=package();old=copy.deepcopy(data)
  data.update(title='CALM Highland Forest Piano — 1 Minute of Gentle Rain',idea='Gentle piano beside a misty forest in soft rain',environment='Redwood forest clearing',concept_id='redwood-clearing-rain')
  validate(data,[old])
 def test_exact_repeated_idea_remains_rejected_with_different_label(self):
  data=package();old=copy.deepcopy(data);data.update(environment='Different label',concept_id='new-slug',title='PEACEFUL Rain Piano — 1 Minute')
  with self.assertRaisesRegex(ValueError,'Idea'):validate(data,[old])
 def test_repeated_anchor_views_are_repaired_without_another_model_call(self):
  data=package();data['scenes']=[copy.deepcopy(data['scenes'][0]) for _ in range(6)]
  with tempfile.TemporaryDirectory() as tmp,patch('storage.Store') as store,patch('lyrics_cpu.request_story') as ai:
   store.return_value.load.side_effect=[INITIAL_HISTORY,None]
   ai.return_value={'choices':[{'message':{'content':json.dumps(data)}}]}
   result=generate(Path(tmp),'123',seed)
   self.assertEqual(ai.call_count,1);self.assertEqual(len({normalize(x['view']) for x in result['scenes']}),6)
 def test_json_errors_have_actionable_saved_diagnostics(self):
  with tempfile.TemporaryDirectory() as tmp,patch('storage.Store') as store,patch('lyrics_cpu.request_story') as ai:
   store.return_value.load.side_effect=[INITIAL_HISTORY,None]
   ai.return_value={'choices':[{'message':{'content':'broken json'}}]}
   with self.assertRaisesRegex(ValueError,'not valid JSON'):generate(Path(tmp),'123',seed)
   reports=json.loads((Path(tmp)/'planning-diagnostics.json').read_text())
   self.assertEqual(len(reports),3);self.assertTrue(all(not r['accepted'] for r in reports))
 def test_duplicate_concept_still_stops_with_specific_reason(self):
  data=package();old=copy.deepcopy(data)
  with tempfile.TemporaryDirectory() as tmp,patch('storage.Store') as store,patch('lyrics_cpu.request_story') as ai:
   store.return_value.load.side_effect=[[old],None];ai.return_value={'choices':[{'message':{'content':json.dumps(data)}}]}
   with self.assertRaisesRegex(ValueError,'Repeated episode concept'):generate(Path(tmp),'123',seed)
