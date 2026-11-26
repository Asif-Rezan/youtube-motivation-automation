import copy
import unittest
from unittest.mock import patch
from relaxation.publication import validate,run
from upload_settings import load_settings

class PublicationTests(unittest.TestCase):
    def package(self):
        metadata={'snippet':{'description':'alex36917\n00:00 Rain'}}
        return {'seconds':10800,'scenes':[{}]*100,'nature_backend':'field_recording','chapters':'00:00 Rain','youtube':metadata},metadata
    def test_full_package_and_credits_required(self):
        plan,metadata=self.package();validate(plan,metadata)
        for field,value in [('seconds',60),('scenes',[{}]),('nature_backend','audioldm')]:
            bad=copy.deepcopy(plan);bad[field]=value
            with self.assertRaises(ValueError):validate(bad,metadata)
        bad=copy.deepcopy(metadata);bad['snippet']['description']='missing credit'
        with self.assertRaises(ValueError):validate(plan,bad)
    def test_music_general_audience_settings(self):
        with patch.dict('os.environ',{'UPLOAD_MODE':'public','PUBLISH_AT':''}):
            settings=load_settings(relaxation=True)
        self.assertEqual(settings['category_id'],'10')
        self.assertFalse(settings['made_for_kids']);self.assertFalse(settings['paid_product_placement'])
        self.assertTrue(settings['contains_synthetic_media'])
    def test_missing_facebook_configuration_stops_before_render(self):
        with patch.dict('os.environ',{},clear=True):
            with self.assertRaises(ValueError):run('preflight','123',None)
    def test_invalid_episode_rejected(self):
        with self.assertRaises(ValueError):run('cleanup','../bad',None)
