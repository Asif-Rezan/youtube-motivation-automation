import unittest
from fitness.sequence import compile_sequence,source_frame,narration
from fitness.plan import TIMING
from test_fitness_preview import package

class SequenceTests(unittest.TestCase):
    def test_ai_pacing_changes_actual_motion_and_voice(self):
        p=package()
        for c,d in zip(p['cycles'],[10,14,12,14,10]):c['duration']=d
        seq=compile_sequence(p)
        self.assertEqual([r['start_frame'] for r in seq],[0,240,576,864,1200])
        self.assertEqual(source_frame(seq,239),288)
        self.assertEqual(source_frame(seq,240),1)
        self.assertAlmostEqual(narration(p,TIMING)[5]['start'],10)
        self.assertNotEqual(source_frame(seq,120),source_frame(compile_sequence(package()),120))
        self.assertTrue(all(c['start']+c['window']<=60 for c in narration(p,TIMING)))
    def test_rejects_unknown_exercise_wrong_duration_and_timeline(self):
        for field,value in [('movement','pushup'),('duration',2),('duration',14)]:
            p=package();p['cycles'][0][field]=value
            with self.assertRaises(ValueError):compile_sequence(p)
    def test_every_frame_is_covered_and_source_bounds_hold(self):
        seq=compile_sequence(package())
        for f in range(1440):self.assertTrue(1<=source_frame(seq,f)<=288)
        with self.assertRaises(ValueError):source_frame(seq,1440)
if __name__=='__main__':unittest.main()
