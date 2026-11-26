import tempfile,unittest,copy,json
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image
from relaxation.preview import plan,extend,validate_audio,image_at,rain_score,overlap,atmospheric
from relaxation.planning import validate,INITIAL_HISTORY

def package():
 return dict(idea='Gentle piano beside a misty mountain lake in soft rain',concept_id='highland-lake-soft-rain',title='CALM Highland Lake Piano — 1 Minute of Gentle Rain',description='A quiet piano pause beside a misty lake.',
  tags=['relaxing piano','gentle rain','mountain lake','rain ambience','calm music','soft piano','nature sounds','one minute relaxation'],environment='Misty highland lake and a pine shore',lighting='Soft overcast dawn',palette='Muted blue and pine green',music_prompt='Sparse gentle felt piano, warm pads, no vocals or drums',rain_prompt='Soft steady rain on lake water, no thunder or voices',thumbnail=dict(headline='A QUIET MOMENT',scene_index=1),scenes=[dict(chapter='Lake view '+str(i+1),view='View '+str(i+1)+' of the lake shore with different foreground rocks',camera=['pan_left','pan_right','zoom_in','zoom_out'][i%4],water_region='lower_center') for i in range(6)])
class RelaxationTests(unittest.TestCase):
 def test_ai_history_unique_scenes_metadata_and_no_publish(self):
  with tempfile.TemporaryDirectory() as d,patch('storage.Store') as store,patch('lyrics_cpu.request_story') as ai:
   store.return_value.load.side_effect=[INITIAL_HISTORY,None];ai.return_value={'choices':[{'message':{'content':json.dumps(package())}}]}
   p=plan(Path(d),'episode');self.assertEqual([s['start'] for s in p['scenes']],[0,10,20,30,40,50]);self.assertEqual(len({s['seed'] for s in p['scenes']}),6);self.assertFalse(p['publish'])
   self.assertTrue(ai.called);self.assertIn('tropical-rain-garden',ai.call_args.args[1]['messages'][0]['content']);self.assertIn('0:50',p['youtube']['snippet']['description']);self.assertEqual(p['youtube']['snippet']['categoryId'],'10');self.assertFalse(p['youtube']['status']['selfDeclaredMadeForKids']);self.assertTrue((Path(d)/'metadata.json').exists());self.assertEqual(p['art_style'],'natural-photorealistic-v1');self.assertTrue(all(s['prompt'].startswith('Ultra-realistic nature photograph') for s in p['scenes']))
 def test_rejects_repeated_concept_or_title(self):
  p=package();history=[dict(title=p['title'],idea=p['idea'],concept_id=p['concept_id'])]
  with self.assertRaises(ValueError):validate(p,history)
 def test_loop_crossfade_and_exact_stereo_duration(self):
  pcm=np.sin(np.arange(1000)*.02).astype('float32');result=extend(pcm,100)
  self.assertEqual(extend(pcm[:,None],100).shape,(6000,2));self.assertEqual(result.shape,(6000,2));self.assertTrue(np.isfinite(result).all());self.assertLess(np.abs(np.diff(result[:,0])).max(),.1)
 def test_invalid_neural_outputs_rejected(self):
  for pcm in [np.zeros(1000),np.full(1000,np.nan),np.ones(20)]:
   with self.assertRaises(ValueError):validate_audio(pcm,100,10)
 def test_scene_changes_every_ten_seconds(self):
  images=[Image.new('RGB',(128,72),(i*40,0,0)) for i in range(6)]
  self.assertEqual(image_at(images,0).getpixel((0,0)),(0,0,0));self.assertEqual(image_at(images,10).getpixel((0,0)),(40,0,0));self.assertEqual(image_at(images,59.9).getpixel((0,0)),(200,0,0));self.assertEqual(image_at(images,9).getpixel((0,0)),(20,0,0))
 def test_three_distinct_rain_takes_overlap_to_22_seconds(self):
  clips=[np.ones(1000)*k for k in [.1,.2,.3]];self.assertEqual(len(overlap(clips,100,4)),2200)
  self.assertFalse(rain_score(np.zeros(160000),16000)[1]);self.assertTrue(rain_score(np.random.default_rng(1).normal(0,.05,160000),16000)[1])
 def test_depth_aware_effects_preserve_size(self):
  im=Image.new('RGB',(1280,720),(40,70,80));depth=Image.new('L',(1024,576),128)
  a=atmospheric(im,depth,0,dict(water_region='lower_center'),[(100,100,200)])
  b=atmospheric(im,depth,1,dict(water_region='lower_center'),[(100,100,200)])
  self.assertEqual(a.size,(1280,720));self.assertNotEqual(a.tobytes(),b.tobytes())
if __name__=='__main__':unittest.main()
