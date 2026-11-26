import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image,ImageDraw
from relaxation.editing import SceneRenderer,FEATURES,title_overlay,render_sequence
from relaxation.field_rain import ASSETS
from relaxation.preview import nature
class EditingTests(unittest.TestCase):
 def scene(self,water=False):
  im=Image.new('RGB',(1280,720),(90,130,150));d=ImageDraw.Draw(im)
  d.rectangle((0,360,1280,720),fill=(40,110,55));d.ellipse((300,440,1000,700),fill=(45,80,105))
  depth=Image.fromarray(np.tile(np.linspace(0,255,720,dtype='uint8')[:,None],(1,1280)))
  return SceneRenderer(im,depth,dict(camera='pan_left',water_region='lower_center' if water else 'none'),17)
 def test_all_ten_features_and_water_mask_scope(self):
  self.assertEqual(len(FEATURES),10);dry=self.scene();wet=self.scene(True)
  self.assertIsNone(dry.water.getbbox());self.assertIsNotNone(wet.water.getbbox())
  self.assertLessEqual(wet.water.getbbox()[3],720)
 def test_motion_changes_pixels_keeps_frames_and_no_black_camera_edges(self):
  r=self.scene(True);a=r.frame(0);b=r.frame(3)
  self.assertEqual(a.size,(1280,720));self.assertNotEqual(a.tobytes(),b.tobytes())
  self.assertGreater(sum(b.getpixel((0,0))),0)
 def test_minimal_label_fades_and_is_absent_after_duration(self):
  im=Image.new('RGB',(1280,720),(40,60,50))
  self.assertEqual(title_overlay(im,'Calm rain',0).tobytes(),im.tobytes());self.assertEqual(title_overlay(im,'Calm rain',4).tobytes(),im.tobytes())
  self.assertNotEqual(title_overlay(im,'Calm rain',2).tobytes(),im.tobytes())
 def test_recording_hash_and_attribution_are_present(self):
  meta=json.loads((ASSETS/'rain-source.json').read_text());b=(ASSETS/'rain-alex36917-blanket.ogg').read_bytes()
  self.assertEqual(hashlib.sha256(b).hexdigest(),meta['sha256']);self.assertEqual(meta['license'],'CC-BY-4.0');self.assertIn('alex36917',meta['credit']);self.assertIn('Porrumentzio',meta['credit'])
 def test_nature_stage_uses_recording_without_loading_ai(self):
  with tempfile.TemporaryDirectory() as tmp,patch('relaxation.field_rain.prepare') as prepare:
   out=Path(tmp);(out/'plan.json').write_text(json.dumps(dict(nature_backend='field_recording',run_id='new')))
   nature(out);prepare.assert_called_once_with(out,'new')
if __name__=='__main__':unittest.main()
