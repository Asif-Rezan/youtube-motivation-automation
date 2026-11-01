import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from PIL import Image, ImageDraw
from character_motion import prepare_layers, cached_clip, render_clip, deform


class CharacterMotionTests(unittest.TestCase):
    def test_layers_preserve_art_and_invalidate_changed_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            source=root/'source.png'
            image=Image.new('RGB',(80,60),'blue')
            ImageDraw.Draw(image).rectangle((25,10,55,50),fill='red')
            image.save(source)
            mask=Image.new('L',image.size)
            ImageDraw.Draw(mask).rectangle((25,10,55,50),fill=255)
            folder=root/'layers'
            extract=lambda im:mask
            with patch('character_motion.mask_for',side_effect=AssertionError('unexpected model')):
                first=prepare_layers(source,folder,extract,lambda im,m:Image.new('RGB',im.size,'blue'))
                fg=Image.open(folder/'foreground.png')
                self.assertEqual(fg.getpixel((30,20)),(255,0,0,255))
                self.assertEqual(fg.getpixel((0,0))[3],0)
                prepare_layers(source,folder,lambda im:self.fail('cache missed'),lambda im,m:self.fail('cache missed'))
                Image.new('RGB',(80,60),'green').save(source)
                changed=prepare_layers(source,folder,extract,lambda im,m:im)
                self.assertNotEqual(first['identity'],changed['identity'])
                (folder/'background.png').write_bytes(b'broken')
                prepare_layers(source,folder,extract,lambda im,m:im)
                Image.open(folder/'background.png').verify()

    def test_bad_mask_fails_instead_of_reusing_static_scene(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            source=root/'source.png'
            Image.new('RGB',(50,50),'white').save(source)
            for value in (0,255):
                with self.assertRaisesRegex(ValueError,'Invalid foreground'):
                    prepare_layers(source,root/'layers',lambda im:Image.new('L',im.size,value),lambda im,m:im)

    @unittest.skipUnless(shutil.which('ffmpeg'),'FFmpeg required')
    def test_actual_foreground_motion_and_cache_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            source=root/'source.png'
            image=Image.new('RGB',(160,90),'blue')
            ImageDraw.Draw(image).rectangle((55,20,95,80),fill='red')
            image.save(source)
            mask=Image.new('L',image.size)
            ImageDraw.Draw(mask).rectangle((55,20,95,80),fill=255)
            layers=root/'characters'/'source'
            prepare_layers(source,layers,lambda im:mask,lambda im,m:Image.new('RGB',im.size,'blue'))
            target=root/'clip.mp4'
            render_clip(source,target,160,90,0,'rabbit hopping')
            self.assertTrue(cached_clip(source,target,160,90,0,'rabbit hopping'))
            self.assertFalse(cached_clip(source,target,160,90,0,'new narration scene'))
            frames=[]
            for at in (0,1.2):
                raw=subprocess.check_output(['ffmpeg','-v','error','-ss',str(at),'-i',str(target),'-frames:v','1',
                    '-pix_fmt','rgb24','-f','rawvideo','pipe:1'])
                frames.append(np.frombuffer(raw,dtype=np.uint8).reshape(90,160,3).astype(float))
            self.assertGreater(np.abs(frames[0]-frames[1]).mean(),2)
            self.assertLess(np.abs(frames[0][0:10]-frames[1][0:10]).mean(),2)
            target.write_bytes(b'corrupted')
            self.assertFalse(cached_clip(source,target,160,90,0,'rabbit hopping'))
