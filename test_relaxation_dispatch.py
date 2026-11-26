import json,shutil,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from relaxation.production import main

class DispatchTests(unittest.TestCase):
 def test_all_worker_commands_call_the_correct_handler(self):
  for stage,handler in [('audio','audio_worker'),('assemble','assemble'),('clips','clip_shard'),('images','image_shard')]:
   with self.subTest(stage=stage),tempfile.TemporaryDirectory() as tmp,patch('relaxation.production.'+handler) as worker:
    main([stage,'--out',tmp,'--index','7'])
    worker.assert_called_once_with(*([Path(tmp),7] if stage in ('clips','images') else [Path(tmp)]))
 def test_invalid_stage_rejected_before_work(self):
  with patch('sys.stderr'),self.assertRaises(SystemExit):main(['unknown'])
 @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'FFmpeg required')
 def test_real_audio_command_encodes_expected_duration(self):
  try:import soundfile as sf
  except ImportError:self.skipTest('soundfile optional in lightweight test environment')
  import numpy as np
  with tempfile.TemporaryDirectory() as tmp:
   out=Path(tmp);rate=8000
   (out/'plan.json').write_text(json.dumps(dict(seconds=60,version=3,rain_seconds=60,nature_backend='field_recording')))
   for name,length in [('music-original.wav',24),('rain-original.wav',60)]:
    t=np.arange(rate*length)/rate;sf.write(out/name,.1*np.sin(2*np.pi*220*t),rate)
   main(['audio','--out',tmp])
   probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(out/'production-audio.m4a')]))
   self.assertAlmostEqual(float(probe['format']['duration']),60,places=1)
   self.assertEqual(probe['streams'][0]['channels'],2)
   self.assertEqual(int(probe['streams'][0]['sample_rate']),48000)
