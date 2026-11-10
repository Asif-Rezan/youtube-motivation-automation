import math
import unittest
import numpy as np
from PIL import Image
from scene_actions import plan_scene, travel_offset, travel_feet, compose_scene


class TravellingMotionTests(unittest.TestCase):
    def test_walk_run_and_chase_prompts_enable_real_travel(self):
        for cue,kind in [('walk together','walk'),('run across meadow','run'),('chase and play','run'),('clap dance','side_step'),('hop dance','hop')]:
            self.assertEqual(plan_scene(cue)['locomotion'],kind)
        self.assertIsNone(plan_scene('sleep under moon')['locomotion'])

    def test_path_is_smooth_visible_and_never_exits_frame(self):
        for size,bounds in [((640,360),(200,80,430,320)),((360,640),(80,180,260,570))]:
            plan=plan_scene('run across meadow 130 BPM')
            shifts=[travel_offset(size,bounds,plan,float(t)) for t in np.linspace(0,5,126)]
            self.assertEqual(shifts[0],0)
            self.assertGreater(abs(shifts[-1]),size[0]*.1)
            for dx in shifts:
                self.assertGreaterEqual(bounds[0]+dx,size[0]*.025-.01)
                self.assertLessEqual(bounds[2]+dx,size[0]*.975+.01)
            self.assertLess(max(abs(a-b) for a,b in zip(shifts,shifts[1:])),size[0]*.006)
        self.assertEqual(travel_offset((100,100),(0,0,100,100),plan,3),0)

    def test_fixed_camera_proves_actors_move_relative_to_ground_not_just_camera(self):
        bg=Image.new('RGBA',(640,360),'white')
        parts=[(Image.new('RGBA',(60,120),'red'),(210,190,270,310),None),
               (Image.new('RGBA',(55,110),'blue'),(370,200,425,310),None)]
        plan=plan_scene('walk and clap dance at 130 BPM')
        before=np.asarray(compose_scene(bg,parts,plan,0,camera=False,environment=False))
        after=np.asarray(compose_scene(bg,parts,plan,4.8,camera=False,environment=False))
        centers=[]
        for color in ([255,0,0],[0,0,255]):
            a=np.where((before[:,:,:3]==color).all(axis=2))[1]
            b=np.where((after[:,:,:3]==color).all(axis=2))[1]
            self.assertGreater(abs(b.mean()-a.mean()),70)
            centers.append(b.mean())
        self.assertLess(centers[0],centers[1])

    def test_stance_compensation_holds_foot_in_world_coordinates(self):
        size=(640,360);bounds=(200,80,430,320)
        plan=plan_scene('walk 120 BPM')
        beat=plan['beat_seconds']
        # Same left-foot stance, while the root continues moving.
        times=[beat*(2+u) for u in (.6,.7,.8,.9)]
        anchors=[travel_offset(size,bounds,plan,t)-travel_feet(size,bounds,plan,t)[0] for t in times]
        self.assertLess(max(anchors)-min(anchors),1e-9)

    def test_camera_preserves_both_actors_during_locomotion(self):
        bg=Image.new('RGBA',(320,180),'white')
        parts=[(Image.new('RGBA',(30,65),'red'),(100,90,130,155),None),
               (Image.new('RGBA',(30,60),'blue'),(210,90,240,150),None)]
        for t in np.linspace(0,4.96,20):
            pixels=np.asarray(compose_scene(bg,parts,plan_scene('run 130 BPM'),float(t)))
            for color in ([255,0,0],[0,0,255]):
                self.assertGreater(((pixels[:,:,:3]==color).all(axis=2)).sum(),500)
