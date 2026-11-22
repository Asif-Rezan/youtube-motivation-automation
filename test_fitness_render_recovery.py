"""Exercise real checkpoint decoding against simulated native-process failures."""
import json,subprocess,tempfile,unittest
from pathlib import Path
from PIL import Image
from fitness.render_worker import run,valid_checkpoint,RenderFailure

class RenderRecoveryTests(unittest.TestCase):
    def setup_files(self,folder):
        out=Path(folder);(out/'plan.json').write_text(json.dumps(dict(run_id='one',creative_seed=1)))
        (out/'speech-envelope.json').write_text('[0,0]');source=out/'source.blend';source.write_bytes(b'test-only source')
        return out,source
    def write_frame(self,out,frame):
        folder=out/'render-00';folder.mkdir(exist_ok=True)
        Image.new('RGBA',(1920,1080),(170,120,90,255)).save(folder/f'f-{frame:04d}.png')
        foot=dict(height=.001,points=[[1,1],[2,1],[2,2]])
        (folder/f'f-{frame:04d}.json').write_text(json.dumps(dict(frame=frame,feet=dict(l=foot,r=foot))))
    def test_crash_preserves_completed_frame_and_resumes_remainder(self):
        with tempfile.TemporaryDirectory() as temp:
            out,source=self.setup_files(temp);calls=[];saved=[]
            def worker(command,**kwargs):
                calls.append(command)
                if len(calls)==1:
                    self.write_frame(out,0);saved.append((out/'render-00/f-0000.png').stat().st_mtime_ns)
                    return subprocess.CompletedProcess(command,139)
                self.assertTrue(valid_checkpoint(out/'render-00',0));self.write_frame(out,1)
                return subprocess.CompletedProcess(command,0)
            run(out,0,'blender',source,execute=worker,count=2,batch=2)
            self.assertEqual(len(calls),2)
            self.assertEqual(saved[0],(out/'render-00/f-0000.png').stat().st_mtime_ns)
            self.assertEqual(len(json.loads((out/'render-00/contacts.json').read_text())),2)
    def test_abnormal_shutdown_is_accepted_only_after_all_outputs_validate(self):
        with tempfile.TemporaryDirectory() as temp:
            out,source=self.setup_files(temp)
            def worker(command,**kwargs):
                self.write_frame(out,0);return subprocess.CompletedProcess(command,139)
            run(out,0,'blender',source,execute=worker,count=1,batch=1)
            self.assertTrue(json.loads((out/'render-00/render-review.json').read_text())['validated_pngs'])
    def test_script_error_is_not_hidden_by_retries(self):
        with tempfile.TemporaryDirectory() as temp:
            out,source=self.setup_files(temp);calls=[]
            def worker(command,**kwargs):
                calls.append(command);kwargs['stdout'].write('Traceback (most recent call last)\nInvalid skin contact')
                return subprocess.CompletedProcess(command,2)
            with self.assertRaisesRegex(RenderFailure,'script/render failed'):run(out,0,'blender',source,execute=worker,count=1)
            self.assertEqual(len(calls),1)
    def test_native_failure_stops_after_three_attempts(self):
        with tempfile.TemporaryDirectory() as temp:
            out,source=self.setup_files(temp);calls=[]
            def worker(command,**kwargs):calls.append(command);return subprocess.CompletedProcess(command,-11)
            with self.assertRaisesRegex(RenderFailure,'three attempts'):run(out,0,'blender',source,execute=worker,count=1)
            self.assertEqual(len(calls),3)
    def test_corrupt_frame_cannot_be_used_as_completed_checkpoint(self):
        with tempfile.TemporaryDirectory() as temp:
            out,source=self.setup_files(temp);self.write_frame(out,0)
            (out/'render-00/f-0000.png').write_bytes(b'broken PNG')
            self.assertFalse(valid_checkpoint(out/'render-00',0))
    def test_same_episode_recovery_id_does_not_invalidate_correct_frames(self):
        with tempfile.TemporaryDirectory() as temp:
            out,source=self.setup_files(temp)
            def worker(command,**kwargs):self.write_frame(out,0);return subprocess.CompletedProcess(command,0)
            run(out,0,'blender',source,execute=worker,count=1)
            (out/'plan.json').write_text(json.dumps(dict(run_id='two',recovery_source_run='one',creative_seed=1)))
            def forbidden(*a,**k):raise AssertionError('A valid cached frame was rerendered')
            run(out,0,'blender',source,execute=forbidden,count=1)

if __name__=='__main__':unittest.main()
