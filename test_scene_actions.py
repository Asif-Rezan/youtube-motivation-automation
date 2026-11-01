import math
import unittest
import numpy as np
from PIL import Image, ImageDraw
from scene_actions import plan_scene, state_at, detect_face, compose_frame, actor_parts, compose_scene, motion_prompt


class SceneActionTests(unittest.TestCase):
    def test_rabbit_has_exactly_two_hop_arcs_after_notice(self):
        plan=plan_scene('a rabbit discovers a butterfly')
        samples=[state_at(plan,i/100)['hop'] for i in range(500)]
        starts=sum(v>0 and (i==0 or samples[i-1]==0) for i,v in enumerate(samples))
        self.assertEqual(starts,2)
        self.assertTrue(all(v==0 for v in samples[:210]))
        self.assertEqual([b['action'] for b in plan['beats']],
                         ['blink','prop_enters','look','two_hops','close_up_reaction'])

    def test_non_hopping_scenes_have_other_actions(self):
        for prompt,action,prop in [('child rolls a ball with puppy','approach','ball'),
                                  ('child and cat sleeping under moon','settle','star'),
                                  ('child and duck splash in rain','sway','droplet')]:
            plan=plan_scene(prompt)
            self.assertEqual((plan['action'],plan['prop']),(action,prop))
            self.assertTrue(all(state_at(plan,t/25)['hop']==0 for t in range(125)))

    def test_blank_actor_has_no_invented_face(self):
        self.assertIsNone(detect_face(Image.new('RGBA',(100,160),'white')))

    def test_entry_movement_and_reaction_work_in_both_orientations(self):
        for w,h in [(160,90),(90,160)]:
            bg=Image.new('RGBA',(w,h),'skyblue')
            actor=Image.new('RGBA',(20,35),'red')
            box=(w//3,h//3,w//3+20,h//3+35)
            plan=plan_scene('rabbit looks at butterfly')
            frames=[np.asarray(compose_frame(bg,actor,box,plan,t)) for t in [0,1.8,2.4,4.8]]
            self.assertTrue(all(f.shape==(h,w,3) for f in frames))
            self.assertTrue(all(np.any(a!=b) for a,b in zip(frames,frames[1:])))

    def test_tight_edge_character_remains_renderable(self):
        bg=Image.new('RGBA',(80,60),'blue')
        actor=Image.new('RGBA',(80,60),'red')
        for t in (0,2.4,3.3,4.9):
            self.assertEqual(compose_frame(bg,actor,(0,0,80,60),plan_scene('rabbit'),t).size,(80,60))

    def test_companions_are_separate_and_can_render_together(self):
        foreground=Image.new('RGBA',(180,120))
        d=ImageDraw.Draw(foreground)
        d.rectangle((20,25,50,105),fill='red')
        d.rectangle((100,50,130,105),fill='yellow')
        parts=actor_parts(foreground)
        self.assertEqual(len(parts),2)
        bg=Image.new('RGBA',foreground.size,'skyblue')
        frames=[np.asarray(compose_scene(bg,parts,plan_scene('child and puppy'),t)) for t in (0,1.8,4.8)]
        self.assertTrue(np.any(frames[0]!=frames[-1]))

    def test_world_does_not_override_the_current_lyric_action(self):
        scene={'lyric':'Roll our ball together', 'prompt':'Child and puppy with ball. Clear complete main character. World has moon and rain.'}
        self.assertEqual(plan_scene(motion_prompt(scene))['prop'],'ball')
