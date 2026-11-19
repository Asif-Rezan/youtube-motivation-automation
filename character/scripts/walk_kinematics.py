"""World-space helpers for the imported centimetre-scale Daz rig."""
import bpy,math
from mathutils import Vector
class WalkRig:
    def __init__(self,rig,body):
        self.rig=rig;self.body=body
        self.rest={b.name:rig.matrix_world@b.matrix_local for b in rig.data.bones}
        self.indices={side:[v.index for v in body.data.vertices if v.co.y<10 and (v.co.x>0)==(side=='l')] for side in ['l','r']}
    def p(self,n):return self.rig.matrix_world@self.rig.pose.bones[n].head
    def q(self,n):return (self.rig.matrix_world@self.rig.pose.bones[n].matrix).to_quaternion()
    def set(self,n,q,pos=None):
        w=q.to_matrix().to_4x4()
        for i in range(3):
            for j in range(3):w[i][j]*=.01
        w.translation=self.p(n) if pos is None else pos
        self.rig.pose.bones[n].matrix=self.rig.matrix_world.inverted()@w;bpy.context.view_layer.update()
    def soles(self):
        obj=self.body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=obj.to_mesh()
        result={side:min((obj.matrix_world@mesh.vertices[i].co).z for i in ids) for side,ids in self.indices.items()}
        obj.to_mesh_clear();return result
    def solve(self,side,goal,pole=None):
        tn=side+'_thigh';sn=side+'_shin';fn=side+'_foot';toe=side+'_toes'
        h=self.p(tn);k=self.p(sn);g=goal-(self.p(toe)-self.p(fn));qf=self.q(fn);qt=self.q(toe)
        rp=lambda n:self.rest[n].translation
        l1=(rp(sn)-rp(tn)).length;l2=(rp(fn)-rp(sn)).length
        horizontal=Vector((h.x-g.x,h.y-g.y,0)).length
        down=h.z-g.z-math.sqrt(max(.00001,(l1+l2-.0005)**2-horizontal**2))
        if down>0:
            pos=self.p('hip');pos.z-=down;self.set('hip',self.q('hip'),pos);h=self.p(tn);k=self.p(sn)
        axis=(g-h).normalized();distance=min(l1+l2-.00001,max(abs(l1-l2)+.00001,(g-h).length))
        bend=(k-h) if pole is None else pole.copy();bend-=axis*bend.dot(axis)
        if bend.length<1e-5:bend=Vector((0,-1,0))-axis*axis.dot(Vector((0,-1,0)))
        bend.normalize();c=max(-1,min(1,(l1*l1+distance*distance-l2*l2)/(2*l1*distance)))
        knee=h+axis*l1*c+bend*l1*math.sqrt(max(0,1-c*c))
        self.set(tn,(k-h).rotation_difference(knee-h)@self.q(tn))
        self.set(sn,(self.p(fn)-self.p(sn)).rotation_difference(g-self.p(sn))@self.q(sn))
        self.set(fn,qf);self.set(toe,qt)
