import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
import numpy as np
from PIL import Image,ImageDraw
from fitness.plan import generate,validate

def package():
    return dict(idea='A calm standing desk break using five controlled heel raises.',
        title='RESET in 60 Seconds: A Gentle Standing Calf Break',description='Follow five slow heel raises with a virtual coach.',
        tags=['heel raises','calf warmup','standing workout','desk break','one minute fitness','gentle exercise','calf exercise','fitness break'],
        music_prompt='Original upbeat instrumental with soft percussion and warm synths, no vocals.',bpm=112,
        thumbnail=dict(headline='READY TO RISE?',before_label='AT REST',after_label='HEELS UP',focus='full_body',accent_hue=190,
            before_frame=1,after_frame=120,angle='three_quarter',layout='diagonal'),
        cycles=[dict(movement='heel_raise',duration=12,chapter='Controlled raise '+str(i+1),ready='Stand comfortably tall',lift='Lift heels slowly',hold='Pause at the top',lower='Lower with control',reset='Breathe and reset') for i in range(5)])
def response(data):return dict(choices=[dict(message=dict(content=json.dumps(data)))])

class FitnessPreviewTests(unittest.TestCase):
    def test_real_timeline_metadata_and_no_publication(self):
        with tempfile.TemporaryDirectory() as temp,patch('storage.Store') as store,patch('lyrics_cpu.request_story',return_value=response(package())):
            store.return_value.load.return_value=[]
            plan=generate(Path(temp),'test-episode')
            self.assertIn('0:48 Controlled raise 5',plan['description'])
            self.assertEqual(plan['narration'][-1]['start'],56.7)
            self.assertTrue(all(c['start']+c['window']<=60 for c in plan['narration']))
            self.assertFalse(plan['publish'])
            self.assertFalse(plan['youtube']['status']['selfDeclaredMadeForKids'])
            self.assertEqual(plan['youtube']['snippet']['defaultAudioLanguage'],'en')
            self.assertFalse(plan['youtube']['paidProductPlacementDetails']['hasPaidProductPlacement'])

    def test_repeated_title_and_thumbnail_are_regenerated(self):
        old=package();new=copy.deepcopy(old);new['title']='WAKE Your Calves in 60 Seconds';new['thumbnail']['headline']='ONE SMALL RESET'
        history=[dict(title=old['title'],thumbnail=old['thumbnail']['headline'])]
        with tempfile.TemporaryDirectory() as temp,patch('storage.Store') as store,patch('lyrics_cpu.request_story',side_effect=[response(old),response(new)]) as ai:
            store.return_value.load.side_effect=[history,None]
            plan=generate(Path(temp),'fresh')
            self.assertEqual(ai.call_count,2);self.assertEqual(plan['title'],new['title'])

    def test_overlong_spoken_cue_and_misleading_runtime_rejected(self):
        data=package();data['cycles'][0]['lift']='This spoken instruction contains far too many words'
        with self.assertRaises(ValueError):validate(data)
        data=package();data['title']='RESET Your Whole Workout in Ten Minutes'
        with self.assertRaises(ValueError):validate(data)

    def test_thumbnail_layout_and_title_hook_change_the_actual_image(self):
        from fitness.compose import thumbnail
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp);data=package();(out/'plan.json').write_text(json.dumps(data))
            for name in ['before','after']:
                im=Image.new('RGBA',(400,900));ImageDraw.Draw(im).ellipse((100,20,300,850),fill=(220,180,150,255));im.save(out/f'thumbnail-{name}.png')
            thumbnail(out);first=(out/'thumbnail.jpg').read_bytes()
            data['thumbnail'].update(layout='inset',headline='A NEW KIND OF BREAK',accent_hue=315)
            (out/'plan.json').write_text(json.dumps(data));thumbnail(out)
            self.assertNotEqual(first,(out/'thumbnail.jpg').read_bytes())
            with Image.open(out/'thumbnail.jpg') as im:self.assertEqual(im.size,(1920,1080))

    def test_music_requires_neural_generation_then_covers_full_minute(self):
        from fitness.audio import music
        pcm=np.full((2400,2),.2,dtype=np.float32);sf=Mock();sf.read.return_value=(pcm,100)
        with tempfile.TemporaryDirectory() as temp,patch('music_cpu.generate_segment') as ai,patch.dict('sys.modules',soundfile=sf):
            out=Path(temp);(out/'plan.json').write_text(json.dumps(package()));music(out)
            self.assertTrue(ai.call_args.args[0]['instrumental'])
            self.assertEqual(ai.call_args.args[0]['duration'],24)
            written=sf.write.call_args.args[1]
            self.assertEqual(written.shape,(6000,2))
            self.assertTrue(np.allclose(written[0],0) and np.allclose(written[-1],0))

if __name__=='__main__':unittest.main()
