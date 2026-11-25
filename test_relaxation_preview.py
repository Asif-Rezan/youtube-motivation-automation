import tempfile,unittest
from pathlib import Path
import numpy as np
from PIL import Image
from relaxation.preview import plan,extend,validate_audio,image_at
class RelaxationTests(unittest.TestCase):
 def test_six_unique_scenes_exact_timeline_no_publish(self):
  with tempfile.TemporaryDirectory() as d:
   p=plan(Path(d),'episode');self.assertEqual([s['start'] for s in p['scenes']],[0,10,20,30,40,50]);self.assertEqual(len({s['seed'] for s in p['scenes']}),6);self.assertFalse(p['publish'])
 def test_loop_crossfade_and_exact_stereo_duration(self):
  pcm=np.sin(np.arange(1000)*.02).astype('float32');result=extend(pcm,100)
  self.assertEqual(result.shape,(6000,2));self.assertTrue(np.isfinite(result).all());self.assertLess(np.abs(np.diff(result[:,0])).max(),.1)
 def test_invalid_neural_outputs_rejected(self):
  for pcm in [np.zeros(1000),np.full(1000,np.nan),np.ones(20)]:
   with self.assertRaises(ValueError):validate_audio(pcm,100,10)
 def test_scene_changes_every_ten_seconds(self):
  images=[Image.new('RGB',(128,72),(i*40,0,0)) for i in range(6)]
  self.assertEqual(image_at(images,0).getpixel((0,0)),(0,0,0));self.assertEqual(image_at(images,10).getpixel((0,0)),(40,0,0));self.assertEqual(image_at(images,59.9).getpixel((0,0)),(200,0,0))
if __name__=='__main__':unittest.main()
