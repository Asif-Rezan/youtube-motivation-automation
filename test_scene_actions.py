import math
import unittest
import numpy as np
from PIL import Image, ImageDraw
from scene_actions import plan_scene, state_at, detect_face, compose_frame, actor_parts, compose_scene, motion_prompt, background_motion, camera_viewport, actor_profile


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

    def test_background_moves_without_transparent_edges_or_moving_floor(self):
        w,h=320,180
        array=np.zeros((h,w,4),dtype=np.uint8)
        array[:,:,:3]=np.random.default_rng(8).integers(20,240,(h,w,3))
        array[:,:,3]=255
        image=Image.fromarray(array)
        a=np.asarray(background_motion(image,0))
        b=np.asarray(background_motion(image,1.4))
        self.assertGreater(np.abs(a.astype(float)-b).mean(),1)
        self.assertEqual(b[:,:,3].min(),255)
        self.assertLessEqual(np.abs(a[-1].astype(int)-b[-1].astype(int)).max(),1)

    def test_camera_pushes_in_but_keeps_cast_inside_landscape_and_portrait(self):
        plan=plan_scene('children and animals')
        for size,bounds in [((320,180),(80,30,250,155)),((180,320),(30,70,150,270)),
                            ((320,180),(0,0,320,180))]:
            first=camera_viewport(size,bounds,plan,0)
            last=camera_viewport(size,bounds,plan,4.96)
            for t in np.linspace(0,4.96,40):
                x,y,r,b=camera_viewport(size,bounds,plan,float(t))
                self.assertTrue(0<=x<=r<=size[0] and 0<=y<=b<=size[1])
                self.assertTrue(x<=bounds[0] and y<=bounds[1])
                self.assertTrue(r>=bounds[2] and b>=bounds[3])
            if bounds[0]>0:
                self.assertLess(last[2]-last[0],first[2]-first[0])

    def test_multiple_characters_move_independently_with_stationary_camera(self):
        bg=Image.new('RGBA',(320,180),'white')
        parts=[(Image.new('RGBA',(35,75),'red'),(60,70,95,145),None),
               (Image.new('RGBA',(40,70),'blue'),(205,60,245,130),None)]
        plan=plan_scene('child and bunny wave hello')
        def vertical_center(frame,color):
            mask=(np.asarray(frame)==color).all(axis=2)
            self.assertTrue(mask.any())
            return np.nonzero(mask)[0].mean()
        before=compose_scene(bg,parts,plan,0,camera=False,environment=False)
        after=compose_scene(bg,parts,plan,2.65,camera=False,environment=False)
        red_change=abs(vertical_center(after,[255,0,0])-vertical_center(before,[255,0,0]))
        blue_change=abs(vertical_center(after,[0,0,255])-vertical_center(before,[0,0,255]))
        self.assertGreater(blue_change,red_change+3)
        self.assertNotEqual(actor_profile(plan,0,2),actor_profile(plan,1,2))

    def test_small_companion_is_retained_and_masks_do_not_duplicate_pixels(self):
        fg=Image.new('RGBA',(180,160))
        d=ImageDraw.Draw(fg)
        d.rectangle((20,20,69,119),fill='red')
        d.rectangle((71,70,80,109),fill='blue')
        parts=actor_parts(fg)
        self.assertEqual(len(parts),2)
        total=np.zeros((160,180),dtype=np.int32)
        for image,bbox,_ in parts:
            x,y,r,b=bbox
            total[y:b,x:r]+=np.asarray(image)[:,:,3]
        np.testing.assert_array_equal(total,np.asarray(fg)[:,:,3])

    def test_empty_cast_is_a_valid_environment_shot(self):
        image=compose_scene(Image.new('RGBA',(180,320),'skyblue'),[],plan_scene('clouds'),2)
        self.assertEqual((image.mode,image.size),('RGB',(180,320)))

    def test_toddlers_and_animals_dance_even_when_background_mentions_night(self):
        plan=plan_scene('toddlers and baby animals dancing in moonlit garden')
        self.assertEqual((plan['kind'],plan['action'],plan['prop']),('dance','dance',None))
        hops=[state_at(plan,t/100)['hop'] for t in range(500)]
        starts=sum(v>0 and (i==0 or hops[i-1]==0) for i,v in enumerate(hops))
        self.assertGreaterEqual(starts,6)
        self.assertTrue(all(v==0 for v in hops[:30]))
        self.assertTrue(all(actor_profile(plan,i,3)['movement']=='dance' for i in range(3)))

    def test_dancing_kids_and_animal_have_distinct_motion_with_fixed_camera(self):
        bg=Image.new('RGBA',(320,180),'white')
        parts=[(Image.new('RGBA',(25,65),'red'),(50,70,75,135),None),
               (Image.new('RGBA',(25,65),'blue'),(140,70,165,135),None),
               (Image.new('RGBA',(30,45),'green'),(235,90,265,135),None)]
        plan=plan_scene('toddlers clap and dance with puppy')
        a=np.asarray(compose_scene(bg,parts,plan,0,camera=False,environment=False))
        b=np.asarray(compose_scene(bg,parts,plan,.95,camera=False,environment=False))
        for color in ([255,0,0],[0,0,255],[0,128,0]):
            before=(a==color).all(axis=2); after=(b==color).all(axis=2)
            self.assertTrue(before.any() and after.any())
            self.assertTrue(np.any(before!=after))
        self.assertEqual(np.asarray(b)[0,0].tolist(),[255,255,255,255] if b.shape[2]==4 else [255,255,255])
